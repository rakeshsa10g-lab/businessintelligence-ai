"""Deterministic contradiction signals (Architecture Part 10.4).

`contradicting_evidence` is a required field, not an optional nicety: a
hypothesis presented with zero contradicting evidence, by a system that never
looked for any, is a confirmation-bias machine. Making the search mandatory is
what produces the honest "two hypotheses, each with support and each with a
problem" view on Scenario 2 instead of a fake winner.

**No LLM here, and no semantic entailment model.** Every signal below is a
checkable property of dates, slices, directions or counts. If a reviewer
disagrees with one, they can recompute it. That is a much smaller claim than
"the model judged this contradictory", and unlike that claim it is true.

What is deliberately *not* implemented: natural-language contradiction between
two documents ("the ticket says the gateway recovered" vs "the note says it
was still failing"). That needs entailment, it would be a second analytical
engine, and pretending to it with keyword matching would be worse than
declining. The five typed signals here are the ones that survive scrutiny.
"""

from __future__ import annotations

from datetime import date

from retrieval.types import (
    CandidateHypothesis,
    CohortEvidence,
    ContradictionDirection,
    ContradictionSignal,
    ContradictionType,
    EvidenceItem,
    SourceType,
)

# A cohort ratio at or below this is evidence the cohort did NOT experience
# the signal the hypothesis needs it to have experienced.
FLAT_COHORT_RATIO = 1.2

# How strong each signal is, before any evidence-weighting. Temporal
# precedence is decisive - an effect cannot precede its cause - so it scores
# highest. The others are suggestive.
STRENGTH = {
    ContradictionType.CONSISTENT_WITH_HYPOTHESIS: 0.5,
    ContradictionType.TEMPORAL_PRECEDENCE_VIOLATED: 1.0,
    ContradictionType.UNAFFECTED_PEER_SAME_MOVEMENT: 0.8,
    ContradictionType.COHORT_NOT_AFFECTED: 0.7,
    ContradictionType.OPPOSITE_DIRECTION: 0.6,
    ContradictionType.COMPETING_EXPLANATION: 0.5,
}


def _slice_conflicts(item: EvidenceItem, slice_filter: dict[str, list[str]]) -> bool:
    """Does this document describe a slice the hypothesis excludes?"""
    for dim, values in slice_filter.items():
        value = getattr(item, dim, None)
        if value is not None and values and value not in values:
            return True
    return False


def temporal_precedence(
    hypothesis: CandidateHypothesis, evidence: list[EvidenceItem]
) -> list[ContradictionSignal]:
    """A candidate cause dated after the changepoint cannot be the cause.

    Trivial to check, embarrassing to miss, and the cheapest guard against the
    most common error in this domain.
    """
    if hypothesis.changepoint is None:
        return []

    late = [
        e for e in evidence if e.timestamp.date() > hypothesis.changepoint
    ]
    early = [
        e for e in evidence if e.timestamp.date() <= hypothesis.changepoint
    ]
    signals: list[ContradictionSignal] = []

    if hypothesis.cause_date and hypothesis.cause_date > hypothesis.changepoint:
        signals.append(
            ContradictionSignal(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_statement=hypothesis.statement,
                contradiction_type=ContradictionType.TEMPORAL_PRECEDENCE_VIOLATED,
                direction=ContradictionDirection.CONTRADICTS,
                strength=STRENGTH[ContradictionType.TEMPORAL_PRECEDENCE_VIOLATED],
                supporting_evidence_ids=[e.evidence_id for e in early],
                contradicting_evidence_ids=[e.evidence_id for e in late],
                detail=(
                    f"the proposed cause is dated {hypothesis.cause_date}, "
                    f"after the changepoint {hypothesis.changepoint}; it "
                    f"cannot have produced a movement that had already begun"
                ),
                checked=(
                    f"cause_date {hypothesis.cause_date} <= changepoint "
                    f"{hypothesis.changepoint}"
                ),
            )
        )
    return signals


