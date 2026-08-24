"""Graph assembly and checkpointing (Architecture Part 12.2, 3.5).

The edges declared here are the whole control flow. Nothing decides where to go
next except the predicates in `graph/routing.py`, and none of those reads model
output. `import langchain` appears nowhere in this package (CLAUDE.md rule 2);
`langchain-core` arrives transitively under LangGraph, which the architecture
anticipated and accepted.

Checkpoint state lives in its own SQLite file, deliberately separate from the
DuckDB warehouse and the retrieval index (brief Part 9). A graph run that dies
half way corrupts a checkpoint, not the analytical data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from graph import nodes
from graph.routing import (
    route_access,
    route_contract,
    route_deferral,
    route_materiality,
    route_sufficiency,
    route_verification,
)
from graph.types import InsightState

ROOT = Path(__file__).resolve().parents[1]
#: Graph state only. Never the warehouse, never the embedding index.
CHECKPOINT_PATH = ROOT / "data" / "graph_checkpoints.sqlite"


def build_graph() -> StateGraph:
    """Declare nodes and edges. No checkpointer, no compilation."""
    g = StateGraph(InsightState)

    # --- nodes -----------------------------------------------------------
    g.add_node("resolve_intent", nodes.resolve_intent)
    g.add_node("load_contract", nodes.load_contract)
    g.add_node("enforce_entitlements", nodes.enforce_entitlements)
    g.add_node("detect", nodes.detect)
    g.add_node("attribute", nodes.attribute)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("rank_hypotheses", nodes.rank_hypotheses)
    g.add_node("gate_1", nodes.gate_1)
    g.add_node("narrate", nodes.narrate)
    g.add_node("gate_2", nodes.gate_2)
    g.add_node("retry_narrate", nodes.retry_narrate)
    g.add_node("deterministic_template", nodes.deterministic_template)
    g.add_node("calibrate", nodes.calibrate)
    g.add_node("recommend", nodes.recommend)
    g.add_node("defer", nodes.defer)
    g.add_node("human_review", nodes.human_review)
    g.add_node("deliver", nodes.deliver)
    g.add_node("log_run", nodes.log_run)

    # terminals
    g.add_node("access_denied", nodes.access_denied)
    g.add_node("contract_error", nodes.contract_error)
    g.add_node("no_material_event", nodes.no_material_event)
    g.add_node("abstain_sparse_history", nodes.abstain_sparse_history)
    g.add_node("abstain_data_quality", nodes.abstain_data_quality)
    g.add_node("abstain_insufficient_evidence",
               nodes.abstain_insufficient_evidence)
    g.add_node("clarify", nodes.clarify)
    g.add_node("abstain_terminal", nodes.abstain_terminal)

    # --- edges -----------------------------------------------------------
    g.add_edge(START, "resolve_intent")
    g.add_edge("resolve_intent", "load_contract")

    g.add_conditional_edges("load_contract", route_contract, {
        "ok": "enforce_entitlements",
        "clarify": "clarify",
        "error": "contract_error",
    })

    g.add_conditional_edges("enforce_entitlements", route_access, {
        "allowed": "detect",
        "denied": "access_denied",
        "error": "contract_error",
    })

    g.add_conditional_edges("detect", route_materiality, {
        "material": "attribute",
        "not_material": "no_material_event",
        "sparse": "abstain_sparse_history",
        "insufficient_data": "abstain_data_quality",
        "error": "abstain_data_quality",
    })

    g.add_edge("attribute", "retrieve")
    g.add_edge("retrieve", "rank_hypotheses")
    g.add_edge("rank_hypotheses", "gate_1")

    g.add_conditional_edges("gate_1", route_sufficiency, {
        "narrate": "narrate",
        "insufficient": "abstain_insufficient_evidence",
        "error": "abstain_insufficient_evidence",
    })

    g.add_edge("narrate", "gate_2")

    # The one cycle in the graph, bounded by `narration_attempts`.
    g.add_conditional_edges("gate_2", route_verification, {
        "pass": "calibrate",
        "retry": "retry_narrate",
        "template": "deterministic_template",
    })
    g.add_edge("retry_narrate", "gate_2")
    g.add_edge("deterministic_template", "calibrate")

    g.add_edge("calibrate", "recommend")
    g.add_edge("recommend", "defer")

    g.add_conditional_edges("defer", route_deferral, {
        "deliver": "deliver",
        "review": "human_review",
        "abstain": "abstain_terminal",
        "error": "abstain_terminal",
    })

    # every path converges on one exit, so telemetry is finalised once
    for terminal in (
        "access_denied", "contract_error", "no_material_event",
        "abstain_sparse_history", "abstain_data_quality",
        "abstain_insufficient_evidence", "clarify", "abstain_terminal",
        "human_review", "deliver",
    ):
        g.add_edge(terminal, "log_run")

    g.add_edge("log_run", END)
    return g


#: Modules whose types cross the checkpoint boundary.
#:
#: LangGraph 1.2 deserialises unregistered types with a warning and says it
#: "will be blocked in a future version". Left alone this repository would keep
#: working until an upgrade broke resume — and resume failing means a paused
#: analyst review that cannot be continued, which is the worst place to find a
#: serialisation problem.
#:
#: The allowlist is derived from the modules rather than typed out. A literal
#: list would drift the moment a type was added, and the failure mode of that
#: drift is silent: an unregistered class comes back as a plain `dict`, so
#: `state["deferral"].outcome` raises `AttributeError` deep inside a resumed
#: run rather than at the boundary where the loss happened.
CHECKPOINTED_MODULES = (
    "graph.types",
    "semantic.types", "semantic.contract",
    "security.entitlements",
    "detection.types",
    "attribution.types",
    "retrieval.types",
    "evidence.types",
    "verification.types",
    "confidence.types",
    "recommendation.types",
    "deferral.types",
)


def _allowed_types() -> tuple[type, ...]:
    """Every class each checkpointed module defines, as classes.

    Classes rather than name strings: a renamed or deleted type then fails at
    import here, instead of degrading a checkpoint into untyped dicts.
    """
    import importlib
    import inspect

    found: list[type] = []
    for module_name in CHECKPOINTED_MODULES:
        module = importlib.import_module(module_name)
        for _name, obj in vars(module).items():
            if inspect.isclass(obj) and obj.__module__ == module_name:
                found.append(obj)
    return tuple(found)


#: Resolved once; the modules are already imported by the time a graph is built.
ALLOWED_CHECKPOINT_MODULES = _allowed_types()


def make_serde():
    """Serialiser with this project's types registered explicitly."""
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer(
        allowed_msgpack_modules=ALLOWED_CHECKPOINT_MODULES,
    )


def make_checkpointer(path: Path | None = None, *, in_memory: bool = False):
    """The SQLite checkpointer, or an in-memory one for tests.

    Returns the saver itself rather than a context manager, so callers are not
    forced into a `with` block around an entire run.
    """
    if in_memory:
        return InMemorySaver(serde=make_serde())
    target = path or CHECKPOINT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False)
    return SqliteSaver(conn, serde=make_serde())


def compile_graph(*, checkpointer=None, in_memory: bool = False):
    """A runnable graph. Checkpointing is on by default: the interrupt needs it."""
    saver = checkpointer or make_checkpointer(in_memory=in_memory)
    return build_graph().compile(checkpointer=saver)


def draw_mermaid() -> str:
    """Render the compiled graph. Generated, never hand-drawn (brief Part 12)."""
    return compile_graph(in_memory=True).get_graph().draw_mermaid()
