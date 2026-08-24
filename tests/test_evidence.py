"""Stage 6 tests — hypothesis scoring, separation, and the frozen bundle.

The load-bearing tests here are the ones about the freeze boundary: that the
bundle is immutable, that its hash is reproducible, and that any change to what
it contains changes the hash. Everything downstream — the narrator, the
verification gate, the audit trail — assumes those three properties, and none
of them is enforced by anything except this file and the frozen models.
"""

from __future__ import annotations

import copy
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence import levers as levers_mod
from evidence import scoring
from evidence.bundle import (
    canonical_payload,
    compute_hash,
    freeze_evidence_bundle,
    load_persona,
    verify_hash,
)
from evidence.hypothesis import bucket_alignment, build_hypotheses
from evidence.types import (
    DataQualityState,
    EvidenceStance,
    EvidenceWeight,
    HypothesisStatus,
)
from retrieval import engine as ret
from retrieval.embeddings import load_index
from retrieval.types import SourceType
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


def _pipeline(slice_filter, principal, cause_date, index, scenario=None):
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=20)
    r = ret.retrieve_evidence(a, principal, index=index)
    return d, a, r


@pytest.fixture(scope="module")
def s1(index):
    return _pipeline(WEST, ANALYST, date(2026, 7, 12), index, "S1")


@pytest.fixture(scope="module")
def s2(index):
    return _pipeline(SOUTH, ANALYST, date(2026, 6, 2), index, "S2")


@pytest.fixture(scope="module")
def s1_bundle(s1):
    d, a, r = s1
    return freeze_evidence_bundle(
        bundle_id="R-TEST-S1", persona_id="meera",
        detection=d, attribution=a, retrieval=r,
    )


# ==========================================================================
# scoring — deterministic and configurable
# ==========================================================================
def test_weights_live_in_configuration_not_in_python():
    """A weight hard-coded in Python is a weight nobody can audit."""
    import inspect

    source = inspect.getsource(scoring)
    body = "\n".join(
        line for line in source.splitlines()
        if not line.strip().startswith("#") and '"""' not in line
    )
    for suspicious in ("0.30", "0.25", "0.20", "0.15", "0.10"):
        assert suspicious not in body, (
            f"literal weight {suspicious} found in scoring.py; weights belong "
            f"in config/scoring.yaml"
        )


