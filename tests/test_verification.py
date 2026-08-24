"""Stage 7 tests — Gate 2.

The important tests in this file are the ten hand-written corrupt narratives
in `TestCorruptedNarratives`. They are written as an adversary would write
them: plausible, fluent, and wrong in exactly one way each. None of them was
derived from the checker's implementation — each states a specific lie, and the
test asserts that Gate 2 names that lie.

A verifier tested only against narratives its own code produced is a verifier
tested against itself.
"""

from __future__ import annotations

from datetime import date

import pytest

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from evidence.types import HypothesisStatus
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window
from verification import causal as causal_check
from verification import direction as direction_check
from verification import numeric as numeric_check
from verification.engine import (
    build_deterministic_narrative,
    narrative_hash,
    verify_narrative,
)
from verification.types import (
    Claim,
    ClaimType,
    Narrative,
    Severity,
    ViolationCode,
)

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


@pytest.fixture(scope="module")
def index():
    return load_index()


def _bundle(slice_filter, principal, persona_id, cause_date, index,
            scenario=None, **kw):
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=20)
    r = ret.retrieve_evidence(a, principal, index=index)
    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario or 'X'}", persona_id=persona_id,
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
def s6_ops(index):
    return _bundle(WEST, OPS_LEAD, "priya", date(2026, 7, 12), index, "S1")


def codes(report) -> set[ViolationCode]:
    return {v.code for v in report.violations}


# ==========================================================================
# the deterministic narrative
# ==========================================================================
def test_the_deterministic_narrative_passes_its_own_verifier(s1):
    """If the mechanically faithful narrative fails, the gate is wrong."""
    narrative = build_deterministic_narrative(s1)
    report = verify_narrative(s1, narrative)
    assert report.passed, report.explain()
    assert report.hard_violation_count == 0


@pytest.mark.parametrize("fixture_name", ["s1", "s2", "s3"])
def test_deterministic_narratives_pass_on_every_scenario(fixture_name, request):
    bundle = request.getfixturevalue(fixture_name)
    report = verify_narrative(bundle, build_deterministic_narrative(bundle))
    assert report.passed, report.explain()


def test_the_deterministic_narrative_is_reproducible(s1):
    first = build_deterministic_narrative(s1)
    second = build_deterministic_narrative(s1)
    assert narrative_hash(first) == narrative_hash(second)
    assert first.claims == second.claims


def test_the_deterministic_narrative_is_labelled_as_such(s1):
    n = build_deterministic_narrative(s1)
    assert n.generated_deterministically
    assert verify_narrative(s1, n).mode == "deterministic_template"


def test_it_states_what_changed_and_the_driver(s1):
    n = build_deterministic_narrative(s1)
    types = {c.claim_type for c in n.claims}
    assert ClaimType.OBSERVATION in types
    assert ClaimType.ATTRIBUTION in types
    assert n.headline


def test_it_carries_a_caveat_when_causal_language_is_denied(s2):
    """S2 is CONFLICTED, so no hypothesis is licensed."""
    n = build_deterministic_narrative(s2)
    joined = " ".join(n.caveats).lower()
    assert "association" in joined or "not an established cause" in joined


def test_it_names_alternatives_when_they_exist(s2):
    n = build_deterministic_narrative(s2)
    uncertainty = [c for c in n.claims if c.claim_type is ClaimType.UNCERTAINTY]
    assert uncertainty
    assert any("alternative" in c.text.lower() for c in uncertainty)


