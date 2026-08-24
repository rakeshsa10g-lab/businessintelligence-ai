"""`run_insight(request) -> RunResult` — the one public entry point (brief 15).

A future Streamlit page consumes `RunResult` and nothing else. It does not
import a module, open the warehouse, or reach into graph state; that is
CLAUDE.md rule 6 made structural rather than aspirational.

Two things this module owns that the graph itself cannot:

* **Wall-clock timing.** Node latencies are summed from what each node
  recorded; the difference between their sum and the wall clock is the
  orchestration overhead, which is the number brief Part 14 asks for. It is
  measured, not assumed to be small.
* **Interrupt handling.** A run that hits `human_review` comes back paused.
  `resume_review` continues *that* run from its checkpoint rather than
  starting a second one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from graph.build import compile_graph
from security import audit as security_audit
from graph.types import (
    InsightState,
    RunResult,
    RunTelemetry,
    TerminalState,
    new_state,
    now_ms,
)
from semantic.types import Window

#: Longest legitimate path is ~18 nodes; anything past this is a loop.
RECURSION_LIMIT = 40


@dataclass
class InsightRequest:
    """A structured request. The graph never parses free text into one."""

    persona_id: str
    kpi_id: str
    window: Window
    slice_filter: dict[str, list[str]] | None = None
    cause_date: date | None = None
    scenario_id: str | None = None
    query_text: str = ""
    run_id: str = ""

    def new_run_id(self) -> str:
        """A fresh id per call unless one was explicitly supplied.

        A deterministic id built from scenario+persona was tried first and
        was a real bug: the checkpointer is durable and keyed by thread id,
        so re-invoking with the same id returned the PREVIOUS run's cached
        result rather than executing anything — invisible after a code fix,
        because the stale answer still looked plausible.
        """
        return self.run_id or f"R-{uuid.uuid4().hex[:10]}"


def _thread(run_id: str, **runtime) -> dict:
    """Thread id plus the run's non-persisted handles.

    `configurable` is passed per invocation and is not written to the
    checkpoint, so the client and index cannot end up in an audit record.
    """
    # Keys prefixed `__` are excluded from checkpoint metadata by LangGraph
    # (`checkpoint/base`), which is the documented way to pass a handle that
    # must not be persisted.
    prefixed = {f"__{k}": v for k, v in runtime.items()}
    return {
        "configurable": {"thread_id": run_id, **prefixed},
        # A structural backstop on top of `narration_attempts`. The counter is
        # the real cap; this bounds the graph even if the counter is wrong,
        # which it once was — a node that raised never incremented it and the
        # verify/retry cycle ran until the process died. A cap that depends on
        # bookkeeping being correct wants a limit that does not.
        "recursion_limit": RECURSION_LIMIT,
    }


def _collect(state: dict, run_id: str, wall_ms: float, *,
             interrupted: bool) -> RunResult:
    """Assemble the serialisable result from what the run actually recorded."""
    telemetry = RunTelemetry(
        run_id=run_id, nodes=list(state.get("telemetry") or []),
        wall_ms=wall_ms,
    )
    terminal = state.get("terminal")
    if interrupted and terminal is None:
        terminal = TerminalState.REVIEW_REQUIRED

    return RunResult(
        run_id=run_id,
        terminal=terminal or TerminalState.CONTRACT_ERROR,
        terminal_reason=state.get("terminal_reason", ""),
        persona_id=state.get("persona_id", ""),
        kpi_id=state.get("kpi_id", ""),
        scenario_id=state.get("scenario_id"),
        detection=state.get("detection"),
        narrative=state.get("narrative"),
        verification=state.get("verification"),
        confidence=state.get("confidence"),
        recommendations=state.get("recommendations"),
        deferral=state.get("deferral"),
        analyst_packet=state.get("analyst_packet"),
        bundle=state.get("bundle"),
        telemetry=telemetry,
        lineage=list(state.get("lineage") or []),
        interrupted=interrupted,
        thread_id=run_id,
    )


def run_insight(
    request: InsightRequest,
    *,
    graph=None,
    client=None,
    index=None,
    history_days: int | None = None,
    has_stable_baseline: bool = True,
) -> RunResult:
    """Execute one run to a terminal state, or to the human interrupt.

    `client` is the narrator's LLM client. Passing None is a supported mode,
    not a degraded one: the graph routes to the deterministic template and
    terminates `VERIFIED_TEMPLATE`.
    """
    run_id = request.new_run_id()
    compiled = graph or compile_graph()

    state = new_state(
        run_id=run_id,
        persona_id=request.persona_id,
        kpi_id=request.kpi_id,
        window=request.window,
        query_text=request.query_text,
        slice_filter=request.slice_filter,
        cause_date=request.cause_date,
        scenario_id=request.scenario_id,
    )
    config = _thread(
        run_id, client=client, index=index, history_days=history_days,
        has_stable_baseline=has_stable_baseline,
    )

    # Bind the security audit trail to this run BEFORE any node reads data,
    # so every `audit_log` row joins to the run id the user is shown. Without
    # this the column exists but correlates nothing (measured: two runs, one
    # id, matching neither).
    security_audit.set_run_id(run_id)

    t0 = now_ms()
    final = compiled.invoke(state, config=config)
    wall = now_ms() - t0

    interrupted = bool(final.get("__interrupt__"))
    if interrupted:
        # The values the paused run accumulated live in the checkpoint, not in
        # the payload the interrupt returned.
        final = dict(compiled.get_state(config).values)

    return _collect(final, run_id, wall, interrupted=interrupted)


def resume_review(
    run_id: str,
    response: dict[str, Any],
    *,
    graph=None,
    client=None,
    index=None,
) -> RunResult:
    """Resume a paused run with the analyst's decision.

    `response` carries the typed outcome — accept, reject, correct or
    request_clarification — and resumes the same thread, so the bundle,
    telemetry and lineage the run already accumulated are still there.
    """
    from langgraph.types import Command

    compiled = graph or compile_graph()
    config = _thread(run_id, client=client, index=index)
    # A resumed run is the same logical run; its reads belong to the same id.
    security_audit.set_run_id(run_id)
    t0 = now_ms()
    final = compiled.invoke(Command(resume=response), config=config)
    wall = now_ms() - t0

    still_paused = bool(final.get("__interrupt__"))
    if still_paused:
        final = dict(compiled.get_state(config).values)
    return _collect(final, run_id, wall, interrupted=still_paused)


def pending_review(run_id: str, *, graph=None) -> dict | None:
    """What a paused run is waiting for, without resuming it."""
    compiled = graph or compile_graph()
    snapshot = compiled.get_state(_thread(run_id))
    if not snapshot.interrupts:
        return None
    return snapshot.interrupts[0].value
