"""Session state and the single call into the backend (brief Part 25).

This module is the *only* place in `ui/` that touches the graph. Everything
else renders a `RunResult` that already exists. That is not a style preference:
CLAUDE.md rule 6 says Streamlit is presentation only, and the cheapest way to
enforce it is to give the UI exactly one function that can start work.

Consequences worth stating:

* The UI never opens DuckDB, never runs attribution or retrieval, never
  computes a confidence score and never calls the LLM. It cannot — none of
  those are imported anywhere under `ui/`, and a test asserts it.
* One analysis request is one graph run. Switching a tab, expanding evidence or
  toggling a drill-down re-renders from `st.session_state`; it does not re-run
  anything.
* The expensive shared resources — the embedding index and the compiled graph —
  are cached per process, because loading the index costs ~60 s and it is
  identical for every run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from graph.build import compile_graph, make_checkpointer
from graph.run import InsightRequest, pending_review, resume_review, run_insight
from graph.types import RunResult

#: Scenarios come from the Stage 9 harness, which ADR-028 made the executable
#: definition. Restating them here would create the second source of truth that
#: ADR-027 and ADR-028 exist to prevent.
from eval.run_recommendation_eval import PERSONAS, SCENARIOS, WINDOW  # noqa: E402


@dataclass(frozen=True)
class Scenario:
    """One demo scenario, read from the harness."""

    id: str
    label: str
    slice_filter: dict
    cause_date: Any
    persona_id: str

    @property
    def role(self) -> str:
        return PERSONAS[self.persona_id][0]

    @property
    def role_label(self) -> str:
        return self.role.replace("_", " ").title()

    @property
    def slice_label(self) -> str:
        if not self.slice_filter:
            return "All segments"
        return " × ".join(
            f"{'/'.join(v)}" for v in self.slice_filter.values()
        )


def scenarios() -> list[Scenario]:
    """The eight executable scenarios, in harness order."""
    return [
        Scenario(id=sid, label=label, slice_filter=sf or {},
                 cause_date=cd, persona_id=persona)
        for sid, label, sf, cd, persona in SCENARIOS
    ]


def scenario_by_id(scenario_id: str) -> Scenario:
    for s in scenarios():
        if s.id == scenario_id:
            return s
    raise KeyError(scenario_id)


def personas() -> dict[str, tuple[str, str | None]]:
    return dict(PERSONAS)


# --------------------------------------------------------------------------
# cached resources
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _index():
    from retrieval.embeddings import load_index
    return load_index()


@st.cache_resource(show_spinner=False)
def _graph():
    """One compiled graph per process, on a durable SQLite checkpointer.

    Durable rather than in-memory because a `REVIEW_REQUIRED` run is a real
    paused checkpoint that a person is expected to come back to. An in-memory
    saver would lose it on restart, which would make the review feature a
    demonstration of itself rather than the thing it claims to be.
    """
    return compile_graph(checkpointer=make_checkpointer())


def warm_up() -> None:
    """Load the index before the first run so its cost is not misattributed."""
    _index()
    _graph()


# --------------------------------------------------------------------------
# the one entry point
# --------------------------------------------------------------------------
def analyse(scenario: Scenario, *, persona_id: str | None = None,
            progress=None) -> RunResult:
    """Run one scenario through the graph. The only backend call in `ui/`.

    `persona_id` overrides the scenario's own persona so the same event can be
    read as three different roles — the analytical truth is identical, only
    entitlement and eligible actions differ.

    No `run_id` is supplied here, so `InsightRequest.new_run_id()` mints a
    fresh one. A fixed id built from scenario+persona was tried first and was
    a real bug: the checkpointer is durable, `invoke()` on an existing thread
    id returns that thread's cached result rather than executing anything, and
    clicking "Run analysis" a second time — or re-running after fixing a bug —
    silently produced the previous run's stale output.
    """
    request = InsightRequest(
        persona_id=persona_id or scenario.persona_id,
        kpi_id="net_revenue",
        window=WINDOW,
        slice_filter=scenario.slice_filter or None,
        cause_date=scenario.cause_date,
        scenario_id=scenario.id,
    )
    if progress is not None:
        progress.start()

    result = run_insight(
        request,
        graph=_graph(),
        index=_index(),
        # The two bundle inputs the harness supplies; S4 is the sparse case.
        history_days=23 if scenario.id == "S4" else 229,
        has_stable_baseline=scenario.id != "S4",
    )
    if progress is not None:
        progress.finish(result)
    return result


def submit_review(run_id: str, outcome: str, note: str = "") -> RunResult:
    """Resume a paused run with a real analyst decision.

    Goes through the LangGraph interrupt, not a local boolean. The run that
    resumes is the run that paused — same thread, same frozen bundle.
    """
    return resume_review(
        run_id, {"outcome": outcome, "note": note}, graph=_graph(),
    )


def review_payload(run_id: str) -> dict | None:
    return pending_review(run_id, graph=_graph())


# --------------------------------------------------------------------------
# session
# --------------------------------------------------------------------------
def init() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("scenario_id", "S1")
    st.session_state.setdefault("persona_id", None)
    st.session_state.setdefault("show_all_drivers", False)
    st.session_state.setdefault("review_submitted", None)


def current() -> RunResult | None:
    return st.session_state.get("result")


def store(result: RunResult) -> None:
    st.session_state["result"] = result
    st.session_state["review_submitted"] = None