def test_an_insufficient_bundle_produces_an_abstention_not_a_story(index):
    """S4: sparse history must not become an explanation."""
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"product_category": ["NewLaunch"]}, scenario_id="S4",
    )
    a = att.attribute(d, ANALYST, n_resamples=10)
    from retrieval.types import (
        FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
    )

    empty = RetrievalResult(
        query=RetrievalQuery(text=""), filters=FilterConditions(),
        config=RetrievalConfig(
            embedding_model="none", embedding_dim=1, corpus_hash="none"
        ),
    )
    bundle = freeze_evidence_bundle(
        bundle_id="R-S4", persona_id="meera", detection=d, attribution=a,
        retrieval=empty, history_days=23, has_stable_baseline=False,
    )
    n = build_deterministic_narrative(bundle)

    assert not any(c.claim_type is ClaimType.CAUSAL for c in n.claims)
    assert any(c.claim_type is ClaimType.UNCERTAINTY for c in n.claims)
    assert not n.recommendation_ids
    assert "abstention" in " ".join(n.caveats).lower()
    assert verify_narrative(bundle, n).passed


# ==========================================================================
# TEN HAND-WRITTEN CORRUPT NARRATIVES
#
# Each is written as a plausible piece of analyst prose containing exactly one
# lie. None was derived from the checker.
# ==========================================================================
class TestCorruptedNarratives:

    def test_A_invented_number(self, s1):
        """A figure that appears nowhere in the bundle."""
        bad = Narrative(
            headline="Net Revenue fell sharply in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "Net Revenue in region=West declined by 41.70% over "
                        "the period, a shortfall of 1,204,880 INR."
                    ),
                    claim_type=ClaimType.OBSERVATION,
                    metric_refs=("F-movement-pct",),
                    direction="down",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.UNGROUNDED_NUMBER in codes(report)
        offenders = {
            v.offending_value for v in report.by_code(ViolationCode.UNGROUNDED_NUMBER)
        }
        assert "41.70" in offenders or "41.7" in offenders

    def test_B_wrong_driver(self, s1):
        """A hypothesis id the analysis never produced."""
        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text="The decline is explained by a courier strike.",
                    claim_type=ClaimType.ATTRIBUTION,
                    hypothesis_id="H-logistics_disruption",
                    evidence_ids=(),
                    metric_refs=("F-movement-pct",),
                    direction="down",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.UNKNOWN_DRIVER in codes(report)

    def test_C_wrong_direction(self, s1):
        """Says revenue improved when it fell."""
        bad = Narrative(
            headline="Net Revenue improved in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "Net Revenue rose over the period and conversion "
                        "improved alongside it."
                    ),
                    claim_type=ClaimType.OBSERVATION,
                    metric_refs=("F-movement-pct",),
                    direction="up",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.DIRECTION_MISMATCH in codes(report)

    def test_D_missing_evidence(self, s1):
        """A substantive claim citing nothing at all."""
        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "Payment failures increased sharply during the "
                        "incident window."
                    ),
                    claim_type=ClaimType.OBSERVATION,
                    evidence_ids=(),
                    metric_refs=(),
                    direction="up",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.MISSING_EVIDENCE in codes(report)

    def test_E_invalid_evidence_id(self, s1):
        """A citation that resolves to nothing."""
        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text="Support tickets recorded repeated payment failures.",
                    claim_type=ClaimType.OBSERVATION,
                    evidence_ids=("T99999", "TICKET-DOES-NOT-EXIST"),
                    direction="up",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.INVALID_EVIDENCE_ID in codes(report)
        assert len(report.by_code(ViolationCode.INVALID_EVIDENCE_ID)) == 2

    def test_F_dominant_driver_omitted(self, s1):
        """Every sentence true; the narrative still misleads by selection."""
        assert s1.hypotheses[0].status is HypothesisStatus.SUPPORTED
        weaker = [
            h for h in s1.hypotheses if h.hypothesis_id != s1.hypotheses[0].hypothesis_id
        ]
        assert weaker, "this test needs a runner-up to talk about instead"

        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "The movement is consistent with competitive pressure "
                        "in the affected slice."
                    ),
                    claim_type=ClaimType.ATTRIBUTION,
                    hypothesis_id=weaker[0].hypothesis_id,
                    metric_refs=("F-movement-pct",),
                    direction="down",
                ),
            ),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.DOMINANT_DRIVER_OMITTED in codes(report)

    def test_G_unsupported_causal_claim(self, s2):
        """S2 is CONFLICTED, so no cause may be asserted for it."""
        top = s2.hypotheses[0]
        assert not top.causal_language_allowed

        bad = Narrative(
            headline="Competitor pricing hit Apparel in the South",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "Competitor pricing caused the decline in Apparel "
                        "revenue across the South."
                    ),
                    claim_type=ClaimType.CAUSAL,
                    hypothesis_id=top.hypothesis_id,
                    evidence_ids=top.supporting_evidence_ids[:1],
                    metric_refs=("F-movement-pct",),
                    direction="down",
                ),
            ),
        )
        report = verify_narrative(s2, bad)
        assert not report.passed
        assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED in codes(report)

    def test_H_valid_causal_claim_is_allowed(self, s1):
        """The gate must not simply block everything."""
        top = s1.hypotheses[0]
        assert top.causal_language_allowed, (
            "S1's top hypothesis should carry the causal licence"
        )
        good = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text=(
                        "A product or platform failure caused the decline in "
                        "the affected slice."
                    ),
                    claim_type=ClaimType.CAUSAL,
                    hypothesis_id=top.hypothesis_id,
                    evidence_ids=top.supporting_evidence_ids[:2],
                    metric_refs=("F-movement-pct",),
                    direction="down",
                ),
            ),
        )
        report = verify_narrative(s1, good)
        assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED not in codes(report)
        assert report.passed, report.explain()

    def test_I_unauthorised_evidence_id(self, s6_ops, s1):
        """A real CRM note, cited in an ops lead's narrative.

        The document exists in the database and is genuinely relevant. The
        ops lead may not read it, so citing it is a leak even though nothing
        is quoted from it.
        """
        from retrieval.types import SourceType

        crm = [
            e for e in s1.supporting_evidence
            if e.source_type is SourceType.CRM_NOTE
        ]
        if not crm:
            pytest.skip("no CRM note in the analyst bundle to borrow")

        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text="An account escalation recorded repeated failures.",
                    claim_type=ClaimType.OBSERVATION,
                    evidence_ids=(crm[0].evidence_id,),
                    direction="up",
                ),
            ),
        )
        report = verify_narrative(s6_ops, bad)
        assert not report.passed
        assert (
            ViolationCode.RESTRICTED_EVIDENCE in codes(report)
            or ViolationCode.INVALID_EVIDENCE_ID in codes(report)
        ), "citing a restricted document must fail"

    def test_J_invented_lever(self, s1):
        """A business action nobody approved."""
        bad = Narrative(
            headline="Net Revenue fell in the West",
            claims=(
                Claim(
                    claim_id="X1",
                    text="Issue refunds to all affected customers immediately.",
                    claim_type=ClaimType.RECOMMENDATION,
                    lever_id="L_BLANKET_REFUND",
                ),
            ),
            recommendation_ids=("L_BLANKET_REFUND",),
        )
        report = verify_narrative(s1, bad)
        assert not report.passed
        assert ViolationCode.UNKNOWN_LEVER in codes(report)
        assert len(report.by_code(ViolationCode.UNKNOWN_LEVER)) == 2