def _is_relevant(cohort: CohortEvidence, hypothesis: CandidateHypothesis) -> bool:
    """Does this cohort bear on the hypothesis at all?

    Without this check every unrelated flat cohort produces a contradiction:
    "routine CRM notes ran at 0.97x baseline" is true, and says nothing
    whatever about a payment-gateway hypothesis. Flooding the panel with
    irrelevant contradictions is not rigour, it is noise that trains a reader
    to skip the section where the real disconfirming evidence lives.

    Relevance is keyword overlap against the hypothesis's own cause vocabulary
    — the same fixed, inspectable term list the query was built from.
    """
    if not hypothesis.keywords:
        return True
    haystack = f"{cohort.category or ''} {cohort.label}".lower()
    return any(k.lower() in haystack for k in hypothesis.keywords)


def cohort_not_affected(
    hypothesis: CandidateHypothesis, cohorts: list[CohortEvidence]
) -> list[ContradictionSignal]:
    """A cohort the hypothesis implies should have moved, and did not."""
    signals = []
    for cohort in cohorts:
        if cohort.ratio is None or not _is_relevant(cohort, hypothesis):
            continue
        if cohort.ratio <= FLAT_COHORT_RATIO:
            signals.append(
                ContradictionSignal(
                    hypothesis_id=hypothesis.hypothesis_id,
                    hypothesis_statement=hypothesis.statement,
                    contradiction_type=ContradictionType.COHORT_NOT_AFFECTED,
                    direction=ContradictionDirection.CONTRADICTS,
                    strength=STRENGTH[ContradictionType.COHORT_NOT_AFFECTED],
                    contradicting_evidence_ids=list(cohort.document_ids),
                    detail=(
                        f"{cohort.label} ran at {cohort.ratio:.2f}x the "
                        f"trailing baseline during the window - essentially "
                        f"flat. If this hypothesis were correct the affected "
                        f"cohort should show a rate change"
                    ),
                    checked=(
                        f"cohort ratio {cohort.ratio:.2f} <= "
                        f"{FLAT_COHORT_RATIO} flat threshold"
                    ),
                )
            )
    return signals


def unaffected_peer_moved(
    hypothesis: CandidateHypothesis,
    peer_moved: bool,
    peer_label: str | None,
    did_estimate_pct: float | None = None,
) -> list[ContradictionSignal]:
    """Another slice moved the same way without the alleged cause.

    Reads the counterfactual result Stage 4 already computed rather than
    recomputing it: if the difference-in-differences against a matched control
    came out near zero, the control moved too, and a slice-specific cause is
    the wrong shape of explanation.
    """
    if not peer_moved:
        return []
    return [
        ContradictionSignal(
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_statement=hypothesis.statement,
            contradiction_type=ContradictionType.UNAFFECTED_PEER_SAME_MOVEMENT,
            direction=ContradictionDirection.CONTRADICTS,
            strength=STRENGTH[ContradictionType.UNAFFECTED_PEER_SAME_MOVEMENT],
            detail=(
                f"control slice {peer_label} moved with the affected slice "
                f"(difference-in-differences "
                f"{did_estimate_pct:+.1f}% of the pre-period level), so the "
                f"movement is not specific to this slice and a cause local to "
                f"it does not explain the pattern"
                if did_estimate_pct is not None
                else f"control slice {peer_label} moved with the affected slice"
            ),
            checked="attribution counterfactual: DiD below the specificity floor",
        )
    ]


def opposite_direction(
    hypothesis: CandidateHypothesis, cohorts: list[CohortEvidence]
) -> list[ContradictionSignal]:
    """The evidence trend moves against the hypothesis."""
    signals = []
    for cohort in cohorts:
        if cohort.ratio is None or not _is_relevant(cohort, hypothesis):
            continue
        if cohort.ratio < 0.8:
            signals.append(
                ContradictionSignal(
                    hypothesis_id=hypothesis.hypothesis_id,
                    hypothesis_statement=hypothesis.statement,
                    contradiction_type=ContradictionType.OPPOSITE_DIRECTION,
                    direction=ContradictionDirection.CONTRADICTS,
                    strength=STRENGTH[ContradictionType.OPPOSITE_DIRECTION],
                    contradicting_evidence_ids=list(cohort.document_ids),
                    detail=(
                        f"{cohort.label} ran at {cohort.ratio:.2f}x baseline - "
                        f"below normal - during a window in which this "
                        f"hypothesis predicts more of them, not fewer"
                    ),
                    checked=f"cohort ratio {cohort.ratio:.2f} < 0.8",
                )
            )
    return signals


