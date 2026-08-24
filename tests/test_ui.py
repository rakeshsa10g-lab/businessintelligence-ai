"""Stage 11 — the decision workspace.

Two kinds of test here, and the split is deliberate.

**Contract tests** are cheap and assert the properties that make the UI safe:
that no analysis lives in `ui/`, that restricted content cannot be rendered,
that template mode is labelled honestly. They run on synthetic inputs and take
milliseconds.

**Render tests** drive the real components with a real `RunResult`, so a
component that would crash on live data fails here rather than in front of a
judge. One run per scenario is expensive — 5 to 55 seconds — so the eight runs
are module-scoped and shared across every assertion that needs them.

The eight scenarios are read from the harness, never restated (ADR-028).
"""

from __future__ import annotations

import pathlib
import re

import pytest

from graph.types import SILENT_TERMINALS, RunResult, TerminalState

UI_ROOT = pathlib.Path(__file__).resolve().parents[1] / "ui"


# ==========================================================================
# contract: the UI computes nothing
# ==========================================================================
BANNED_IMPORTS = {
    "duckdb": "the UI must never query the warehouse",
    "anthropic": "the UI must never call the model directly",
    "attribution.engine": "the UI must never run attribution",
    "retrieval.engine": "the UI must never perform retrieval",
    "detection.engine": "the UI must never run detection",
    "confidence.engine": "the UI must never compute confidence",
    "semantic.gateway": "all data access goes through the graph",
}


def _ui_sources() -> list[tuple[pathlib.Path, str]]:
    return [(p, p.read_text(encoding="utf-8"))
            for p in UI_ROOT.rglob("*.py")]


@pytest.mark.parametrize("module,reason", sorted(BANNED_IMPORTS.items()))
def test_the_ui_never_imports_the_analytical_layer(module, reason):
    """Part 25, enforced structurally rather than by convention.

    `ui/state.py` is allowed one door into the backend — the graph. Nothing
    else in the package may reach past it.
    """
    for path, text in _ui_sources():
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped.startswith(("import ", "from ")):
                continue
            assert module not in stripped, f"{path.name}: {reason}"


def test_app_entrypoint_holds_no_analysis_either():
    text = (UI_ROOT.parent / "app.py").read_text(encoding="utf-8")
    for module in BANNED_IMPORTS:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert module not in stripped, f"app.py imports {module}"


def test_only_one_module_can_start_a_graph_run():
    """One door, so "the UI never runs analysis" is checkable in one place."""
    callers = [
        p.name for p, text in _ui_sources()
        if "run_insight" in text or "resume_review" in text
    ]
    assert set(callers) <= {"state.py"}, (
        f"{callers} can start a run; only ui/state.py may"
    )


def test_the_persona_selector_key_is_scoped_per_scenario():
    """Regression: switching scenarios silently kept the previous persona.

    A Streamlit widget with a fixed `key` ignores `index=` on every rerun
    after the first — its value lives in session_state once set, and the
    scenario selectbox changing does not touch that state. Concretely:
    default-load S1 (meera), switch to S6 without touching the persona
    selector, click Run — the analysis ran AS MEERA, not S6's own default
    ops_lead, defeating the one scenario built specifically to demonstrate
    entitlement withholding. A judge who only ever touches the scenario
    dropdown would never see S6 withhold anything.

    The fix scopes the widget key to the scenario id so each scenario gets
    its own independent default. This test reads the source rather than
    driving Streamlit, because the failure mode is about widget identity
    across reruns, which a single-shot render cannot exercise cheaply.
    """
    text = (UI_ROOT.parent / "app.py").read_text(encoding="utf-8")
    assert 'key=f"persona_pick_{scenario.id}"' in text, (
        "the persona selector must be keyed per scenario, or Streamlit will "
        "keep the previously selected persona when the scenario changes"
    )
    assert 'key="persona_pick"' not in text, (
        "a fixed key on the persona selector reintroduces the bug"
    )


