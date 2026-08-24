"""Stage 10 — graph routing, terminals, retry, interrupts, telemetry, lineage.

Most of this file tests the routing predicates *directly*, with synthetic
state, which the brief asks for explicitly. The reason is not only speed: a
test that drives a whole scenario and checks the final answer cannot tell you
*why* it routed as it did, so it passes for the wrong reason as easily as the
right one. Predicate tests name the branch.

The end-to-end runs that remain are session-scoped, because one real run costs
seconds of detection, embedding and retrieval work and none of it changes
between assertions.
"""

from __future__ import annotations

from datetime import date

import pytest

from confidence.types import ConfidenceBand
from deferral.types import (
    AbstentionReason,
    AutomationScope,
    DeferralDecision,
    DeferralOutcome,
)
from detection.types import DetectionOutcome
from graph import routing
from graph.build import ALLOWED_CHECKPOINT_MODULES, build_graph, compile_graph
from graph.routing import (
    MAX_NARRATION_ATTEMPTS,
    abstention_terminal,
    route_access,
    route_contract,
    route_deferral,
    route_materiality,
    route_sufficiency,
    route_verification,
)
from graph.types import TerminalState
from semantic.types import Window


# ==========================================================================
# fakes — just enough shape for a predicate, nothing more
# ==========================================================================
class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _det(outcome=DetectionOutcome.MATERIAL_EVENT, material=True):
    return _Obj(outcome=outcome, is_material=material)


def _hyp(score, bucket, status=None):
    from evidence.types import HypothesisStatus
    return _Obj(score=score, cause_bucket=bucket,
                status=status or HypothesisStatus.SUPPORTED,
                statement=f"h({bucket})")


def _bundle(*hyps):
    return _Obj(hypotheses=tuple(hyps))


def _report(hard=0):
    return _Obj(hard_violation_count=hard, violations=())


# ==========================================================================
# every conditional branch
# ==========================================================================
def test_route_access_allows_denies_and_errors():
    assert route_access({"access": _Obj(allowed=True)}) == "allowed"
    assert route_access({"access": _Obj(allowed=False)}) == "denied"
    assert route_access({"error": "boom"}) == "error"


def test_route_contract_separates_unknown_kpi_from_broken_config():
    """The two faults have different remedies, so they get different edges."""
    assert route_contract({"contract": _Obj()}) == "ok"
    assert route_contract({"error": "unknown_kpi:revenue_per_llama"}) == "clarify"
    assert route_contract({"error": "yaml parse failure"}) == "error"
    assert route_contract({}) == "error"


def test_route_materiality_defers_to_detections_own_verdict():
    assert route_materiality({"detection": _det()}) == "material"
    assert route_materiality(
        {"detection": _det(DetectionOutcome.NO_MATERIAL_FINDING, False)}
    ) == "not_material"
    assert route_materiality(
        {"detection": _det(DetectionOutcome.SPARSE_HISTORY, False)}
    ) == "sparse"
    assert route_materiality(
        {"detection": _det(DetectionOutcome.INSUFFICIENT_DATA, False)}
    ) == "insufficient_data"
    assert route_materiality({}) == "error"


def test_a_material_outcome_that_is_not_material_still_stops():
    """`outcome` and `is_material` are separate fields and can disagree.

    Trusting only the enum would let a run with `is_material=False` proceed to
    attribution on the strength of a label.
    """
    assert route_materiality(
        {"detection": _det(DetectionOutcome.MATERIAL_EVENT, material=False)}
    ) == "not_material"


def test_route_sufficiency_has_exactly_two_answers():
    from evidence.types import HypothesisStatus

    assert route_sufficiency({"bundle": _bundle(_hyp(0.9, "a"))}) == "narrate"
    assert route_sufficiency({"bundle": _bundle()}) == "insufficient"
    assert route_sufficiency({}) == "insufficient"
    assert route_sufficiency({
        "bundle": _bundle(_hyp(0.9, "a", HypothesisStatus.INSUFFICIENT))
    }) == "insufficient"