def competing_explanation(
    hypothesis: CandidateHypothesis, evidence: list[EvidenceItem]
) -> list[ContradictionSignal]:
    """Market events in-window that propose a different cause.

    Not an entailment judgement: a market event inside the window is, by
    construction, an alternative explanation competing for the same movement.
    Scenario 2 is built to produce exactly this - balanced evidence where no
    single hypothesis dominates - and the honest output is to surface the
    competitor, not to pick a winner here.
    """
    competitors = [
        e
        for e in evidence
        if e.source_type is SourceType.MARKET_EVENT
        and (hypothesis.changepoint is None
             or e.timestamp.date() <= hypothesis.changepoint)
    ]
    if not competitors:
        return []
    return [
        ContradictionSignal(
            hypothesis_id=hypothesis.hypothesis_id,
            hypothesis_statement=hypothesis.statement,
            contradiction_type=ContradictionType.COMPETING_EXPLANATION,
            direction=ContradictionDirection.CONTRADICTS,
            strength=STRENGTH[ContradictionType.COMPETING_EXPLANATION],
            contradicting_evidence_ids=[e.evidence_id for e in competitors],
            detail=(
                f"{len(competitors)} market event(s) in the window predate the "
                f"changepoint and offer a competing explanation: "
                + "; ".join(sorted({(e.title or e.excerpt)[:70] for e in competitors})[:3])
            ),
            checked="market_events in window with event_date <= changepoint",
        )
    ]


def supporting(
    hypothesis: CandidateHypothesis, evidence: list[EvidenceItem]
) -> ContradictionSignal | None:
    """Evidence temporally and contextually consistent with the hypothesis."""
    consistent = [
        e
        for e in evidence
        if (
            hypothesis.changepoint is None
            or e.timestamp.date() >= hypothesis.changepoint
        )
        and not _slice_conflicts(e, hypothesis.slice)
        and e.source_type is not SourceType.MARKET_EVENT
    ]
    if not consistent:
        return None
    return ContradictionSignal(
        hypothesis_id=hypothesis.hypothesis_id,
        hypothesis_statement=hypothesis.statement,
        contradiction_type=ContradictionType.CONSISTENT_WITH_HYPOTHESIS,
        direction=ContradictionDirection.SUPPORTS,
        strength=min(1.0, len(consistent) / 10.0),
        supporting_evidence_ids=[e.evidence_id for e in consistent],
        detail=(
            f"{len(consistent)} document(s) fall inside the affected slice at "
            f"or after the changepoint"
        ),
        checked="timestamp >= changepoint AND slice fields do not conflict",
    )


def analyse(
    hypothesis: CandidateHypothesis,
    evidence: list[EvidenceItem],
    cohorts: list[CohortEvidence] | None = None,
    *,
    peer_moved: bool = False,
    peer_label: str | None = None,
    did_estimate_pct: float | None = None,
) -> list[ContradictionSignal]:
    """Run every deterministic signal for one hypothesis."""
    cohorts = cohorts or []
    signals: list[ContradictionSignal] = []

    support = supporting(hypothesis, evidence)
    if support:
        signals.append(support)

    signals.extend(temporal_precedence(hypothesis, evidence))
    signals.extend(cohort_not_affected(hypothesis, cohorts))
    signals.extend(opposite_direction(hypothesis, cohorts))
    signals.extend(competing_explanation(hypothesis, evidence))
    signals.extend(
        unaffected_peer_moved(hypothesis, peer_moved, peer_label, did_estimate_pct)
    )

    # contradictions first, strongest first - the disconfirming evidence is
    # the part a reader is most likely to skip, so it is not buried
    signals.sort(
        key=lambda s: (s.direction is ContradictionDirection.SUPPORTS, -s.strength)
    )
    return signals
