"""Node instrumentation (brief Part 7).

One wrapper, applied to every node, so telemetry is written *as the node runs*
rather than inferred from the final state afterwards. The difference matters:
a reconstructed record says what the run must have done, an observed one says
what it did, and only the second is evidence.

Two properties this file exists to guarantee:

1. **Telemetry never corrupts the business result.** Recording is wrapped so
   that a failure in the telemetry path cannot propagate into the analysis.
   A run that loses its measurements is degraded; a run that loses its answer
   because measuring it failed is broken.
2. **A node error is recorded, not swallowed.** The wrapper marks the node
   failed, stores the message on the state, and lets the routing layer decide
   what that means. Nodes do not decide their own consequences.
"""

from __future__ import annotations

import functools
from datetime import datetime
from typing import Callable

from langgraph.errors import GraphBubbleUp

from graph.types import InsightState, NodeTelemetry, now_ms


class _LineageFailure(Exception):
    """Raised by `safe_lineage` when a lineage string could not be built.

    Carries the partial result so the wrapper can keep the analysis and drop
    only the description of it.
    """

    def __init__(self, partial: dict, detail: str):
        super().__init__(detail)
        self.partial = partial
        self.detail = detail


class NodeFailure(RuntimeError):
    """A node could not complete. Carried on state, routed deterministically."""


def instrument(name: str) -> Callable:
    """Wrap a node so it reports what it did.

    The wrapped function returns the partial state it wants merged; the wrapper
    appends exactly one `NodeTelemetry` to that partial. Nodes may set
    `_gate_result` / `_branch` / `_model` keys on their return value to record
    a verdict; the wrapper strips them so they never reach the merged state.
    """

    def decorator(fn: Callable[[InsightState], dict]) -> Callable:
        @functools.wraps(fn)
        def wrapper(state: InsightState, config=None) -> dict:
            started_wall = datetime.now().isoformat()
            t0 = now_ms()
            record = NodeTelemetry(node=name, started_at=started_wall)

            try:
                out = fn(state, config) or {}
                record.ok = True
                # Lineage is built here, inside the guard, so a formatting
                # fault in a descriptive string cannot destroy the analysis
                # the node just produced.
                fn_lineage = out.pop("_lineage_fn", None)
                if fn_lineage is not None:
                    try:
                        out["lineage"] = (list(out.get("lineage") or [])
                                          + list(fn_lineage()))
                    except Exception as exc:              # noqa: BLE001
                        record.error = (
                            f"lineage degraded: {type(exc).__name__}: {exc}")
            except _LineageFailure as exc:
                # The node's WORK succeeded and only its lineage string blew
                # up. Losing a real detection because a descriptive f-string
                # raised would be the telemetry path corrupting the business
                # result, which is the one thing it must never do.
                out = dict(exc.partial)
                record.ok = True
                record.error = f"lineage degraded: {exc.detail}"
            except GraphBubbleUp:
                # LangGraph control flow, not a failure. `interrupt()` raises
                # through here to pause the run, and swallowing it turns a
                # working human-in-the-loop pause into a node error — which is
                # exactly what a broad `except Exception` did on first run.
                # Control-flow exceptions must reach the runtime untouched.
                raise
            except Exception as exc:                      # noqa: BLE001
                # The node failed. Record it and hand a typed error to the
                # router; do not re-raise, or one bad node ends the run with a
                # traceback instead of a terminal state.
                out = {"error": f"{name}: {type(exc).__name__}: {exc}"}
                record.ok = False
                record.error = f"{type(exc).__name__}: {exc}"

            # --- measurements, isolated from the result ------------------
            try:
                record.latency_ms = now_ms() - t0
                record.ended_at = datetime.now().isoformat()
                record.gate_result = str(out.pop("_gate_result", "") or "")
                record.branch_taken = str(out.pop("_branch", "") or "")
                model = out.pop("_model", None)
                if model:
                    record.model_calls = int(model.get("calls", 0))
                    record.model_id = str(model.get("model_id", ""))
                    record.input_tokens = int(model.get("input_tokens", 0))
                    record.output_tokens = int(model.get("output_tokens", 0))
                    record.cached_input_tokens = int(
                        model.get("cached_input_tokens", 0))
                    record.estimated_cost_usd = float(
                        model.get("estimated_cost_usd", 0.0))
                out["telemetry"] = [record]
            except Exception:                             # noqa: BLE001
                # Telemetry is best-effort by construction. Strip the private
                # keys so a measurement bug cannot leak them into state, and
                # let the business result through untouched.
                for k in ("_gate_result", "_branch", "_model",
                          "_lineage_fn"):
                    out.pop(k, None)
                out.setdefault("telemetry", [])

            return out

        wrapper.__node_name__ = name        # type: ignore[attr-defined]
        return wrapper

    return decorator


def safe_lineage(partial: dict, build: Callable[[], list]) -> dict:
    """Attach lineage to a node's result without risking the result.

    `build` is called for its side-effect-free string formatting. If it
    raises — a renamed field, a None where an object was expected — the
    analysis in `partial` is preserved and the run continues with one lineage
    entry missing and the reason recorded. Brief Part 11: a telemetry failure
    must not silently corrupt the business result, and it must not loudly
    destroy it either.
    """
    try:
        records = build()
    except Exception as exc:                              # noqa: BLE001
        raise _LineageFailure(partial, f"{type(exc).__name__}: {exc}") from exc
    out = dict(partial)
    out["lineage"] = list(out.get("lineage") or []) + list(records)
    return out