def test_ambiguity_is_recorded_but_no_longer_terminates(caplog):
    """ADR-029. The close pair still exists; it just is not Gate 1b's call.

    Before the change this returned "ambiguous" and ended the run, throwing
    away the analyst packet the deferral engine would have built.
    """
    close = _bundle(_hyp(0.7595, "external_competitor"),
                    _hyp(0.6827, "internal_inventory"))
    assert routing.is_ambiguous(close) is True
    assert route_sufficiency({"bundle": close}) == "narrate"


def test_ambiguity_needs_both_a_close_score_and_a_different_owner():
    same_owner = _bundle(_hyp(0.70, "internal_product"),
                         _hyp(0.68, "internal_product"))
    far_apart = _bundle(_hyp(0.90, "internal_product"),
                        _hyp(0.20, "external_market"))
    assert routing.is_ambiguous(same_owner) is False
    assert routing.is_ambiguous(far_apart) is False
    assert routing.is_ambiguous(_bundle(_hyp(0.9, "a"))) is False


def test_route_deferral_covers_all_three_outcomes():
    def d(outcome):
        return {"deferral": _Obj(outcome=outcome)}
    assert route_deferral(d(DeferralOutcome.AUTOMATE)) == "deliver"
    assert route_deferral(d(DeferralOutcome.REVIEW)) == "review"
    assert route_deferral(d(DeferralOutcome.ABSTAIN)) == "abstain"
    assert route_deferral({}) == "error"


# ==========================================================================
# the retry cycle — capped at one
# ==========================================================================
def test_gate_2_passes_straight_through_when_clean():
    assert route_verification(
        {"verification": _report(0), "narration_attempts": 1}
    ) == "pass"


def test_gate_2_retries_once_then_falls_back_to_the_template():
    """The whole cycle, asserted as a sequence rather than one branch."""
    assert route_verification(
        {"verification": _report(2), "narration_attempts": 1}
    ) == "retry"
    assert route_verification(
        {"verification": _report(2), "narration_attempts": 2}
    ) == "template"


def test_a_third_attempt_is_unreachable_at_any_attempt_count():
    """Not just at 2 — at every count above it."""
    for attempts in range(MAX_NARRATION_ATTEMPTS, MAX_NARRATION_ATTEMPTS + 5):
        assert route_verification(
            {"verification": _report(3), "narration_attempts": attempts}
        ) == "template"


def test_an_unparseable_response_spends_the_retry_then_falls_back():
    """A failed generation is a transient failure and gets the one retry."""
    assert route_verification({"narration_attempts": 0}) == "retry"
    assert route_verification({"narration_attempts": 1}) == "retry"
    assert route_verification(
        {"narration_attempts": MAX_NARRATION_ATTEMPTS}) == "template"


def test_the_narrate_node_refuses_a_third_call_even_if_routing_were_wrong():
    """Defence in depth: the cap is enforced twice, by the router and here.

    A router bug would otherwise turn into paid model calls in a loop.
    """
    from graph import nodes

    state = {"bundle": _Obj(), "narration_attempts": MAX_NARRATION_ATTEMPTS,
             "_client": object(), "run_id": "X"}
    out = nodes.narrate(state)
    assert out.get("error"), "a third narration attempt must fail"
    assert "not permitted" in out["error"]


def test_soft_violations_alone_do_not_trigger_a_retry():
    """Only HARD violations cost a model call."""
    soft_only = _Obj(hard_violation_count=0, violations=("soft",))
    assert route_verification(
        {"verification": soft_only, "narration_attempts": 1}
    ) == "pass"


# ==========================================================================
# no LLM chooses an edge
# ==========================================================================
def test_no_routing_predicate_reads_a_narrative():
    """The architecture's central claim, asserted against the source.

    Reads the predicate source rather than trusting the docstring: a predicate
    that started consulting `state["narrative"]` would pass every behavioural
    test in this file and still break the guarantee.
    """
    import inspect

    for name, fn in routing.PREDICATES.items():
        src = inspect.getsource(fn)
        assert '"narrative"' not in src, f"{name} reads the narrative"
        assert "claims" not in src, f"{name} reads model claims"


def test_verification_routing_reads_the_verdict_not_the_text():
    import inspect

    src = inspect.getsource(route_verification)
    assert "hard_violation_count" in src
    assert "headline" not in src and "text" not in src


