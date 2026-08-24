"""Building ranked hypotheses from attribution and retrieval.

One hypothesis per plausible cause bucket, scored deterministically, ranked,
and then *separated* — the last step being the one that decides whether there
is a winner at all.

Nothing here generates prose. Statements come from a fixed template, because a
sentence a model wrote is a sentence that has to be verified, and there is no
reason to create that problem at the one point in the pipeline where the facts
are already exact.
"""

from __future__ import annotations

import statistics
from datetime import date

from attribution.types import AttributionResult, DriverStrength
from evidence import levers as levers_mod
from evidence import scoring
from evidence.types import (
    EvidenceProfile,
    EvidenceStance,
    EvidenceWeight,
    Hypothesis,
    HypothesisStatus,
    ScoreBreakdown,
)
from retrieval.types import (
    ContradictionDirection,
    RetrievalResult,
    SourceType,
)

# Which cause buckets a driver can plausibly belong to, and how each is
# phrased. Fixed and inspectable, exactly like the retrieval vocabularies -
# and deliberately the same bucket names, so a bucket that retrieval searched
# for is a bucket a hypothesis can be built from.
BUCKET_STATEMENTS: dict[str, str] = {
    "internal_product": "a product or platform failure in {slice}",
    "internal_inventory": "stock availability in {slice}",
    "internal_pricing": "a pricing or discounting change in {slice}",
    "internal_data_schema": "a data-definition change affecting {slice}",
    "external_competitor": "competitive pressure on {slice}",
    "external_market": "a market-wide movement affecting {slice}",
    "unknown": "an unidentified cause in {slice}",
}

BUCKET_NAMES: dict[str, str] = {
    "internal_product": "Product / platform failure",
    "internal_inventory": "Stock availability",
    "internal_pricing": "Pricing or discounting",
    "internal_data_schema": "Data-definition change",
    "external_competitor": "Competitive pressure",
    "external_market": "Market-wide movement",
    "unknown": "Unidentified cause",
}

# Which source types are evidence FOR which bucket. An exact mapping rather
# than a similarity judgement: a deploy record is evidence about the platform,
# a market event is evidence about competitors, and no amount of wording makes
# one the other.
BUCKET_EVIDENCE: dict[str, set[SourceType]] = {
    "internal_product": {SourceType.DEPLOY_CHANGELOG, SourceType.SUPPORT_TICKET},
    "internal_inventory": {SourceType.CRM_NOTE, SourceType.SUPPORT_TICKET},
    "internal_pricing": {SourceType.CRM_NOTE, SourceType.MARKET_EVENT},
    "internal_data_schema": {SourceType.SCHEMA_CHANGE},
    "external_competitor": {SourceType.MARKET_EVENT, SourceType.CRM_NOTE},
    "external_market": {SourceType.MARKET_EVENT},
    "unknown": set(),
}

# Keyword sets used to decide which retrieved document supports which bucket.
# Same vocabulary as retrieval's cause buckets, kept here rather than imported
# so the two can diverge deliberately if one needs to.
BUCKET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "internal_product": (
        "payment", "gateway", "checkout", "declined", "timeout", "card",
        "transaction", "error", "failed", "deploy", "rollback", "outage",
    ),
    "internal_inventory": (
        "stock", "stockout", "out of stock", "availability", "sku",
        "inventory", "replenish",
    ),
    "internal_pricing": ("price", "pricing", "discount", "promotion", "margin"),
    "internal_data_schema": (
        "schema", "renamed", "column", "backfill", "definition",
    ),
    "external_competitor": (
        "competitor", "rival", "promotion", "discounting", "price war",
        "festive",
    ),
    "external_market": ("market", "demand", "seasonal", "trade press", "category"),
    "unknown": (),
}


def bucket_alignment(
    bucket: str, present_types: set[SourceType]
) -> tuple[float, str]:
    """Does the evidence include the source types this cause REQUIRES?

    The strongest discriminator between competing explanations of one
    movement, and the reason is mechanical rather than semantic: a platform
    failure should leave a deploy record and support tickets; competitive
    pressure should leave market events. A cause whose characteristic evidence
    is absent is a cause someone is arguing for without support, however many
    documents happen to mention the topic.

    Returns (score in [0,1], reason).
    """
    expected = BUCKET_EVIDENCE.get(bucket, set())
    if not expected:
        # 'unknown' expects nothing, so it cannot be corroborated or refuted
        # this way. Neutral rather than zero: absence of expected evidence is
        # not evidence of absence when nothing was expected.
        return 0.5, "no characteristic evidence type defined for this cause"

    found = expected & present_types
    score = len(found) / len(expected)
    if not found:
        return 0.0, (
            f"none of the evidence types this cause would produce "
            f"({', '.join(sorted(t.value for t in expected))}) is present"
        )
    return score, (
        f"{len(found)}/{len(expected)} characteristic evidence type(s) present: "
        f"{', '.join(sorted(t.value for t in found))}"
    )