def test_scenarios_are_read_from_the_harness_not_restated():
    """ADR-028. A second scenario definition is the bug this repo keeps hitting."""
    from ui import state as ui_state

    text = (UI_ROOT / "state.py").read_text(encoding="utf-8")
    assert "from eval.run_recommendation_eval import" in text

    ids = [s.id for s in ui_state.scenarios()]
    assert ids == ["S1", "S2", "S3", "S4", "S5a", "S5b", "S6", "S7"]


# ==========================================================================
# contract: the vocabulary the reader sees
# ==========================================================================
def test_the_loading_panel_uses_business_language_not_node_names():
    """Part 18. Node names belong in Method and Audit."""
    from ui.components.progress import STAGES, stage_labels

    for node, label in STAGES:
        assert node not in label, f"{label!r} leaks the node name {node!r}"
    for label in stage_labels():
        assert not any(t in label.lower() for t in
                       ("gate_", "node", "lmdi", "pelt", "bm25", "stl",
                        "adtributor", "rrf")), label


def test_slice_notation_is_humanised_before_it_reaches_the_reader():
    from ui.theme import humanise

    out = humanise("a product or platform failure in "
                   "channel=Web/Mobile App x region=West")
    assert "=" not in out
    assert " x " not in out
    assert "Web/Mobile App" in out and "West" in out


def test_humanise_does_not_swallow_across_a_clause_boundary():
    """Regression: the analyst review question is two clauses in parens.

    `(cause A in dims) or (cause B in dims)` — the first version of this
    regex had no way to stop at `)`, so once it started consuming a value it
    would run through the closing paren, the word "or", the opening paren of
    the SECOND clause, and its key name, stopping only at the next literal
    `x` — deleting an entire hypothesis's worth of text from what a person
    reviewing a real ambiguity would be shown.
    """
    from ui.theme import humanise

    q = ("Which is it: (competitive pressure on "
        "product_category=Apparel x region=South) or (stock availability in "
        "product_category=Apparel x region=South)?")
    out = humanise(q)

    assert "=" not in out
    assert out.count("Apparel") == 2, (
        "one occurrence was consumed into the other clause's match"
    )
    assert out.count("South") == 2
    assert "competitive pressure" in out and "stock availability" in out


def test_hypothesis_labels_are_words_not_raw_scores():
    """Part 7. `0.7595` has no external referent and means nothing to a reader."""
    from evidence.types import HypothesisStatus
    from ui.components.hypotheses import STATUS_LABEL

    for status in HypothesisStatus:
        assert status in STATUS_LABEL, f"{status} has no reader-facing label"
        label = STATUS_LABEL[status][0]
        assert not re.search(r"\d", label), f"{label} exposes a number"


def test_every_terminal_state_has_a_designed_screen():
    """A terminal with no screen would fall through to a blank page."""
    from ui.components.abstention import RENDERERS

    for terminal in SILENT_TERMINALS:
        assert terminal in RENDERERS, f"{terminal.name} has no screen"


# ==========================================================================
# contract: honesty about the model
# ==========================================================================
class _T:
    def __init__(self, calls=0, nodes=()):
        self.llm_calls = calls
        self.nodes = list(nodes)


class _R:
    def __init__(self, terminal, calls=0):
        self.terminal = terminal
        self.telemetry = _T(calls)


def test_template_mode_and_not_required_are_never_conflated():
    """Part 17. Both have zero model calls and mean different things."""
    from ui.components.audit import narration_mode

    label, _kind, text = narration_mode(_R(TerminalState.VERIFIED_TEMPLATE))
    assert label == "Verified template mode"
    assert "No ANTHROPIC_API_KEY" in text

    label2, _k2, text2 = narration_mode(_R(TerminalState.NO_MATERIAL_EVENT))
    assert label2 == "LLM not required"
    assert "no model was needed" in text2

    assert label != label2


def test_template_mode_never_implies_a_model_reviewed_the_text():
    from ui.components.audit import narration_mode

    _label, _kind, text = narration_mode(_R(TerminalState.VERIFIED_TEMPLATE))
    assert "No model reviewed this text" in text


def test_a_live_model_run_is_labelled_as_generated():
    from ui.components.audit import narration_mode

    r = _R(TerminalState.VERIFIED_LLM, calls=2)
    label, kind, text = narration_mode(r)
    assert "Model-generated" in label
    assert "2 model call" in text