# ==========================================================================
# numeric allowlist
# ==========================================================================
def test_allowed_numbers_come_from_the_bundle(s1):
    allowed = numeric_check.allowed_numbers(s1)
    movement = s1.fact("F-movement-pct")
    assert any(abs(movement.value - a) < 1e-6 for a in allowed)
    assert any(abs(abs(movement.value) - a) < 1e-6 for a in allowed)


def test_rounding_tolerance_accepts_a_readable_rounding(s1):
    movement = s1.fact("F-movement-pct")          # e.g. -27.22
    allowed = numeric_check.allowed_numbers(s1)
    rounded = round(abs(movement.value), 1)       # 27.2
    assert numeric_check.matches_any(rounded, allowed)


def test_rounding_tolerance_rejects_a_materially_different_number(s1):
    allowed = numeric_check.allowed_numbers(s1)
    movement = s1.fact("F-movement-pct")
    wrong = abs(movement.value) * 1.5
    assert not numeric_check.matches_any(wrong, allowed)


def test_tolerance_is_half_a_percent_with_a_floor():
    assert numeric_check.tolerance_for(1000.0) == pytest.approx(5.0)
    assert numeric_check.tolerance_for(0.1) == pytest.approx(0.05)


def test_dates_are_not_read_as_quantities(s1):
    """2026-07-12 must not decompose into 2026, 7 and 12."""
    stripped = numeric_check.strip_dates("between 2026-07-12 and 2026-07-26")
    assert "2026" not in stripped and "12" not in stripped