def _slice_tuple(slice_filter: dict) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted((k, "/".join(v) if isinstance(v, list) else str(v))
               for k, v in (slice_filter or {}).items())
    )


def _slice_label(slice_filter: dict) -> str:
    parts = [f"{k}={'/'.join(v) if isinstance(v, list) else v}"
             for k, v in sorted((slice_filter or {}).items())]
    return " x ".join(parts) if parts else "the overall business"


def _matches_bucket(text: str, bucket: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in BUCKET_KEYWORDS.get(bucket, ()))


# Deploy records whose summary reads like this are background noise: a
# changelog window contains one every few days regardless of what happened.
ROUTINE_MARKERS = ("routine release", "routine deploy", "scheduled release")


def _is_routine(item) -> bool:
    text = f"{item.title or ''} {item.excerpt}".lower()
    return any(m in text for m in ROUTINE_MARKERS)


def supports_bucket(item, bucket: str) -> bool:
    """Is this document evidence FOR this cause?

    A structured record counts on source type alone only if it is not routine.
    Without that qualifier every hypothesis in every scenario inherits the
    dozen "Routine release" rows that fall in any two-week window, which
    inflates the product hypothesis everywhere and is the opposite of evidence:
    a deploy that happens every three days tells you nothing about a movement
    that happened once.
    """
    if item.source_type in BUCKET_EVIDENCE.get(bucket, set()):
        if item.source_type is SourceType.DEPLOY_CHANGELOG and _is_routine(item):
            return False
        if item.source_type in (
            SourceType.DEPLOY_CHANGELOG,
            SourceType.SCHEMA_CHANGE,
        ):
            return True
    return _matches_bucket(f"{item.title or ''} {item.excerpt}", bucket)


def _temporal_tightness(
    dates: list[date], changepoint: date | None, window_days: int
) -> tuple[float, float | None]:
    """How tightly evidence clusters around the changepoint, in [0, 1]."""
    if not dates or changepoint is None:
        return 0.0, None
    gaps = [abs((d - changepoint).days) for d in dates]
    median_gap = float(statistics.median(gaps))
    tightness = max(0.0, 1.0 - median_gap / max(1, window_days))
    return tightness, median_gap


def candidate_buckets(
    attribution: AttributionResult, retrieval: RetrievalResult | None = None
) -> list[str]:
    """Which explanations are worth building for this movement.

    Driven by the dominant identity factor, exactly as retrieval's query
    buckets are, so that every bucket searched is a bucket that can be argued
    for or against.

    `internal_data_schema` is added whenever a schema change actually falls in
    the evidence window. It is not tied to a driver because a definition change
    can move any metric, and it is the one cause whose correct conclusion is
    "no business action" - so it has to be able to compete rather than being
    unreachable. Scenario 7 is the case: a channel rename that looks exactly
    like a 40% collapse until someone checks the changelog.
    """
    driver = (
        attribution.identity.dominant_driver if attribution.identity else None
    )
    from retrieval.engine import CAUSE_BUCKETS, GENERIC_BUCKET

    buckets = [b for b, _ in CAUSE_BUCKETS.get(driver or "", [GENERIC_BUCKET])]

    if retrieval is not None and any(
        item.source_type is SourceType.SCHEMA_CHANGE
        for item in retrieval.all_items
    ):
        if "internal_data_schema" not in buckets:
            buckets.append("internal_data_schema")
    return buckets