# ==========================================================================
# render: the eight scenarios, driven for real
# ==========================================================================
@pytest.fixture(scope="module")
def runs() -> dict[str, RunResult]:
    """Every scenario, once. Expensive, so shared."""
    from eval.run_graph_eval import request_for
    from eval.run_recommendation_eval import SCENARIOS, load_index
    from graph.build import compile_graph
    from graph.run import run_insight

    graph = compile_graph(in_memory=True)
    index = load_index()
    out: dict[str, RunResult] = {}
    for sid, label, sf, cd, persona in SCENARIOS:
        out[sid] = run_insight(
            request_for(sid, label, sf, cd, persona),
            graph=graph, index=index,
            history_days=23 if sid == "S4" else 229,
            has_stable_baseline=sid != "S4",
        )
    return out


EXPECTED_TERMINALS = {
    "S1": TerminalState.VERIFIED_TEMPLATE,
    "S2": TerminalState.REVIEW_REQUIRED,
    "S3": TerminalState.REVIEW_REQUIRED,
    "S4": TerminalState.ABSTAIN_SPARSE_HISTORY,
    "S5a": TerminalState.VERIFIED_TEMPLATE,
    "S5b": TerminalState.VERIFIED_TEMPLATE,
    "S6": TerminalState.VERIFIED_TEMPLATE,
    "S7": TerminalState.NO_MATERIAL_EVENT,
}


@pytest.mark.parametrize("sid", list(EXPECTED_TERMINALS))
def test_every_scenario_is_demoable(sid, runs):
    """The UI must have something coherent to show for all eight."""
    result = runs[sid]
    assert result.terminal is EXPECTED_TERMINALS[sid]


@pytest.mark.parametrize("sid", list(EXPECTED_TERMINALS))
def test_every_scenario_renders_without_raising(sid, runs):
    """Drive the real components. A crash here is a crash in the demo."""
    from ui.components import (
        abstention, audit, confidence, drivers, evidence, hypotheses,
        method, movement, recommendation,
    )
    from ui import state as ui_state

    result = runs[sid]
    scenario = ui_state.scenario_by_id(sid)

    # Pure readers first — these must never raise regardless of terminal.
    movement.headline_numbers(result)
    evidence.counts(result)
    audit.narration_mode(result)
    drivers.driver_rows(result)
    confidence.basis_sentence(result)
    confidence.provenance_sentence(result)

    if result.terminal in SILENT_TERMINALS:
        assert result.terminal in abstention.RENDERERS


@pytest.mark.parametrize("sid", ["S1", "S5a", "S5b", "S6"])
def test_a_finding_answers_all_four_first_time_user_questions(sid, runs):
    """Part 24, asserted rather than claimed.

    What changed / why / how strong / what to do — every one has to be
    answerable from the objects the default screen renders.
    """
    from ui.components import confidence, drivers, evidence, movement

    result = runs[sid]

    n = movement.headline_numbers(result)
    assert n["pct"] is not None, "no answer to: what changed?"
    assert n["material"] is True

    assert result.bundle.hypotheses, "no answer to: why?"
    assert drivers.driver_rows(result), "no driver breakdown"

    support, _contra, _withheld = evidence.counts(result)
    assert support > 0, "no answer to: how strong is the evidence?"
    assert "of" in confidence.basis_sentence(result)

    assert result.recommendations.primary is not None, \
        "no answer to: what should I do?"


# ==========================================================================
# render: the states that are not findings
# ==========================================================================
def test_sparse_history_does_not_claim_a_materiality_verdict(runs):
    """Regression: the movement chip said "Below materiality threshold" for
    a run that never reached the materiality check.

    S4 aborts at the coverage gate — `DetectionOutcome.SPARSE_HISTORY` — which
    is earlier in the pipeline than materiality is ever evaluated. Showing
    "below threshold" claims a check ran and failed; it never ran at all.
    """
    from detection.types import DetectionOutcome
    from ui.components.movement import headline_numbers

    result = runs["S4"]
    assert result.detection.outcome is DetectionOutcome.SPARSE_HISTORY
    n = headline_numbers(result)
    assert n["material"] is False
    assert n["outcome"] is DetectionOutcome.SPARSE_HISTORY