def test_an_invented_date_is_caught(s1):
    bad = Narrative(
        headline="x",
        claims=(
            Claim(
                claim_id="X1",
                text="The incident began on 2019-03-04.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",),
            ),
        ),
    )
    report = verify_narrative(s1, bad)
    assert ViolationCode.UNGROUNDED_DATE in codes(report)


def test_a_real_date_from_the_bundle_is_accepted(s1):
    good_date = s1.window_start.isoformat()
    bad = Narrative(
        headline="x",
        claims=(
            Claim(
                claim_id="X1",
                text=f"The window opens on {good_date}.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",),
            ),
        ),
    )
    report = verify_narrative(s1, bad)
    assert ViolationCode.UNGROUNDED_DATE not in codes(report)


# ==========================================================================
# direction
# ==========================================================================
def test_direction_words_are_detected():
    assert direction_check.words_in("revenue declined sharply") == "down"
    assert direction_check.words_in("conversion improved") == "up"


def test_a_mixed_sentence_is_not_forced_into_one_direction():
    """'Conversion fell while sessions rose' is legitimate."""
    assert direction_check.words_in("conversion fell while sessions rose") is None


def test_prose_contradicting_the_structured_field_is_caught(s1):
    bad = Narrative(
        headline="x",
        claims=(
            Claim(
                claim_id="X1",
                text="Revenue increased over the window.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=(),
                evidence_ids=(),
                direction="down",
            ),
        ),
    )
    report = verify_narrative(s1, bad)
    assert ViolationCode.DIRECTION_MISMATCH in codes(report)


# ==========================================================================
# causal licence
# ==========================================================================
def test_causal_verbs_are_detected():
    assert causal_check.causal_phrases("the change caused the drop")
    assert causal_check.causal_phrases("revenue fell due to the outage")
    assert causal_check.causal_phrases("the deploy triggered failures")
    assert not causal_check.causal_phrases("revenue fell during the window")


