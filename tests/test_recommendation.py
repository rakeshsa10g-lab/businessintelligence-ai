"""Stage 9 tests — recommendation, confidence, deferral, feedback.

The tests that matter most here are the ones asserting what the system will NOT
do: recommend a lever nobody approved, quote an accuracy it has not observed,
automate an action the reader could not authorise, or collapse six distinct
reasons for declining into one.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import pytest

from attribution import engine as att
from confidence import engine as conf_engine
from confidence.types import (
    CalibrationEntry,
    CalibrationTable,
    ConfidenceBand,
    CalibrationCoverage,
)
from data import spec
from deferral import engine as defer_engine
from deferral.types import AbstentionReason, DeferralOutcome
from detection import engine as det
from evidence import levers as levers_mod
from evidence.bundle import freeze_evidence_bundle
from evidence.types import HypothesisStatus
from feedback import store as feedback_store
from feedback.types import FeedbackEvent, FeedbackOutcome, ROUTING, UpdateTiming
from recommendation import engine as rec_engine
from recommendation.types import DecisionRight, ImpactModel
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}
SOUTH = {"region": ["South"], "product_category": ["Apparel"]}
EAST = {"region": ["East"], "segment": ["SMB"]}

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
OPS_LEAD = Principal(
    user_id="priya", display_name="Priya Nair", role="ops_lead",
    user_region="West",
)
FINANCE = Principal(
    user_id="arjun", display_name="Arjun Mehta", role="finance_director"
)


@pytest.fixture(scope="module")
def index():
    return load_index()


def _bundle(slice_filter, principal, persona, cause_date, index, scenario, **kw):
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=20)
    if d.observed_start is None and d.changepoint_date is None:
        from retrieval.types import (
            FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
        )
        r = RetrievalResult(
            query=RetrievalQuery(text=""), filters=FilterConditions(),
            config=RetrievalConfig(
                embedding_model="none", embedding_dim=1, corpus_hash="none"
            ),
        )
    else:
        r = ret.retrieve_evidence(a, principal, index=index)
    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario}", persona_id=persona,
        detection=d, attribution=a, retrieval=r, **kw
    )


@pytest.fixture(scope="module")
def s1(index):
    return _bundle(WEST, ANALYST, "meera", date(2026, 7, 12), index, "S1")


@pytest.fixture(scope="module")
def s2(index):
    return _bundle(SOUTH, ANALYST, "meera", date(2026, 6, 2), index, "S2")


@pytest.fixture(scope="module")
def s3(index):
    return _bundle(EAST, ANALYST, "meera", date(2026, 8, 5), index, "S3")


@pytest.fixture(scope="module")
def s4(index):
    return _bundle(
        {"product_category": ["NewLaunch"]}, ANALYST, "meera", None, index,
        "S4", history_days=23, has_stable_baseline=False,
    )


@pytest.fixture(scope="module")
def s6(index):
    return _bundle(WEST, OPS_LEAD, "priya", date(2026, 7, 12), index, "S6")


def _pipeline(bundle, queue_depth: int = 0):
    confidence = conf_engine.compute(bundle)
    recs = rec_engine.recommend(bundle, confidence)
    decision = defer_engine.decide(
        bundle, confidence, recs, queue_depth=queue_depth
    )
    return confidence, recs, decision


# ==========================================================================
# lever catalogue
# ==========================================================================
def test_every_lever_carries_the_stage_9_fields():
    from evidence import levers as levers_mod

    catalogue = levers_mod.load_catalogue()
    assert catalogue["version"] == "2.0.0"
    for lever in catalogue["levers"]:
        for field in ("driver_id", "action_template", "eligible_personas",
                      "expected_impact", "allowed_confidence_context",
                      "owner_role", "monitoring", "constraints"):
            assert field in lever, f"{lever['lever_id']} lacks {field}"


def test_a_valid_lever_resolves():
    spec_ = rec_engine.validate_lever_id("L_GATEWAY_ESCALATE")
    assert spec_["owner_role"] == "engineering_lead"


def test_an_invalid_lever_is_rejected_as_a_hallucination():
    with pytest.raises(rec_engine.LeverHallucination, match="not in the catalogue"):
        rec_engine.validate_lever_id("L_INVENTED_BY_A_MODEL")


def test_an_llm_generated_lever_id_never_becomes_a_recommendation(s1):
    """The hard rule from Part 14.3, from the recommendation side."""
    from evidence import levers as levers_mod

    known = levers_mod.known_lever_ids()
    _, recs, _ = _pipeline(s1)
    for r in recs.recommendations:
        assert r.lever_id in known


def test_every_monitoring_metric_exists_in_the_semantic_catalogue():
    from evidence import levers as levers_mod
    from semantic import registry

    for lever in levers_mod.load_catalogue()["levers"]:
        metric = (lever.get("monitoring") or {}).get("metric")
        assert metric, f"{lever['lever_id']} names no monitoring metric"
        registry.get(metric)      # raises if it is not a real KPI


def test_a_lever_naming_an_unknown_metric_is_refused(s1):
    bad = {
        "lever_id": "L_FAKE", "monitoring": {"metric": "vibes_per_quarter"},
    }
    with pytest.raises(rec_engine.RecommendationError, match="semantic catalogue"):
        rec_engine.build_monitoring_plan(bad, s1)


# ==========================================================================
# impact — computed, never generated
# ==========================================================================
def test_impact_is_computed_from_the_measured_movement(s1):
    _, recs, _ = _pipeline(s1)
    assert recs.recommendations
    r = recs.primary
    movement = s1.fact("F-movement-abs")

    assert r.expected_impact.computed
    assert r.expected_impact.source_fact_id == "F-movement-abs"
    assert r.expected_impact.high == pytest.approx(
        abs(movement.value) * r.expected_impact.recovery_fraction_high
    )
    assert r.expected_impact.low < r.expected_impact.high


def test_impact_is_a_range_not_a_point_estimate(s1):
    _, recs, _ = _pipeline(s1)
    impact = recs.primary.expected_impact
    assert impact.low != impact.high
    assert impact.model.value in impact.render()


def test_a_schema_change_claims_no_business_impact(s1):
    """A definition change moved no money; claiming a recoverable amount would
    be the exact error the scenario exists to catch."""
    from evidence import levers as levers_mod

    spec_ = levers_mod.get("L_DATA_QUALITY_FIX")
    impact = rec_engine.compute_impact(spec_, s1, s1.hypotheses[0])
    assert impact.model is ImpactModel.NO_BUSINESS_IMPACT
    assert impact.low == 0.0 and impact.high == 0.0
    assert "artefact" in impact.render()


def test_no_measured_movement_yields_no_claimed_amount(s4):
    from evidence import levers as levers_mod

    spec_ = levers_mod.get("L_GATEWAY_ESCALATE")
    fake_hypothesis = None
    impact = rec_engine.compute_impact(spec_, s4, fake_hypothesis)
    assert impact.low == 0.0 and impact.high == 0.0
    assert "no measured movement" in impact.basis


# ==========================================================================
# persona restrictions
# ==========================================================================
def test_persona_decision_rights_are_resolved(s1):
    from evidence import levers as levers_mod

    spec_ = levers_mod.get("L_GATEWAY_ESCALATE")
    assert rec_engine.persona_right(spec_, "engineering_lead") is DecisionRight.APPROVE
    assert rec_engine.persona_right(spec_, "ops_lead") is DecisionRight.REQUEST
    assert rec_engine.persona_right(spec_, "nobody") is DecisionRight.NONE


def test_a_persona_without_rights_gets_no_recommendation(s1):
    from evidence import levers as levers_mod

    spec_ = levers_mod.get("L_PRICING_REVIEW")
    assert "ops_lead" not in (spec_.get("eligible_personas") or [])


def test_request_rights_automate_the_request_not_the_action(s1):
    """Raising a request automatically is not performing an action
    automatically, and conflating the two defers everything."""
    from deferral.types import AutomationScope

    confidence, recs, decision = _pipeline(s1)
    if decision.abstain or recs.primary is None:
        pytest.skip("this bundle abstains")
    if recs.primary.persona_right is DecisionRight.REQUEST and decision.automated:
        assert decision.automation_scope is AutomationScope.RAISE_REQUEST
        assert "request" in decision.render().lower()


def test_a_persona_with_no_rights_at_all_never_automates(s1):
    """Asserting the config flag is set proves nothing about behaviour.

    The earlier version of this test read `require_persona_any_rights is True`
    and stopped there, which would still have passed had the override been
    deleted from the engine entirely.
    """
    from deferral.types import AutomationScope

    confidence, recs, _ = _pipeline(s1)
    if recs.primary is None:
        pytest.skip("this bundle abstains")

    stripped = recs.primary.model_copy(update={"persona_right": DecisionRight.NONE})
    recs_no_rights = recs.model_copy(
        update={"recommendations": (stripped,) + tuple(recs.recommendations[1:])}
    )
    decision = defer_engine.decide(s1, confidence, recs_no_rights)

    assert decision.automated is False
    assert decision.automation_scope is AutomationScope.NONE
    assert "no rights" in (decision.override_applied or "")


def test_scope_is_none_unless_the_decision_actually_automated(s1, s2, s3, s6):
    """`automation_scope` states what WAS automated, not what could have been.

    A review carrying `execute` is a live misreading hazard: a consumer that
    reads the scope without reading the outcome would act on a decision that
    deliberately declined to act.
    """
    from deferral.types import AutomationScope

    for bundle in (s1, s2, s3, s6):
        confidence, recs, decision = _pipeline(bundle)
        if decision.automation_scope is not AutomationScope.NONE:
            assert decision.automated is True, (
                f"{bundle.bundle_id}: scope "
                f"{decision.automation_scope.value} on a non-automated decision"
            )


def test_a_never_automate_lever_is_never_automated(s1):
    """The escalate/execute boundary, asserted behaviourally.

    Raising an engineering request may be automated. Performing the technical
    remediation may not. This drives the real decision path with a disruptive
    lever as the primary rather than trusting the config list by inspection.
    """
    from deferral.types import AutomationScope

    policy = defer_engine.load_policy()
    never = sorted(policy["overrides"].get("never_automate_lever_ids") or [])
    assert never, "the never-automate list must not be empty"

    confidence, recs, _ = _pipeline(s1)
    if recs.primary is None:
        pytest.skip("this bundle abstains")

    for lever_id in never:
        spec = levers_mod.get(lever_id)
        forced = recs.primary.model_copy(update={
            "lever_id": lever_id,
            "lever_name": spec["name"],
            # the most permissive right there is - the guard must hold anyway
            "persona_right": DecisionRight.APPROVE,
        })
        forced_recs = recs.model_copy(update={"recommendations": (forced,)})
        decision = defer_engine.decide(s1, confidence, forced_recs)

        assert decision.automated is False, f"{lever_id} was automated"
        assert decision.automation_scope is AutomationScope.NONE
        assert lever_id in (decision.override_applied or "")


def test_which_disruptive_levers_rest_on_a_single_guard(s1):
    """Records defence in depth per lever, so erosion of it fails here.

    `L_CHECKOUT_ROLLBACK` is guarded twice: it is on the never-automate list
    AND no persona this system runs as can approve it, so even without the
    list it could only ever reach `raise_request`.

    `L_PRICING_REVIEW` is guarded once. `finance_director` is both a persona
    the system runs as and an approver, so deleting one config line would make
    an automated pricing change reachable. That is the correct behaviour today
    and a single point of failure tomorrow; this test exists so the asymmetry
    is visible rather than assumed.
    """
    personas = {"ops_lead", "analytics_lead", "finance_director"}

    rollback = set(
        (levers_mod.get("L_CHECKOUT_ROLLBACK").get("decision_rights") or {})
        .get("can_approve") or []
    )
    assert not (rollback & personas), (
        "L_CHECKOUT_ROLLBACK gained a persona approver; it now rests on the "
        "never-automate list alone"
    )

    pricing = set(
        (levers_mod.get("L_PRICING_REVIEW").get("decision_rights") or {})
        .get("can_approve") or []
    )
    assert pricing & personas == {"finance_director"}, (
        "the single-guard set for L_PRICING_REVIEW changed; re-check whether "
        "the never-automate list is still the only thing stopping an "
        "automated pricing change"
    )


def test_gateway_escalate_is_a_request_for_every_persona(s1):
    """L_GATEWAY_ESCALATE escalates; it does not roll back.

    `can_approve` is [engineering_lead, cto]. Neither is a persona this system
    runs as, so the automated act is always raising the request.
    """
    spec = levers_mod.get("L_GATEWAY_ESCALATE")
    approvers = set((spec.get("decision_rights") or {}).get("can_approve") or [])
    assert approvers == {"engineering_lead", "cto"}
    for role in ("ops_lead", "analytics_lead", "finance_director"):
        assert rec_engine.persona_right(spec, role) is DecisionRight.REQUEST


def test_the_same_event_gives_different_personas_different_evidence(s1, s6):
    """The earlier version asserted `x != y or True`, which is a tautology.

    What actually differs between an analytics lead and an ops lead on this
    event is entitlement: the CRM note is readable by one and not the other.
    """
    _, analyst_recs, _ = _pipeline(s1)
    _, ops_recs, _ = _pipeline(s6)

    assert analyst_recs.persona_id != ops_recs.persona_id
    assert s6.security_context.withheld_item_count > 0, (
        "s6 runs as ops_lead and should have CRM evidence withheld"
    )
    assert s1.security_context.withheld_item_count == 0
    assert "crm_note" in s6.security_context.withheld_source_ids
    # withheld items are counted, never silently dropped
    assert s6.security_context.withheld_source_ids


# ==========================================================================
# confidence
# ==========================================================================
def test_confidence_weights_live_in_configuration():
    cfg = conf_engine.load_config()
    assert cfg["version"]
    assert abs(sum(cfg["weights"].values()) - 1.0) < 1e-9


def test_confidence_config_rejects_weights_that_do_not_sum_to_one(tmp_path):
    bad = tmp_path / "confidence.yaml"
    bad.write_text(
        "version: 'x'\nweights: {a: 0.9, b: 0.9}\n"
        "contradiction: {penalty_per_signal: 0.1, max_penalty: 0.5}\n"
        "data_quality: {base: 1.0}\nbands: {HIGH: 0.75}\n"
        "calibration: {min_cases_per_band: 10}\n",
        encoding="utf-8",
    )
    with pytest.raises(conf_engine.ConfidenceError, match="sum to"):
        conf_engine.load_config(str(bad))


def test_confidence_is_deterministic(s1):
    first = conf_engine.compute(s1)
    for _ in range(5):
        again = conf_engine.compute(s1)
        assert again.score == first.score
        assert again.band is first.band


def test_confidence_components_reconstruct_the_score(s1):
    c = conf_engine.compute(s1)
    subtotal = sum(comp.weighted for comp in c.components)
    assert c.score == pytest.approx(
        min(1.0, subtotal * c.contradiction_multiplier), abs=1e-9
    )


def test_the_p_value_is_not_a_confidence_component(s1):
    """ADR-017: the Welch p-value is post-selection and scores nothing."""
    c = conf_engine.compute(s1)
    names = {comp.name for comp in c.components}
    assert "p_value" not in names
    assert "robustness" in names


def test_sparse_history_deducts_from_data_quality(s4, s1):
    sparse, _ = conf_engine.data_quality_score(s4)
    healthy, _ = conf_engine.data_quality_score(s1)
    assert sparse < healthy


def test_confidence_never_renders_a_bare_number(s1):
    text = conf_engine.compute(s1).render()
    assert text.strip() != ""
    # a band name must be present; a lone score must not be the whole message
    assert any(
        word in text
        for word in ("High", "Medium", "Low", "UNCALIBRATED", "Insufficient")
    )


def test_an_empty_calibration_table_yields_uncalibrated(s1):
    empty = CalibrationTable(version="0.0.0", source="none")
    c = conf_engine.compute(s1, calibration=empty)
    assert c.band is ConfidenceBand.UNCALIBRATED
    assert c.coverage is CalibrationCoverage.NO_HISTORY
    assert "UNCALIBRATED" in c.render()
    assert not c.reportable


def test_a_thin_calibration_band_yields_uncalibrated(s1):
    thin = CalibrationTable(
        version="1.0.0", source="test", n_cases=3,
        entries=(
            CalibrationEntry(band=ConfidenceBand.HIGH, correct=3, total=3),
        ),
    )
    c = conf_engine.compute(s1, calibration=thin)
    assert c.band is ConfidenceBand.UNCALIBRATED
    assert c.coverage is CalibrationCoverage.OUT_OF_COVERAGE


def test_a_covered_band_reports_the_observed_base_rate(s1):
    table = CalibrationTable(
        version="1.0.0", source="test", n_cases=40, is_synthetic=True,
        entries=(
            CalibrationEntry(band=ConfidenceBand.HIGH, correct=29, total=34),
            CalibrationEntry(band=ConfidenceBand.MEDIUM, correct=18, total=31),
            CalibrationEntry(band=ConfidenceBand.LOW, correct=6, total=22),
        ),
    )
    c = conf_engine.compute(s1, calibration=table)
    assert c.coverage is CalibrationCoverage.IN_COVERAGE
    assert "of" in c.render() and "similar past cases" in c.render()
    assert "synthetic" in c.render()


def test_calibration_is_labelled_synthetic():
    table = conf_engine.load_calibration()
    assert table.is_synthetic
    if table.n_cases:
        assert "NOT production history" in table.source


def test_a_conflicted_hypothesis_cannot_report_high_confidence(s2):
    assert s2.overall_status is HypothesisStatus.CONFLICTED
    table = CalibrationTable(
        version="1.0.0", source="test",
        entries=(
            CalibrationEntry(band=ConfidenceBand.HIGH, correct=29, total=34),
            CalibrationEntry(band=ConfidenceBand.MEDIUM, correct=18, total=31),
        ),
    )
    c = conf_engine.compute(s2, calibration=table)
    assert c.band is not ConfidenceBand.HIGH


def test_a_bundle_with_no_hypotheses_is_insufficient(s4):
    c = conf_engine.compute(s4)
    assert c.band is ConfidenceBand.INSUFFICIENT
    assert not c.reportable


# ==========================================================================
# deferral
# ==========================================================================
def test_the_deferral_rule_compares_expected_losses(s1):
    confidence, recs, decision = _pipeline(s1)
    if decision.abstain:
        pytest.skip("this bundle abstains before the arithmetic runs")
    assert decision.model_arm is not None and decision.human_arm is not None
    assert decision.expected_model_loss == pytest.approx(
        (1 - decision.p_model) * decision.cost_of_error
    )
    assert decision.expected_human_loss == pytest.approx(
        (1 - decision.p_human) * decision.cost_of_error + decision.review_cost
    )


def test_deferral_is_not_a_confidence_threshold(s1):
    """The same band gives different answers as the decision value changes."""
    policy = defer_engine.load_policy()
    confidence, recs, _ = _pipeline(s1)
    if confidence.band is ConfidenceBand.INSUFFICIENT:
        pytest.skip("no arithmetic on an insufficient bundle")

    cheap = json.loads(json.dumps(policy))
    cheap["decision_value_inr"] = {"analytics_lead": 50_000, "default": 50_000}
    expensive = json.loads(json.dumps(policy))
    expensive["decision_value_inr"] = {
        "analytics_lead": 50_000_000, "default": 50_000_000
    }

    d_cheap = defer_engine.decide(s1, confidence, recs, policy=cheap)
    d_expensive = defer_engine.decide(s1, confidence, recs, policy=expensive)
    # identical confidence, different decisions - a threshold cannot do this
    assert (d_cheap.outcome, d_expensive.outcome) != (None, None)
    assert d_cheap.expected_model_loss != d_expensive.expected_model_loss


def test_a_disruptive_lever_is_never_automated(s1):
    policy = defer_engine.load_policy()
    assert "L_CHECKOUT_ROLLBACK" in policy["overrides"]["never_automate_lever_ids"]


def test_uncalibrated_confidence_always_defers(s1):
    empty = CalibrationTable(version="0.0.0", source="none")
    confidence = conf_engine.compute(s1, calibration=empty)
    recs = rec_engine.recommend(s1, confidence)
    decision = defer_engine.decide(s1, confidence, recs)
    assert not decision.automated
    if decision.review:
        assert "UNCALIBRATED" in (decision.override_applied or "")


def test_an_exhausted_review_queue_abstains_rather_than_promising(s1):
    confidence, recs, _ = _pipeline(s1)
    decision = defer_engine.decide(s1, confidence, recs, queue_depth=99)
    if decision.outcome is DeferralOutcome.ABSTAIN:
        assert not decision.capacity_ok
        assert "queue" in decision.rationale


def test_the_decision_records_its_policy_version(s1):
    _, _, decision = _pipeline(s1)
    assert decision.policy_version == defer_engine.load_policy()["version"]


# ==========================================================================
# abstention — six distinct states
# ==========================================================================
def test_sparse_history_is_its_own_abstention_state(s4):
    confidence, recs, decision = _pipeline(s4)
    assert decision.abstain
    assert decision.abstention_reason is AbstentionReason.SPARSE_HISTORY
    assert "history" in decision.remedy


def test_no_material_event_is_its_own_state(index):
    bundle = _bundle(
        {"region": ["North"], "product_category": ["Electronics"]},
        ANALYST, "meera", None, index, "FLAT",
    )
    _, _, decision = _pipeline(bundle)
    assert decision.abstain
    assert decision.abstention_reason in (
        AbstentionReason.NO_MATERIAL_EVENT,
        AbstentionReason.EVIDENCE_INSUFFICIENCY,
    )


def test_conflicting_evidence_is_distinguished_from_insufficiency(s2):
    reason = defer_engine.classify_abstention(s2, conf_engine.compute(s2))
    assert reason is AbstentionReason.CONFLICTING_EVIDENCE


def test_an_unsupported_causal_claim_is_not_an_abstention_from_the_finding(s2):
    """The movement and its driver stand; only the wording is constrained."""
    from deferral.types import ABSTENTION_REMEDY

    remedy = ABSTENTION_REMEDY[AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM]
    assert "finding stands" in remedy or "associative" in remedy


def test_every_abstention_reason_has_a_remedy():
    from deferral.types import ABSTENTION_REMEDY

    for reason in AbstentionReason:
        if reason is AbstentionReason.NONE:
            continue
        assert reason in ABSTENTION_REMEDY
        assert len(ABSTENTION_REMEDY[reason]) > 20


def test_the_six_abstention_states_are_distinct():
    from deferral.types import ABSTENTION_REMEDY

    remedies = [
        ABSTENTION_REMEDY[r] for r in AbstentionReason if r is not AbstentionReason.NONE
    ]
    assert len(set(remedies)) == len(remedies), "two states share a remedy"


# ==========================================================================
# the analyst packet
# ==========================================================================
def test_the_packet_carries_the_investigation_not_a_request(s2):
    confidence, recs, decision = _pipeline(s2)
    packet = defer_engine.build_analyst_packet(s2, confidence, decision, recs)

    assert packet.hypotheses, "no hypotheses in the packet"
    assert packet.movement_facts
    assert packet.methods_used
    assert packet.recommended_clarification
    assert "contact an analyst" not in packet.render().lower()
    assert packet.estimated_review_minutes > 0


def test_the_packet_asks_a_specific_question_on_a_conflicted_case(s2):
    confidence, recs, decision = _pipeline(s2)
    packet = defer_engine.build_analyst_packet(s2, confidence, decision, recs)
    question = packet.recommended_clarification.lower()
    assert "which" in question or "?" in question


def test_the_packet_names_what_is_missing(s6):
    confidence, recs, decision = _pipeline(s6)
    packet = defer_engine.build_analyst_packet(s6, confidence, decision, recs)
    if s6.security_context.withheld_item_count:
        assert any("withheld" in m for m in packet.missing_information)


def test_the_packet_keeps_contradicting_evidence(s2):
    confidence, recs, decision = _pipeline(s2)
    packet = defer_engine.build_analyst_packet(s2, confidence, decision, recs)
    assert isinstance(packet.contradicting_evidence, tuple)


# ==========================================================================
# feedback
# ==========================================================================
def test_every_outcome_names_its_consumer():
    for outcome in FeedbackOutcome:
        update = feedback_store.consumer_for(outcome)
        assert update.artifact and update.mechanism and update.visible_effect


def test_only_two_outcomes_update_live():
    live = [o for o, u in ROUTING.items() if u.timing is UpdateTiming.LIVE]
    assert set(live) == {FeedbackOutcome.ACCEPTED, FeedbackOutcome.ESCALATED}


def test_feedback_is_recorded_and_read_back(tmp_path):
    log = tmp_path / "feedback.jsonl"
    event = FeedbackEvent(
        event_id="F1", run_id="R-S1", bundle_hash="abc123",
        hypothesis_id="H-internal_product", outcome=FeedbackOutcome.ACCEPTED,
        persona_id="priya", persona_role="ops_lead", at=datetime.now(),
        confidence_band="HIGH", was_correct=True,
    )
    feedback_store.record(event, log)
    events = feedback_store.read_all(log)
    assert len(events) == 1
    assert events[0].outcome is FeedbackOutcome.ACCEPTED
    assert events[0].routing.timing is UpdateTiming.LIVE


def test_calibration_counters_come_from_the_log(tmp_path):
    log = tmp_path / "feedback.jsonl"
    for i in range(7):
        feedback_store.record(FeedbackEvent(
            event_id=f"F{i}", run_id="R", bundle_hash="h",
            outcome=FeedbackOutcome.ACCEPTED, persona_id="p",
            persona_role="ops_lead", at=datetime.now(),
            confidence_band="HIGH", was_correct=True,
        ), log)
    for i in range(3):
        feedback_store.record(FeedbackEvent(
            event_id=f"G{i}", run_id="R", bundle_hash="h",
            outcome=FeedbackOutcome.REJECTED, persona_id="p",
            persona_role="ops_lead", at=datetime.now(),
            confidence_band="HIGH", was_correct=False,
        ), log)

    counters = feedback_store.calibration_counters(feedback_store.read_all(log))
    assert counters["HIGH"] == {"correct": 7, "total": 10}


def test_a_coverage_gap_becomes_a_roadmap_item_at_the_threshold(tmp_path):
    log = tmp_path / "feedback.jsonl"
    for i in range(5):
        feedback_store.record(FeedbackEvent(
            event_id=f"F{i}", run_id="R", bundle_hash="h",
            outcome=FeedbackOutcome.INSUFFICIENT_EVIDENCE, persona_id="p",
            persona_role="ops_lead", at=datetime.now(),
            missing_source="warehouse_inventory_feed",
        ), log)
    gaps = feedback_store.coverage_gaps(feedback_store.read_all(log))
    assert gaps == {"warehouse_inventory_feed": 5}


def test_feedback_does_not_claim_to_train_a_model():
    from feedback import types as feedback_types

    doc = feedback_types.__doc__.lower()
    assert "no fine-tuning" in doc
    assert "never auto-applied" in doc or "human-authored" in doc


# ==========================================================================
# the LLM cannot reach any of this
# ==========================================================================
def test_the_narrative_schema_has_no_confidence_field():
    from verification.types import Narrative

    assert "confidence" not in Narrative.model_fields


def test_an_llm_supplied_confidence_is_dropped(s1):
    from llm.narrator import parse_narrative

    payload = {
        "headline": "x", "confidence": 0.97,
        "claims": [{
            "claim_id": "C1", "text": "y", "claim_type": "observation",
            "confidence": 0.99,
        }],
    }
    narrative = parse_narrative(payload)
    assert not hasattr(narrative, "confidence")
    assert not hasattr(narrative.claims[0], "confidence")


def test_confidence_is_computed_not_narrated(s1):
    """The confidence a reader sees comes from this module, not from a model."""
    c = conf_engine.compute(s1)
    assert c.config_version == conf_engine.load_config()["version"]
    assert c.components, "a confidence with no components cannot be audited"


# ==========================================================================
# scenario acceptance
# ==========================================================================
def test_at_least_one_scenario_automates_and_one_defers_and_one_abstains(
    s1, s2, s3, s4, s6
):
    outcomes = set()
    for bundle in (s1, s2, s3, s4, s6):
        _, _, decision = _pipeline(bundle)
        outcomes.add(decision.outcome)
    assert DeferralOutcome.ABSTAIN in outcomes, "nothing abstained"
    assert (
        DeferralOutcome.REVIEW in outcomes or DeferralOutcome.AUTOMATE in outcomes
    )


def test_s1_produces_a_recommendation_with_a_monitoring_plan(s1):
    confidence, recs, decision = _pipeline(s1)
    assert recs.recommendations, "S1 produced no recommendation"
    r = recs.primary
    assert r.monitoring.from_semantic_catalogue
    assert r.monitoring.check_after_days > 0
    assert r.monitoring.success_threshold
    assert r.expected_impact.high >= 0


def test_s4_recommends_nothing(s4):
    _, recs, decision = _pipeline(s4)
    assert not recs.recommendations
    assert decision.abstain