def test_sparse_history_states_what_it_has_and_what_it_needs(runs):
    """Part 9. A decline has to be actionable too.

    S4 abstains at detection, so there is no EvidenceBundle. The counts the
    screen needs still exist on the detection result, which is why `RunResult`
    carries it separately — without that the screen could only say "not
    enough history" and not how much is missing.
    """
    result = runs["S4"]
    assert result.bundle is None, "S4 abstains before a bundle is frozen"
    assert result.detection is not None,         "the abstention screen cannot state its numbers without this"

    coverage = result.detection.coverage
    assert coverage.observations_available < coverage.observations_required
    # the gap is what the screen turns into "about N more days"
    assert coverage.observations_required - coverage.observations_available > 0


def test_no_material_event_is_quieter_than_a_finding(runs):
    """The Amber Alert habituation finding, made structural.

    S7 must not render a driver chart, a reliability chip or an action — if a
    non-event looked like an event the materiality gate would be undone by the
    presentation of it.
    """
    from ui.components import drivers

    result = runs["S7"]
    assert result.terminal is TerminalState.NO_MATERIAL_EVENT
    assert result.recommendations is None or result.recommendations.primary is None
    assert result.confidence is None or result.confidence.score == 0.0
    assert drivers.driver_rows(result) == []


def test_review_state_carries_a_real_interrupt_not_a_local_flag(runs):
    """Part 10. The pause is a checkpoint, and it holds the frozen bundle."""
    result = runs["S2"]
    assert result.terminal is TerminalState.REVIEW_REQUIRED
    assert result.interrupted is True
    assert result.bundle is not None
    assert result.bundle_hash, "the paused run lost its evidence"


def test_the_four_review_actions_match_the_graph_contract():
    from ui.components.review import ACTIONS

    offered = {a[0] for a in ACTIONS}
    assert offered == {"accept", "reject", "correct", "request_clarification"}


def test_conflicting_evidence_shows_competing_explanations(runs):
    """Part 9: show both, and why the system escalates rather than picking."""
    result = runs["S2"]
    assert len(result.bundle.hypotheses) >= 2
    top, second = result.bundle.hypotheses[0], result.bundle.hypotheses[1]
    assert top.cause_bucket != second.cause_bucket


# ==========================================================================
# render: entitlement
# ==========================================================================
def test_restricted_evidence_never_reaches_the_ui(runs):
    """Part 11. Filtered before ranking, so there is nothing to leak here."""
    result = runs["S6"]
    sec = result.bundle.security_context
    assert sec.withheld_item_count > 0, "S6 should withhold CRM evidence"

    # Whatever was withheld is absent from every rendered collection.
    rendered_ids = {i.evidence_id for i in
                    (result.bundle.supporting_evidence or ())}
    rendered_ids |= {i.evidence_id for i in
                     (result.bundle.contradicting_evidence or ())}
    for eid in rendered_ids:
        assert not eid.startswith("withheld:"), \
            "a withheld placeholder reached the rendered evidence"


def test_the_withheld_notice_says_nothing_about_what_was_withheld(runs):
    """The count is the trust signal; the content is not ours to show."""
    text = (UI_ROOT / "components" / "evidence.py").read_text(encoding="utf-8")
    notice = text.split("def render_withheld_notice")[1].split("def ")[0]
    assert "Some evidence is unavailable for your role" in notice
    assert "excerpt" not in notice
    for leaky in ("item.title", "item.excerpt", "w.excerpt"):
        assert leaky not in notice


def test_personas_differ_in_entitlement_not_in_analysis(runs):
    """Part 12. Same event, three roles: identical truth, different access."""
    ops, finance = runs["S5a"], runs["S5b"]

    assert ops.bundle.detection.pct_delta == finance.bundle.detection.pct_delta
    assert ops.recommendations.primary.lever_id == \
        finance.recommendations.primary.lever_id

    # what differs
    assert ops.persona_id != finance.persona_id
    assert (ops.bundle.security_context.withheld_item_count
            != finance.bundle.security_context.withheld_item_count)