def test_associative_phrasing_is_permitted(s2):
    """S2's correct wording: a contributor, not an established cause."""
    top = s2.hypotheses[0]
    good = Narrative(
        headline="Two explanations remain open for Apparel in the South",
        claims=(
            Claim(
                claim_id="X1",
                text=(
                    "Competitive pressure is one plausible contributor, but "
                    "the available evidence does not establish causality."
                ),
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=top.hypothesis_id,
                evidence_ids=top.supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
        ),
    )
    report = verify_narrative(s2, good)
    assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED not in codes(report), (
        report.explain()
    )


def test_a_causal_verb_with_no_hypothesis_reference_is_blocked(s1):
    """Otherwise omitting the reference is the way past the gate."""
    bad = Narrative(
        headline="x",
        claims=(
            Claim(
                claim_id="X1",
                text="The outage caused the revenue decline.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
        ),
    )
    report = verify_narrative(s1, bad)
    assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED in codes(report)


def test_a_licensed_hypothesis_does_not_license_a_runner_up(s1):
    """Per hypothesis, never per bundle."""
    licensed = [h for h in s1.hypotheses if h.causal_language_allowed]
    unlicensed = [h for h in s1.hypotheses if not h.causal_language_allowed]
    if not (licensed and unlicensed):
        pytest.skip("this bundle has no mixed licence state")

    bad = Narrative(
        headline="x",
        claims=(
            Claim(
                claim_id="X1",
                text="Competitive pressure caused the decline.",
                claim_type=ClaimType.CAUSAL,
                hypothesis_id=unlicensed[0].hypothesis_id,
                evidence_ids=unlicensed[0].supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
            Claim(
                claim_id="X2",
                text="A platform failure explains the movement.",
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=licensed[0].hypothesis_id,
                evidence_ids=licensed[0].supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
        ),
    )
    report = verify_narrative(s1, bad)
    violations = report.by_code(ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED)
    assert violations
    assert {v.claim_id for v in violations} == {"X1"}, (
        "only the unlicensed claim should fail"
    )


# ==========================================================================
# severity and the report
# ==========================================================================
def test_hard_violations_block_and_info_does_not(s1):
    report = verify_narrative(s1, build_deterministic_narrative(s1))
    assert report.passed
    assert report.info_violation_count >= 0
    assert all(v.severity is not Severity.HARD for v in report.violations)


def test_every_hard_code_carries_a_rationale():
    from verification.types import HARD_RATIONALE, SEVERITY, Severity as S

    for code, severity in SEVERITY.items():
        if severity is S.HARD:
            assert code in HARD_RATIONALE, f"{code} has no stated rationale"
            assert len(HARD_RATIONALE[code]) > 30


def test_the_report_is_serialisable(s1):
    report = verify_narrative(s1, build_deterministic_narrative(s1))
    payload = report.model_dump_json()
    assert report.bundle_hash in payload
    assert report.narrative_hash in payload


def test_the_report_names_what_it_verified(s1):
    narrative = build_deterministic_narrative(s1)
    report = verify_narrative(s1, narrative)
    assert report.bundle_hash == s1.bundle_hash
    assert report.narrative_hash == narrative_hash(narrative)
    assert report.verification_version
    assert len(report.checks_run) >= 9


# ==========================================================================
# determinism
# ==========================================================================
def test_verification_is_deterministic(s1):
    narrative = build_deterministic_narrative(s1)
    first = verify_narrative(s1, narrative)
    for _ in range(5):
        again = verify_narrative(s1, narrative)
        assert again.passed == first.passed
        assert again.violations == first.violations
        assert again.narrative_hash == first.narrative_hash
        assert again.checks_passed == first.checks_passed


def test_violation_order_is_stable(s1):
    bad = Narrative(
        headline="x",
        claims=(
            Claim(claim_id="Z1", text="Revenue rose by 999.99%.",
                  claim_type=ClaimType.OBSERVATION, direction="up"),
            Claim(claim_id="A1", text="Caused by a courier strike.",
                  claim_type=ClaimType.CAUSAL, hypothesis_id="H-nonexistent"),
        ),
        recommendation_ids=("L_MADE_UP",),
    )
    first = verify_narrative(s1, bad)
    for _ in range(3):
        again = verify_narrative(s1, bad)
        assert [v.code for v in again.violations] == [
            v.code for v in first.violations
        ]


def test_narrative_hash_changes_when_the_narrative_changes(s1):
    a = build_deterministic_narrative(s1)
    b = a.model_copy(update={"headline": a.headline + " (revised)"})
    assert narrative_hash(a) != narrative_hash(b)


# ==========================================================================
# scenario expectations
# ==========================================================================
def test_s1_a_valid_narrative_passes_all_hard_checks(s1):
    assert verify_narrative(s1, build_deterministic_narrative(s1)).passed


def test_s2_causal_fails_but_associative_passes(s2):
    """The pair that shows the gate discriminates rather than blocks."""
    top = s2.hypotheses[0]
    common = dict(
        claim_id="X1", hypothesis_id=top.hypothesis_id,
        evidence_ids=top.supporting_evidence_ids[:1],
        metric_refs=("F-movement-pct",), direction="down",
    )
    causal = Narrative(
        headline="Apparel revenue fell in the South",
        claims=(Claim(
            text="Competitor pricing caused the decline.",
            claim_type=ClaimType.CAUSAL, **common
        ),),
    )
    associative = Narrative(
        headline="Apparel revenue fell in the South",
        claims=(Claim(
            text=(
                "Competitor pricing is one plausible contributor, but the "
                "available evidence does not establish causality."
            ),
            claim_type=ClaimType.ATTRIBUTION, **common
        ),),
    )
    assert not verify_narrative(s2, causal).passed
    assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED not in codes(
        verify_narrative(s2, associative)
    )


def test_s3_produces_an_abstention_style_narrative(s3):
    n = build_deterministic_narrative(s3)
    assert not any(c.claim_type is ClaimType.CAUSAL for c in n.claims)
    assert verify_narrative(s3, n).passed


def test_s6_restricted_evidence_cannot_appear(s6_ops):
    from retrieval.types import SourceType

    for ref in s6_ops.supporting_evidence + s6_ops.contradicting_evidence:
        assert ref.source_type is not SourceType.CRM_NOTE
    n = build_deterministic_narrative(s6_ops)
    assert verify_narrative(s6_ops, n).passed


def test_s7_schema_change_hypothesis_stays_traceable(s1):
    """When a schema-change hypothesis exists, its evidence is citable."""
    schema_hyps = [
        h for h in s1.hypotheses if h.cause_bucket == "internal_data_schema"
    ]
    if not schema_hyps:
        pytest.skip("no schema-change hypothesis in this bundle")
    h = schema_hyps[0]
    narrative = Narrative(
        headline="A data-definition change is in scope",
        claims=(
            Claim(
                claim_id="X1",
                text=(
                    "A data-definition change affecting the slice is one "
                    "explanation under consideration."
                ),
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=h.hypothesis_id,
                evidence_ids=h.supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
            Claim(
                claim_id="X2",
                text=(
                    "A product or platform failure remains the leading "
                    "explanation."
                ),
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=s1.hypotheses[0].hypothesis_id,
                evidence_ids=s1.hypotheses[0].supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",),
                direction="down",
            ),
        ),
    )
    report = verify_narrative(s1, narrative)
    assert ViolationCode.INVALID_EVIDENCE_ID not in codes(report), report.explain()


# ==========================================================================
# the boundary
# ==========================================================================
def test_verification_does_not_import_a_model_or_a_ui():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    forbidden = (
        "anthropic", "openai", "langchain", "langgraph", "streamlit", "duckdb",
    )
    for path in (root / "verification").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert f"import {name}" not in text, f"{path.name} imports {name}"


@pytest.mark.parametrize("fixture_name", ["s1", "s2", "s3"])
def test_the_template_never_cites_evidence_the_bundle_does_not_hold(
    fixture_name, request
):
    """Stage 13 regression: the template cited ids the bundle had dropped.

    A hypothesis records every evidence id that scored for or against it; the
    bundle keeps a top-k subset. The builder cited straight from the
    hypothesis, so on S2 it emitted three contradicting ids against one the
    bundle retained — and Gate 2 correctly blocked its own template as
    carrying citations "indistinguishable from a fabricated one".

    It had passed until then only because the sets happened to coincide. A
    wider document corpus separated them.
    """
    bundle = request.getfixturevalue(fixture_name)
    if bundle.hypotheses:
        name = fixture_name
        narrative = build_deterministic_narrative(bundle)
        held = {i.evidence_id for i in bundle.supporting_evidence}
        held |= {i.evidence_id for i in bundle.contradicting_evidence}
        held |= {c.cohort_id for c in bundle.cohorts}

        for claim in narrative.claims:
            for eid in claim.evidence_ids:
                assert eid in held, (
                    f"{name}: template cites {eid!r}, which is not in the "
                    f"bundle — Gate 2 would reject it as unresolvable"
                )