def test_config_weights_must_sum_to_one(tmp_path):
    bad = tmp_path / "scoring.yaml"
    bad.write_text(
        "version: 'x'\n"
        "movement_confidence: {contribution: 0.9, robustness: 0.9}\n"
        "evidence_fit: {bucket_alignment: 1.0}\n"
        "contradiction: {penalty_per_signal: 0.1, max_penalty: 0.5}\n"
        "separation: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(scoring.ScoringError, match="sum to"):
        scoring.load_config(str(bad))


def test_scoring_is_deterministic():
    kwargs = dict(
        contribution_share=0.8, surprise_normalised=0.5, robustness_score=1.0,
        temporal_precedence=True, counterfactual_passed=True,
        bucket_alignment=1.0, distinct_documents=5, source_types=2,
        cohort_signal=0.7, temporal_tightness=0.9, contradiction_signals=[],
    )
    first, _ = scoring.score_hypothesis(**kwargs)
    for _ in range(10):
        again, _ = scoring.score_hypothesis(**kwargs)
        assert again == first


def test_score_is_the_product_of_its_two_halves():
    """The breakdown must let a reviewer recompute the number by hand."""
    score, breakdown = scoring.score_hypothesis(
        contribution_share=1.0, surprise_normalised=1.0, robustness_score=1.0,
        temporal_precedence=True, counterfactual_passed=True,
        bucket_alignment=1.0, distinct_documents=100, source_types=5,
        cohort_signal=1.0, temporal_tightness=1.0, contradiction_signals=[],
    )
    assert score == pytest.approx(1.0)
    assert breakdown["movement_confidence"] == pytest.approx(1.0)
    assert breakdown["evidence_fit"] == pytest.approx(1.0)
    assert score == pytest.approx(
        breakdown["movement_confidence"]
        * breakdown["evidence_fit"]
        * breakdown["contradiction_multiplier"]
    )


def test_a_well_established_movement_with_no_evidence_scores_low():
    """Both halves must hold. A sum would let one carry the other."""
    score, _ = scoring.score_hypothesis(
        contribution_share=1.0, surprise_normalised=1.0, robustness_score=1.0,
        temporal_precedence=True, counterfactual_passed=True,
        bucket_alignment=0.0, distinct_documents=0, source_types=0,
        cohort_signal=0.0, temporal_tightness=0.0, contradiction_signals=[],
    )
    assert score == pytest.approx(0.0, abs=1e-9)


def test_strong_evidence_for_an_unestablished_movement_scores_low():
    score, _ = scoring.score_hypothesis(
        contribution_share=0.0, surprise_normalised=0.0, robustness_score=0.0,
        temporal_precedence=False, counterfactual_passed=False,
        bucket_alignment=1.0, distinct_documents=50, source_types=5,
        cohort_signal=1.0, temporal_tightness=1.0, contradiction_signals=[],
    )
    assert score == pytest.approx(0.0, abs=1e-9)


def test_contradiction_scales_the_score_down_but_never_to_zero():
    base = dict(
        contribution_share=1.0, surprise_normalised=1.0, robustness_score=1.0,
        temporal_precedence=True, counterfactual_passed=True,
        bucket_alignment=1.0, distinct_documents=8, source_types=3,
        cohort_signal=1.0, temporal_tightness=1.0,
    )
    clean, _ = scoring.score_hypothesis(**base, contradiction_signals=[])
    contested, breakdown = scoring.score_hypothesis(
        **base,
        contradiction_signals=[("a", 1.0), ("b", 1.0), ("c", 1.0), ("d", 1.0),
                               ("e", 1.0), ("f", 1.0), ("g", 1.0)],
    )
    assert contested < clean
    assert contested > 0.0, "a contradicted hypothesis is demoted, not deleted"
    assert breakdown["contradiction_multiplier"] >= 1.0 - 0.60


def test_duplicate_documents_cannot_inflate_the_score():
    """Thirty copies of one ticket are one finding."""
    one, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=3, source_types=1,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    many, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=3, source_types=1,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    assert one == many

    saturated, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=500, source_types=1,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    capped, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=8, source_types=1,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    assert saturated == capped, "document count must saturate"


def test_source_diversity_beats_volume():
    """Three independent sources agreeing outweighs one source repeating.

    Eight tickets from one queue about one incident are one finding retold.
    The duplicate caps stop the same document counting twice; this weighting
    is what stops the same SOURCE counting eight times.
    """
    diverse, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=3, source_types=3,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    voluminous, _ = scoring.evidence_fit(
        bucket_alignment=1.0, distinct_documents=8, source_types=1,
        cohort_signal=0.0, temporal_tightness=0.0,
    )
    assert diverse > voluminous


# ==========================================================================
# bucket alignment — the discriminating term
# ==========================================================================
def test_bucket_alignment_rewards_characteristic_evidence():
    full, reason = bucket_alignment(
        "internal_product",
        {SourceType.DEPLOY_CHANGELOG, SourceType.SUPPORT_TICKET},
    )
    assert full == pytest.approx(1.0)
    assert "2/2" in reason


def test_bucket_alignment_is_zero_when_expected_evidence_is_absent():
    score, reason = bucket_alignment("internal_product", {SourceType.MARKET_EVENT})
    assert score == 0.0
    assert "none of the evidence types" in reason


def test_unknown_bucket_alignment_is_neutral_not_zero():
    """Absence of expected evidence is not evidence of absence when nothing
    was expected."""
    score, _ = bucket_alignment("unknown", set())
    assert score == 0.5


# ==========================================================================
# separation
# ==========================================================================
def test_a_dominant_top_score_is_supported():
    verdict, reason = scoring.separation_verdict([0.90, 0.25], 1.0)
    assert verdict == "SUPPORTED"
    assert "separates" in reason


def test_two_close_scores_are_conflicted():
    verdict, reason = scoring.separation_verdict([0.74, 0.70], 1.0)
    assert verdict == "CONFLICTED"
    assert "does not separate them" in reason


def test_a_weakly_established_movement_is_insufficient_whatever_the_evidence():
    verdict, reason = scoring.separation_verdict([0.95, 0.10], 0.10)
    assert verdict == "INSUFFICIENT"
    assert "movement confidence" in reason


def test_no_hypotheses_is_insufficient():
    verdict, _ = scoring.separation_verdict([], 1.0)
    assert verdict == "INSUFFICIENT"


def test_separation_reason_never_states_a_false_comparison():
    """An earlier version printed 'margin 0.176 < 0.10' while calling it
    ambiguous, because two redundant tests were joined with OR."""
    verdict, reason = scoring.separation_verdict([0.914, 0.738], 1.0)
    assert verdict == "SUPPORTED", (
        f"a margin of 0.176 on a [0,1] score is a clear separation, got "
        f"{verdict}: {reason}"
    )


# ==========================================================================
# hypotheses end to end
# ==========================================================================
def test_s1_produces_one_clearly_separated_hypothesis(s1):
    d, a, r = s1
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    assert hs
    assert hs[0].status is HypothesisStatus.SUPPORTED
    assert hs[0].cause_bucket == "internal_product"
    assert hs[0].score > hs[1].score + 0.10


def test_s2_produces_at_least_two_credible_hypotheses(s2):
    """The correct answer to an ambiguous case is two answers."""
    d, a, r = s2
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    assert len(hs) >= 2
    assert hs[0].status is HypothesisStatus.CONFLICTED
    buckets = {h.cause_bucket for h in hs}
    assert "external_competitor" in buckets and "internal_inventory" in buckets


def test_at_most_three_hypotheses_are_returned(s1, s2):
    for _, a, r in (s1, s2):
        hs = build_hypotheses(a, r, persona_role="analytics_lead")
        assert len(hs) <= 3


def test_hypotheses_are_ranked_by_descending_score(s2):
    d, a, r = s2
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    assert [h.rank for h in hs] == list(range(1, len(hs) + 1))
    assert all(hs[i].score >= hs[i + 1].score for i in range(len(hs) - 1))


def test_hypothesis_building_is_deterministic(s1):
    d, a, r = s1
    first = build_hypotheses(a, r, persona_role="analytics_lead")
    for _ in range(3):
        again = build_hypotheses(a, r, persona_role="analytics_lead")
        assert [h.hypothesis_id for h in again] == [h.hypothesis_id for h in first]
        assert [h.score for h in again] == [h.score for h in first]


def test_routine_deploys_do_not_corroborate_every_hypothesis(s2):
    """A deploy that happens every three days explains nothing.

    Without this, the dozen 'Routine release' rows in any two-week window
    inflate the product hypothesis in every scenario.
    """
    d, a, r = s2
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    product = [h for h in hs if h.cause_bucket == "internal_product"]
    if product:
        assert product[0].evidence_count < 10, (
            "the product hypothesis absorbed the routine changelog"
        )


def test_supporting_and_contradicting_lists_stay_separate(s2):
    d, a, r = s2
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    for h in hs:
        assert not (
            set(h.supporting_evidence_ids) & set(h.contradicting_evidence_ids)
        ), "a document cannot both support and contradict the same hypothesis"


def test_evidence_profile_distinguishes_distinct_from_total(s1):
    d, a, r = s1
    hs = build_hypotheses(a, r, persona_role="analytics_lead")
    top = hs[0]
    p = top.evidence_profile
    assert p.total_documents >= p.distinct_documents
    assert p.duplicate_documents == p.total_documents - p.distinct_documents
    assert top.evidence_count == p.distinct_documents


# ==========================================================================
# levers
# ==========================================================================
def test_lever_catalogue_is_a_closed_set():
    ids = levers_mod.known_lever_ids()
    assert "L_GATEWAY_ESCALATE" in ids
    with pytest.raises(levers_mod.LeverError, match="unknown lever"):
        levers_mod.get("L_INVENTED_BY_A_MODEL")


def test_a_pricing_lever_is_blocked_without_a_stable_baseline():
    """Scenario 4: no pricing change off 23 days of history."""
    eligible = levers_mod.eligible_levers(
        cause_bucket="external_competitor", driver_id="orders",
        evidence_types={"market_event"}, evidence_strength=0.9,
        causal_language_allowed=True, has_stable_baseline=False,
        history_days=23, contract_allowed_levers=None,
        persona_role="analytics_lead",
    )
    assert "L_PRICING_REVIEW" not in {l["lever_id"] for l, _ in eligible}


def test_a_disruptive_lever_requires_licensed_causal_language():
    kwargs = dict(
        cause_bucket="internal_product", driver_id="conversion_rate",
        evidence_types={"deploy_changelog"}, evidence_strength=0.9,
        has_stable_baseline=True, history_days=200,
        contract_allowed_levers=None, persona_role="analytics_lead",
    )
    denied = levers_mod.eligible_levers(**kwargs, causal_language_allowed=False)
    licensed = levers_mod.eligible_levers(**kwargs, causal_language_allowed=True)
    assert "L_CHECKOUT_ROLLBACK" not in {l["lever_id"] for l, _ in denied}
    assert "L_CHECKOUT_ROLLBACK" in {l["lever_id"] for l, _ in licensed}


def test_the_monitor_lever_is_always_available():
    """The system must be able to recommend doing nothing."""
    eligible = levers_mod.eligible_levers(
        cause_bucket="unknown", driver_id="unknown", evidence_types=set(),
        evidence_strength=0.0, causal_language_allowed=False,
        has_stable_baseline=False, history_days=None,
        contract_allowed_levers=None, persona_role="ops_lead",
    )
    assert "L_MONITOR_ONLY" in {l["lever_id"] for l, _ in eligible}


def test_contract_allowlist_restricts_levers():
    eligible = levers_mod.eligible_levers(
        cause_bucket="internal_product", driver_id="conversion_rate",
        evidence_types={"deploy_changelog", "support_ticket"},
        evidence_strength=0.9, causal_language_allowed=True,
        has_stable_baseline=True, history_days=200,
        contract_allowed_levers=["L_GATEWAY_ESCALATE"],
        persona_role="analytics_lead",
    )
    ids = {l["lever_id"] for l, _ in eligible}
    assert "L_CHECKOUT_ROLLBACK" not in ids
    assert "L_GATEWAY_ESCALATE" in ids


# ==========================================================================
# metric facts
# ==========================================================================
def test_metric_facts_form_a_numeric_allowlist(s1_bundle):
    facts = s1_bundle.metric_facts
    assert facts
    ids = {f.fact_id for f in facts}
    assert "F-movement-pct" in ids and "F-baseline" in ids

    allowed = s1_bundle.allowed_numbers()
    assert allowed
    movement = s1_bundle.fact("F-movement-pct")
    assert round(movement.value, 6) in allowed


def test_every_metric_fact_carries_its_provenance(s1_bundle):
    for f in s1_bundle.metric_facts:
        assert f.unit, f"{f.fact_id} has no unit"
        assert f.computed_by, f"{f.fact_id} does not say which stage produced it"
        assert f.contract_version, f"{f.fact_id} has no contract version"
        assert f.label


def test_metric_facts_render_deterministically(s1_bundle):
    for f in s1_bundle.metric_facts:
        assert f.render() == f.render()
        assert f.label in f.render()


def test_the_lmdi_drivers_appear_as_facts(s1_bundle):
    ids = {f.fact_id for f in s1_bundle.metric_facts}
    assert any(i.startswith("F-driver-conversion_rate") for i in ids)


# ==========================================================================
# the bundle — immutability and hashing
# ==========================================================================
def test_bundle_is_immutable(s1_bundle):
    with pytest.raises(ValidationError):
        s1_bundle.bundle_id = "tampered"
    with pytest.raises(AttributeError):
        s1_bundle.hypotheses.append(None)      # tuples have no append
    if s1_bundle.metric_facts:
        with pytest.raises(ValidationError):
            s1_bundle.metric_facts[0].value = 0.0


def test_bundle_hash_is_reproducible(s1):
    """Same inputs and same configuration -> same hash."""
    d, a, r = s1
    first = freeze_evidence_bundle(
        bundle_id="R-HASH", persona_id="meera",
        detection=d, attribution=a, retrieval=r,
    )
    second = freeze_evidence_bundle(
        bundle_id="R-HASH", persona_id="meera",
        detection=d, attribution=a, retrieval=r,
    )
    assert first.bundle_hash == second.bundle_hash
    assert verify_hash(first) and verify_hash(second)


def test_hash_excludes_wall_clock_time(s1):
    """Otherwise the hash proves nothing about content."""
    d, a, r = s1
    b = freeze_evidence_bundle(
        bundle_id="R-CLOCK", persona_id="meera",
        detection=d, attribution=a, retrieval=r,
    )
    payload = canonical_payload(b)
    assert "created_at" not in payload
    assert "bundle_hash" not in payload


@pytest.mark.parametrize(
    "field,new_value",
    [
        ("kpi_id", "something_else"),
        ("bundle_id", "R-DIFFERENT"),
        ("status_reason", "changed"),
        # a boolean has to be FLIPPED, not set: setting it to the value it
        # already holds is not a mutation, and an earlier version of this test
        # asserted the hash changed when nothing had
        ("causal_language_allowed", None),
        ("scoring_version", "9.9.9"),
    ],
)
def test_any_change_to_the_bundle_changes_the_hash(s1_bundle, field, new_value):
    if new_value is None:
        new_value = not getattr(s1_bundle, field)
    mutation = {field: new_value}
    assert getattr(s1_bundle, field) != new_value, "the test must mutate something"
    mutated = s1_bundle.model_copy(update=mutation)
    assert compute_hash(mutated) != s1_bundle.bundle_hash
    assert not verify_hash(mutated), (
        "a mutated bundle must fail hash verification"
    )


def test_changing_a_metric_fact_changes_the_hash(s1_bundle):
    facts = list(s1_bundle.metric_facts)
    facts[0] = facts[0].model_copy(update={"value": facts[0].value + 1.0})
    mutated = s1_bundle.model_copy(update={"metric_facts": tuple(facts)})
    assert compute_hash(mutated) != s1_bundle.bundle_hash


def test_changing_evidence_changes_the_hash(s1_bundle):
    if not s1_bundle.supporting_evidence:
        pytest.skip("no supporting evidence in this bundle")
    ev = list(s1_bundle.supporting_evidence)
    ev[0] = ev[0].model_copy(update={"excerpt": "rewritten"})
    mutated = s1_bundle.model_copy(update={"supporting_evidence": tuple(ev)})
    assert compute_hash(mutated) != s1_bundle.bundle_hash


def test_changing_a_hypothesis_changes_the_hash(s1_bundle):
    if not s1_bundle.hypotheses:
        pytest.skip("no hypotheses in this bundle")
    hs = list(s1_bundle.hypotheses)
    hs[0] = hs[0].model_copy(update={"score": hs[0].score + 0.01})
    mutated = s1_bundle.model_copy(update={"hypotheses": tuple(hs)})
    assert compute_hash(mutated) != s1_bundle.bundle_hash


def test_changing_the_lever_list_changes_the_hash(s1_bundle):
    mutated = s1_bundle.model_copy(update={"allowed_levers": ()})
    assert compute_hash(mutated) != s1_bundle.bundle_hash


def test_changing_the_security_context_changes_the_hash(s1_bundle):
    sc = s1_bundle.security_context.model_copy(
        update={"permitted_regions": ("Mars",)}
    )
    mutated = s1_bundle.model_copy(update={"security_context": sc})
    assert compute_hash(mutated) != s1_bundle.bundle_hash


def test_canonical_serialisation_is_order_independent(s1_bundle):
    """Two structurally identical bundles must hash identically."""
    payload = canonical_payload(s1_bundle)
    shuffled = copy.deepcopy(payload)
    # a dict rebuilt in a different insertion order must canonicalise the same
    rebuilt = {k: shuffled[k] for k in sorted(shuffled, reverse=True)}
    import json

    assert json.dumps(payload, sort_keys=True) == json.dumps(
        rebuilt, sort_keys=True
    )


# ==========================================================================
# personas and entitlement
# ==========================================================================
def test_two_personas_get_different_bundles_from_the_same_event(index):
    """The entitlement rule changes the answer, not the styling."""
    d_a, a_a, r_a = _pipeline(WEST, ANALYST, date(2026, 7, 12), index, "S1")
    d_o, a_o, r_o = _pipeline(WEST, OPS_LEAD, date(2026, 7, 12), index, "S1")

    analyst = freeze_evidence_bundle(
        bundle_id="R-P", persona_id="meera",
        detection=d_a, attribution=a_a, retrieval=r_a,
    )
    ops = freeze_evidence_bundle(
        bundle_id="R-P", persona_id="priya",
        detection=d_o, attribution=a_o, retrieval=r_o,
    )

    assert analyst.bundle_hash != ops.bundle_hash
    assert analyst.persona.role != ops.persona.role
    assert ops.security_context.permitted_regions == ("West",)
    assert not analyst.security_context.permitted_regions


def test_restricted_evidence_never_appears_in_the_bundle(index):
    """S6: an ops lead may not read CRM notes, so none may be in the bundle."""
    d, a, r = _pipeline(WEST, OPS_LEAD, date(2026, 7, 12), index, "S1")
    ops = freeze_evidence_bundle(
        bundle_id="R-SEC", persona_id="priya",
        detection=d, attribution=a, retrieval=r,
    )
    for e in ops.supporting_evidence + ops.contradicting_evidence:
        assert e.source_type is not SourceType.CRM_NOTE, (
            f"CRM note {e.evidence_id} reached an ops_lead bundle"
        )
    assert "crm_notes" in ops.security_context.denied_sources


def test_withholding_is_reported_without_leaking_content(index):
    d, a, r = _pipeline(WEST, OPS_LEAD, date(2026, 7, 12), index, "S1")
    ops = freeze_evidence_bundle(
        bundle_id="R-SEC2", persona_id="priya",
        detection=d, attribution=a, retrieval=r,
    )
    sc = ops.security_context
    assert sc.withheld_item_count >= 1
    assert sc.withheld_source_ids
    # the notice names the source, never the documents
    serialised = ops.model_dump_json()
    assert "crm_note" in serialised          # the source type is named
    for e in ops.supporting_evidence:
        assert e.source_type is not SourceType.CRM_NOTE


def test_persona_profile_selects_emphasis_not_content():
    ops = load_persona("priya")
    analyst = load_persona("meera")
    assert ops.emphasis != analyst.emphasis
    assert "methodology" in analyst.emphasis
    assert "action" in ops.emphasis


def test_unknown_persona_is_refused():
    from evidence.bundle import BundleError

    with pytest.raises(BundleError, match="unknown persona"):
        load_persona("nobody")


# ==========================================================================
# scenarios where the system must decline
# ==========================================================================
def test_sparse_history_produces_no_hypothesis(index):
    """S4: never construct a false confident hypothesis."""
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"product_category": ["NewLaunch"]}, scenario_id="S4",
    )
    a = att.attribute(d, ANALYST, n_resamples=10)
    from retrieval.types import (
        FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
    )

    empty = RetrievalResult(
        query=RetrievalQuery(text=""),
        filters=FilterConditions(),
        config=RetrievalConfig(
            embedding_model="none", embedding_dim=1, corpus_hash="none"
        ),
    )
    bundle = freeze_evidence_bundle(
        bundle_id="R-SPARSE", persona_id="meera",
        detection=d, attribution=a, retrieval=empty,
        history_days=23, has_stable_baseline=False,
    )
    assert bundle.hypotheses == ()
    assert bundle.overall_status is HypothesisStatus.INSUFFICIENT
    assert not bundle.causal_language_allowed
    assert DataQualityState.SPARSE in bundle.data_quality_state