# ==========================================================================
# terminal states
# ==========================================================================
def test_every_abstention_reason_maps_to_a_terminal():
    for reason in AbstentionReason:
        if reason is AbstentionReason.NONE:
            continue
        assert isinstance(abstention_terminal(reason), TerminalState)


def test_conflicting_evidence_reaches_its_own_terminal():
    """Reachable through the deferral engine after ADR-029 moved it there."""
    assert abstention_terminal(AbstentionReason.CONFLICTING_EVIDENCE) is \
        TerminalState.ABSTAIN_CONFLICTING_EVIDENCE


def test_unauthorized_information_is_an_access_terminal_not_an_abstention():
    assert abstention_terminal(AbstentionReason.UNAUTHORIZED_INFORMATION) is \
        TerminalState.ACCESS_DENIED


def test_every_terminal_state_has_a_node_that_can_set_it():
    """No terminal in the enum is decorative."""
    import inspect

    from graph import nodes

    src = inspect.getsource(nodes) + inspect.getsource(routing)
    for t in TerminalState:
        assert f"TerminalState.{t.name}" in src, f"{t.name} is unreachable"


# ==========================================================================
# graph structure
# ==========================================================================
def test_the_graph_compiles_and_has_one_cycle():
    compiled = compile_graph(in_memory=True)
    g = compiled.get_graph()
    edges = {(e.source, e.target) for e in g.edges}
    # the only back-edge: gate_2 -> retry_narrate -> gate_2
    assert ("gate_2", "retry_narrate") in edges
    assert ("retry_narrate", "gate_2") in edges


def test_every_terminal_node_converges_on_the_logging_exit():
    """One exit, so telemetry is finalised on every path including failures."""
    g = compile_graph(in_memory=True).get_graph()
    edges = {(e.source, e.target) for e in g.edges}
    terminals = [
        "access_denied", "contract_error", "no_material_event",
        "abstain_sparse_history", "abstain_data_quality",
        "abstain_insufficient_evidence", "clarify", "abstain_terminal",
        "human_review", "deliver",
    ]
    for t in terminals:
        assert (t, "log_run") in edges, f"{t} does not reach log_run"


def test_mermaid_is_generated_from_the_compiled_graph():
    """The picture cannot drift from the code, because it is not drawn."""
    from graph.build import draw_mermaid

    text = draw_mermaid()
    assert "graph" in text.lower()
    for node in ("detect", "gate_2", "retry_narrate", "human_review",
                 "deterministic_template"):
        assert node in text, f"{node} missing from the generated diagram"


def test_no_direct_langchain_import_anywhere_in_the_graph_package():
    """CLAUDE.md rule 2. `langchain-core` transitively is fine; `langchain` is not."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "graph"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            assert not stripped.startswith("import langchain"), path
            assert not stripped.startswith("from langchain "), path
            assert not stripped.startswith("from langchain."), path


def test_no_autonomous_agent_constructs():
    """No `create_agent`, no tool selection, no supervisor."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "graph"
    banned = ("create_agent", "create_react_agent", "AgentExecutor",
              "ToolNode", "bind_tools")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{token} found in {path}"


def test_checkpoint_state_is_separate_from_analytical_data():
    """A failed run must not be able to touch the warehouse."""
    from graph.build import CHECKPOINT_PATH

    assert CHECKPOINT_PATH.suffix == ".sqlite"
    assert "warehouse" not in CHECKPOINT_PATH.name
    assert CHECKPOINT_PATH.name != "warehouse.duckdb"


def test_project_types_are_registered_with_the_checkpoint_serialiser():
    """LangGraph will block unregistered types in a future version.

    Without registration the failure would surface as a paused analyst review
    that cannot be resumed, after an upgrade nobody connected to it.
    """
    registered = {c.__module__ for c in ALLOWED_CHECKPOINT_MODULES}
    for module in ("graph.types", "evidence.types", "deferral.types",
                   "confidence.types", "verification.types",
                   "detection.types", "attribution.types"):
        assert module in registered, f"{module} not registered"