# ==========================================================================
# render: telemetry and lineage
# ==========================================================================
def test_telemetry_renders_the_fields_part_17_requires(runs):
    result = runs["S1"]
    t = result.telemetry
    assert t.wall_ms > 0
    assert t.total_node_latency_ms > 0
    assert t.graph_overhead_ms >= 0
    assert t.llm_calls == 0
    assert t.estimated_cost_usd == 0.0
    retrieval = [n for n in t.nodes if n.node == "retrieve"]
    assert retrieval, "retrieval time is a required telemetry field"


def test_audit_can_answer_every_lineage_question(runs):
    result = runs["S1"]
    stages = {r.stage for r in result.lineage}
    for required in ("contract", "entitlement", "detection", "attribution",
                     "retrieval", "bundle", "verification", "recommendation"):
        assert required in stages, f"audit cannot answer '{required}'"
    assert result.bundle_hash


def test_the_run_result_is_serialisable_for_the_ui(runs):
    import json

    payload = runs["S1"].as_dict()
    assert json.dumps(payload)
    assert payload["terminal"] == "VERIFIED_TEMPLATE"


# ==========================================================================
# Antigravity browser QA findings — regression guards
# ==========================================================================
def test_p2_01_the_raw_loss_inequality_is_absent_from_the_workspace():
    """P2-01. `E[loss|model] ... < E[loss|human]+review ...` is audit notation.

    It is exact and it belongs in Method/Audit. On the decision screen it
    asks a business reader to parse conditional-expectation syntax before
    they can tell whether the system is acting or asking them to.
    """
    from deferral.types import AutomationScope, DeferralDecision, DeferralOutcome
    from ui.components.recommendation import business_rationale

    decision = DeferralDecision(
        outcome=DeferralOutcome.AUTOMATE, automated=True,
        expected_model_loss=53_571, expected_human_loss=128_250,
        review_cost=53_250, automation_scope=AutomationScope.RAISE_REQUEST,
        rationale=("E[loss|model] 53,571 < E[loss|human]+review 128,250 INR; "
                   "review would cost more than the accuracy it buys"),
    )
    prose = business_rationale(decision)

    for notation in ("E[loss", "|model]", "|human]", "E["):
        assert notation not in prose, f"{notation!r} leaked to the Workspace"
    # the figures themselves are kept — only the notation is replaced
    assert "53,571" in prose and "128,250" in prose and "53,250" in prose
    assert "risk" in prose.lower()


def test_p2_01_the_workspace_never_renders_the_raw_rationale_string():
    """The Workspace component must not print `decision.rationale` directly."""
    text = (UI_ROOT / "components" / "recommendation.py").read_text(
        encoding="utf-8")
    render_body = text.split("def render(")[1]
    assert "decision.rationale" not in render_body, (
        "render() prints the raw audit rationale; use business_rationale()"
    )


def test_p2_01_the_exact_notation_is_still_available_in_method():
    """Removing it from the Workspace must not remove it from the product."""
    text = (UI_ROOT / "components" / "method.py").read_text(encoding="utf-8")
    assert "decision.rationale" in text, (
        "the exact expected-loss notation must remain in the Method view"
    )
    assert "p_model" in text and "p_human" in text


def test_p2_02_a_cohort_with_no_data_is_not_rendered():
    """P2-02. An empty container reads as data that failed to load."""
    from ui.components.evidence import cohort_is_renderable

    class _Empty:
        label = ""
        cohort_id = ""
        incident_count = 0

    class _NoCount:
        label = "payment tickets"
        cohort_id = "C1"
        incident_count = 0

    class _Real:
        label = "payment tickets"
        cohort_id = "C1"
        incident_count = 9

    assert cohort_is_renderable(None) is False
    assert cohort_is_renderable(_Empty()) is False
    assert cohort_is_renderable(_NoCount()) is False, (
        "a cohort with a label but no documents has nothing to show"
    )
    assert cohort_is_renderable(_Real()) is True