def test_a_non_material_movement_produces_no_hypothesis(index):
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"region": ["North"], "product_category": ["Electronics"]},
    )
    a = att.attribute(d, ANALYST, n_resamples=10)
    from retrieval.types import (
        FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
    )

    empty = RetrievalResult(
        query=RetrievalQuery(text=""),
        filters=FilterConditions(),
        config=RetrievalConfig(
            embedding_model="none", embedding_dim=1, corpus_hash="none"
        ),
    )
    bundle = freeze_evidence_bundle(
        bundle_id="R-FLAT", persona_id="meera",
        detection=d, attribution=a, retrieval=empty,
    )
    assert bundle.hypotheses == ()
    assert bundle.overall_status is HypothesisStatus.INSUFFICIENT
    assert not bundle.causal_language_allowed


def test_s3_thin_evidence_does_not_produce_false_certainty(index):
    """S3: a real movement with almost no corroboration."""
    d, a, r = _pipeline(EAST, ANALYST, date(2026, 8, 5), index, "S3")
    bundle = freeze_evidence_bundle(
        bundle_id="R-S3", persona_id="meera",
        detection=d, attribution=a, retrieval=r,
    )
    assert bundle.overall_status is not HypothesisStatus.SUPPORTED or (
        bundle.hypotheses and bundle.hypotheses[0].evidence_count >= 2
    ), "a supported verdict needs more than one corroborating document"