def build_hypotheses(
    attribution: AttributionResult,
    retrieval: RetrievalResult,
    *,
    persona_role: str,
    contract_allowed_levers: list[str] | None = None,
    history_days: int | None = None,
    has_stable_baseline: bool = True,
    config: dict | None = None,
) -> list[Hypothesis]:
    """One scored hypothesis per plausible cause bucket, ranked."""
    cfg = config or scoring.load_config()
    sep = cfg["separation"]
    tightness_window = cfg["evidence_fit"]["tightness_window_days"]

    movement = attribution.movement
    changepoint = movement.changepoint_date
    slice_filter = dict(retrieval.query.slice or attribution.slice or {})
    slice_label = _slice_label(slice_filter)

    driver_id = (
        attribution.identity.dominant_driver if attribution.identity else "unknown"
    )
    driver_contribution = None
    driver_share = None
    if attribution.identity:
        for d in attribution.identity.drivers:
            if d.driver == driver_id:
                driver_contribution = d.contribution
                driver_share = abs(d.contribution_pct) / 100.0
                break

    top = attribution.top_slice
    surprise = top.surprise if top else None
    # Surprise on a four-element dimension is numerically tiny (4e-4 on the
    # West event) while the paper's example reaches 0.14. Normalising against
    # a fixed constant would make every real hypothesis score ~0 on this
    # component, so it is normalised against the best surprise actually
    # observed in this attribution - a relative statement, which is what
    # "most surprising dimension" already means.
    all_surprises = [
        abs(d.surprise) for d in attribution.ranked_dimensions if d.surprise
    ]
    max_surprise = max(all_surprises) if all_surprises else 0.0

    robustness = attribution.robustness
    robustness_score = 0.0
    robustness_label = None
    if robustness:
        robustness_label = robustness.strength.value
        robustness_score = {
            DriverStrength.STRONG.value: 1.0,
            DriverStrength.WEAK.value: 0.5,
            DriverStrength.UNSTABLE.value: 0.0,
        }.get(robustness.strength.value, 0.0)

    counter = attribution.counterfactual
    precedence = bool(counter and counter.temporal_precedence)
    cf_passed = bool(counter and counter.passed)

    # contradiction signals from retrieval, split by direction
    contra_signals = [
        (s.contradiction_type.value, s.strength)
        for s in retrieval.contradictions
        if s.direction is ContradictionDirection.CONTRADICTS
    ]
    contradicting_ids: set[str] = set()
    for s in retrieval.contradictions:
        if s.direction is ContradictionDirection.CONTRADICTS:
            contradicting_ids.update(s.contradicting_evidence_ids)

    all_items = retrieval.all_items
    hypotheses: list[Hypothesis] = []

    for bucket in candidate_buckets(attribution, retrieval):
        wanted_types = BUCKET_EVIDENCE.get(bucket, set())
        supporting = [
            item
            for item in all_items
            if item.evidence_id not in contradicting_ids
            and supports_bucket(item, bucket)
        ]
        supporting_ids = tuple(sorted({i.evidence_id for i in supporting}))

        cohorts = [
            c
            for c in retrieval.cohorts
            if _matches_bucket(f"{c.label} {c.category or ''}", bucket)
        ]
        cohort_signal = 0.0
        for c in cohorts:
            if c.novel:
                cohort_signal = max(cohort_signal, 1.0)
            elif c.ratio is not None:
                cohort_signal = max(cohort_signal, min(1.0, (c.ratio - 1.0) / 3.0))

        total_docs = sum(1 + i.duplicate_count for i in supporting)
        duplicates = total_docs - len(supporting)
        source_types = tuple(sorted({i.source_type.value for i in supporting}))

        tightness, median_gap = _temporal_tightness(
            [i.timestamp.date() for i in supporting], changepoint, tightness_window
        )

        alignment, alignment_reason = bucket_alignment(
            bucket, {i.source_type for i in supporting}
        )
        support_score, _ = scoring.evidence_fit(
            bucket_alignment=alignment,
            distinct_documents=len(supporting),
            source_types=len(source_types),
            cohort_signal=cohort_signal,
            temporal_tightness=tightness,
            config=cfg,
        )

        # Only contradictions that bear on THIS bucket count against it. A
        # competing-explanation signal naming market events argues against the
        # product hypothesis, not against the competitor one - it is that
        # hypothesis's supporting evidence.
        bucket_contra = [
            (name, strength)
            for name, strength in contra_signals
            if not (name == "competing_explanation" and bucket.startswith("external"))
        ]
        bucket_contra_ids = tuple(sorted(
            i for i in contradicting_ids
            if not (bucket.startswith("external"))
        )) if bucket_contra else ()

        surprise_norm = (
            abs(surprise) / max_surprise if (surprise and max_surprise) else 0.0
        )

        score, breakdown = scoring.score_hypothesis(
            contribution_share=driver_share or 0.0,
            surprise_normalised=surprise_norm,
            robustness_score=robustness_score,
            temporal_precedence=precedence,
            counterfactual_passed=cf_passed,
            bucket_alignment=alignment,
            distinct_documents=len(supporting),
            source_types=len(source_types),
            cohort_signal=cohort_signal,
            temporal_tightness=tightness,
            contradiction_signals=bucket_contra,
            config=cfg,
        )

        quality = EvidenceWeight.WEAK
        if len(source_types) >= 2 and len(supporting) >= 3:
            quality = EvidenceWeight.STRONG
        elif supporting:
            quality = EvidenceWeight.MODERATE

        evidence_types = set(source_types)
        eligible = levers_mod.eligible_levers(
            cause_bucket=bucket,
            driver_id=driver_id,
            evidence_types=evidence_types,
            evidence_strength=support_score,
            causal_language_allowed=attribution.causal_language_licensed,
            has_stable_baseline=has_stable_baseline,
            history_days=history_days,
            contract_allowed_levers=contract_allowed_levers,
            persona_role=persona_role,
        )

        hypotheses.append(
            Hypothesis(
                hypothesis_id=f"H-{bucket}",
                statement=(
                    BUCKET_STATEMENTS.get(bucket, "an unidentified cause in {slice}")
                    .format(slice=slice_label)
                ),
                driver_id=driver_id,
                driver_name=driver_id.replace("_", " "),
                cause_bucket=bucket,
                dimension=top.dimension if top else None,
                slice=_slice_tuple(slice_filter),
                contribution=driver_contribution,
                contribution_share=driver_share,
                surprise=surprise,
                robustness=robustness_label,
                robustness_score=robustness_score,
                effect_size=(
                    attribution.movement.pct_delta / 100.0
                    if attribution.movement.pct_delta is not None
                    else None
                ),
                statistical_significance=None,   # see scoring.py: not a score input
                counterfactual=counter,
                temporal_precedence=precedence,
                causal_language_allowed=attribution.causal_language_licensed,
                causal_language_reason=attribution.causal_language_reason,
                supporting_evidence_ids=supporting_ids,
                contradicting_evidence_ids=bucket_contra_ids,
                cohort_ids=tuple(sorted(c.cohort_id for c in cohorts)),
                evidence_profile=EvidenceProfile(
                    distinct_documents=len(supporting),
                    total_documents=total_docs,
                    duplicate_documents=duplicates,
                    source_types=source_types,
                    cohort_count=len(cohorts),
                    contradiction_count=len(bucket_contra),
                    contradiction_strength=sum(s for _, s in bucket_contra),
                    temporal_tightness=tightness,
                    days_from_changepoint_median=median_gap,
                ),
                evidence_quality=quality,
                score=score,
                score_breakdown=ScoreBreakdown(**breakdown),
                eligible_lever_ids=tuple(l["lever_id"] for l, _ in eligible),
            )
        )

    hypotheses.sort(key=lambda h: (-h.score, h.hypothesis_id))
    reportable = [h for h in hypotheses if h.score >= sep["min_score_to_report"]]

    confidence = (
        hypotheses[0].score_breakdown.movement_confidence if hypotheses else 0.0
    )
    verdict, reason = scoring.separation_verdict(
        [h.score for h in reportable], confidence, cfg
    )

    kept = reportable[: sep["max_hypotheses"]]
    if verdict == "CONFLICTED":
        kept = reportable[
            : max(sep["min_hypotheses_when_conflicted"], min(len(reportable),
                                                             sep["max_hypotheses"]))
        ]

    final: list[Hypothesis] = []
    for i, h in enumerate(kept, start=1):
        if verdict == "SUPPORTED":
            status = (
                HypothesisStatus.SUPPORTED if i == 1 else HypothesisStatus.PLAUSIBLE
            )
        elif verdict == "CONFLICTED":
            status = HypothesisStatus.CONFLICTED
        elif verdict == "PLAUSIBLE":
            status = HypothesisStatus.PLAUSIBLE
        else:
            status = HypothesisStatus.INSUFFICIENT

        if (
            status is HypothesisStatus.SUPPORTED
            and h.evidence_count < sep["min_distinct_documents_for_supported"]
        ):
            status = HypothesisStatus.PLAUSIBLE
            reason = (
                f"{reason}; demoted to plausible because only "
                f"{h.evidence_count} distinct document(s) corroborate it"
            )

        # The counterfactual licensed a causal claim about the MOVEMENT: it
        # showed the drop was specific to this slice rather than market-wide.
        # It said nothing about WHICH cause. Letting a runner-up inherit that
        # licence would allow "competitive pressure caused the decline" off a
        # single CRM note, which is precisely the claim the gate exists to
        # prevent. So the licence additionally requires that this hypothesis
        # is the one the evidence actually separated out.
        licensed = h.causal_language_allowed and status is HypothesisStatus.SUPPORTED
        licence_reason = (
            h.causal_language_reason
            if licensed
            else (
                f"the counterfactual licensed a causal claim about the "
                f"movement, but this hypothesis is {status.value} rather than "
                f"SUPPORTED, so no cause may be asserted"
                if h.causal_language_allowed
                else h.causal_language_reason
            )
        )

        final.append(h.model_copy(update={
            "rank": i,
            "status": status,
            "status_reason": reason,
            "causal_language_allowed": licensed,
            "causal_language_reason": licence_reason,
        }))
    return final