def test_p2_02_a_populated_cohort_card_uses_the_real_field_names():
    """The blank cards came from `getattr` names that do not exist."""
    from retrieval.types import CohortEvidence
    from ui.components.evidence import _cohort_card

    fields = set(CohortEvidence.model_fields)
    for real in ("incident_count", "baseline_count", "ratio", "label",
                 "distinct_accounts", "novel", "baseline_weeks"):
        assert real in fields, f"{real} is not a CohortEvidence field"
    for invented in ("document_count", "count", "change_vs_baseline",
                     "ratio_vs_baseline", "summary"):
        assert invented not in fields

    card_src = (UI_ROOT / "components" / "evidence.py").read_text(
        encoding="utf-8")
    body = card_src.split("def _cohort_card(")[1].split("def ")[0]
    for invented in ("document_count", "change_vs_baseline", "ratio_vs_baseline"):
        assert invented not in body, f"_cohort_card still reads {invented}"


def _func_body(text: str, name: str) -> str:
    """The *code* of one top-level function, comments and docstrings stripped.

    Stripping matters: these tests assert that a symbol is not rendered, and
    the fix for each finding is documented in a comment that necessarily
    names the symbol it removed. Matching raw source would fail the test for
    explaining itself.
    """
    after = text.split(f"def {name}(")[1]
    body = after.split("\ndef ")[0]
    lines = []
    in_doc = False
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            # single-line docstring opens and closes on the same line
            if not (len(stripped) > 3 and stripped.endswith(('"""', "'''"))):
                in_doc = not in_doc
            continue
        if in_doc:
            continue
        code = line.split("#", 1)[0]
        if code.strip():
            lines.append(code)
    return "\n".join(lines)


def test_p2_03_the_workspace_shows_no_raw_detector_string():
    """P2-03. Gate names and enum values belong in Method/Audit."""
    text = (UI_ROOT / "components" / "abstention.py").read_text(encoding="utf-8")
    assert "terminal_reason" not in _func_body(text, "no_material_event"), (
        "the raw detector string is back on the no-material Workspace screen"
    )
    assert "terminal_reason" not in _func_body(text, "data_quality"), (
        "a raw exception string can reach the data-quality screen"
    )


def test_p2_03_the_raw_reason_is_still_available_in_audit():
    text = (UI_ROOT / "components" / "audit.py").read_text(encoding="utf-8")
    assert "terminal_reason" in text, (
        "the raw reason must remain visible in the Audit view"
    )


def test_p2_04_narration_status_is_a_chip_not_a_grey_caption():
    """P2-04. The disclosure has to be findable, without dominating."""
    text = (UI_ROOT / "components" / "audit.py").read_text(encoding="utf-8")
    assert "def render_narration_status(" in text
    body = _func_body(text, "render_narration_status")
    assert "theme.chip(" in body, "the indicator should use the chip style"
    assert "narration_mode(" in body, (
        "the indicator must derive from real telemetry, not a static string"
    )


def test_p2_04_the_sidebar_no_longer_asserts_a_missing_api_key():
    """The old caption claimed something about the environment, not the run.

    If a key WERE configured it would have said the opposite of the truth.
    """
    text = (UI_ROOT.parent / "app.py").read_text(encoding="utf-8")
    sidebar = _func_body(text, "sidebar")
    assert "No ANTHROPIC_API_KEY is configured" not in sidebar, (
        "the sidebar hardcodes a claim about the environment"
    )
    assert "status_slot" in sidebar


def test_p2_04_live_llm_and_template_modes_produce_different_indicators():
    """Both states, so the indicator cannot be a constant."""
    from ui.components.audit import narration_mode

    template_label, template_kind, template_text = narration_mode(
        _R(TerminalState.VERIFIED_TEMPLATE))
    live_label, live_kind, live_text = narration_mode(
        _R(TerminalState.VERIFIED_LLM, calls=2))

    assert template_label == "Verified template mode"
    assert "Model-generated" in live_label
    assert template_label != live_label
    assert template_kind != live_kind
    # the template state must never imply a model was involved
    assert "No model reviewed this text" in template_text
    assert "2 model call" in live_text