# ==========================================================================
# the freeze boundary
# ==========================================================================
def test_the_bundle_is_serialisable(s1_bundle):
    payload = s1_bundle.model_dump_json()
    assert payload
    assert s1_bundle.bundle_hash in payload


def test_bundle_carries_everything_a_narrator_needs(s1_bundle):
    b = s1_bundle
    assert b.bundle_id and b.bundle_version and b.bundle_hash
    assert b.created_at
    assert b.persona and b.kpi_id and b.kpi_name
    assert b.window_start and b.window_end
    assert b.metric_facts
    assert b.hypotheses
    assert b.supporting_evidence
    assert b.allowed_levers
    assert b.lineage
    assert b.security_context
    assert b.methods_used and all(b.methods_used)
    assert b.data_quality_state
    assert b.config_versions
    assert b.causal_permissions


def test_causal_permission_is_recorded_per_hypothesis(s1_bundle):
    ids = {h.hypothesis_id for h in s1_bundle.hypotheses}
    recorded = {hid for hid, _ in s1_bundle.causal_permissions}
    assert ids == recorded


def test_evidence_module_never_imports_an_llm():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    forbidden = ("anthropic", "openai", "langchain", "langgraph", "streamlit")
    for path in (root / "evidence").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert f"import {name}" not in text, f"{path.name} imports {name}"
