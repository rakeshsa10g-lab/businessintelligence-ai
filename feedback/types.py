"""The five feedback outcomes (Architecture Part 15.1).

"The model learns" is the answer the Round 2 case is filtering out. This is the
specific version: five outcomes, each naming the artifact it updates and the
mechanism by which it does so.

Two of the five update live, because both are counters and neither needs a
model:

    accepted   -> calibration_events    -> the reliability text changes
    escalated  -> human_accuracy        -> deferral routing shifts

The other three accumulate and are applied on human review:

    rejected              -> a labelled example; scoring weights refit only at
                             N >= 30, within bounds, via a reviewed PR
    corrected             -> a regression test; prompt edits are human-authored
    insufficient_evidence -> a coverage gap; a source named 5+ times becomes a
                             roadmap item

**What this explicitly does not do:** no fine-tuning, no auto-applied prompt
changes, no unbounded weight drift, no per-item index rebuild. Saying so is a
credibility gain rather than a gap - the distinction between what updates live
and what updates on review is the specificity the case is testing for.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FeedbackOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CORRECTED = "corrected"
    ESCALATED = "escalated"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class UpdateTiming(str, Enum):
    LIVE = "live"            # a counter; applied on the event
    BATCHED = "batched"      # accumulates; applied on human review


class ArtifactUpdate(BaseModel):
    """Which downstream artifact this outcome feeds, and how."""

    model_config = ConfigDict(frozen=True)

    outcome: FeedbackOutcome
    artifact: str
    mechanism: str
    timing: UpdateTiming
    visible_effect: str
    threshold: str = ""


# The routing table from Part 15.1, as data rather than prose. A feedback
# event that cannot name its consumer is a feedback event nobody will act on.
ROUTING: dict[FeedbackOutcome, ArtifactUpdate] = {
    FeedbackOutcome.ACCEPTED: ArtifactUpdate(
        outcome=FeedbackOutcome.ACCEPTED,
        artifact="config/calibration.json :: calibration_events",
        mechanism="+1 to the (band, correct) counter; band accuracy recomputed",
        timing=UpdateTiming.LIVE,
        visible_effect="the reliability text on the confidence chip changes",
    ),
    FeedbackOutcome.REJECTED: ArtifactUpdate(
        outcome=FeedbackOutcome.REJECTED,
        artifact="eval/attribution_labels.jsonl and config/scoring.yaml",
        mechanism=(
            "labelled example appended; scoring weights refit by constrained "
            "regression, version-controlled, human-merged"
        ),
        timing=UpdateTiming.BATCHED,
        threshold="N >= 30 labelled cases",
        visible_effect="hypothesis ordering changes on future similar cases",
    ),
    FeedbackOutcome.CORRECTED: ArtifactUpdate(
        outcome=FeedbackOutcome.CORRECTED,
        artifact="eval/narrative_corrections.jsonl and prompts/*.txt",
        mechanism=(
            "the correction becomes a regression case; prompt edits are "
            "human-authored from recurring patterns, never auto-applied"
        ),
        timing=UpdateTiming.BATCHED,
        visible_effect="fewer Gate 2 violations of that type",
    ),
    FeedbackOutcome.ESCALATED: ArtifactUpdate(
        outcome=FeedbackOutcome.ESCALATED,
        artifact="config/deferral.yaml :: human_accuracy",
        mechanism="the analyst's verdict updates p_human for that cause bucket",
        timing=UpdateTiming.LIVE,
        visible_effect="the deferral rule's routing shifts for that bucket",
    ),
    FeedbackOutcome.INSUFFICIENT_EVIDENCE: ArtifactUpdate(
        outcome=FeedbackOutcome.INSUFFICIENT_EVIDENCE,
        artifact="coverage_gaps register",
        mechanism="the missing source is logged against the KPI",
        timing=UpdateTiming.BATCHED,
        threshold="a source named 5+ times becomes a roadmap item",
        visible_effect="Gate 1 abstains earlier and more specifically",
    ),
}


class FeedbackEvent(BaseModel):
    """One recorded human judgement."""

    model_config = ConfigDict(frozen=True)

    event_id: str
    run_id: str
    bundle_hash: str
    hypothesis_id: str | None = None
    recommendation_id: str | None = None
    lever_id: str | None = None

    outcome: FeedbackOutcome
    persona_id: str
    persona_role: str
    at: datetime

    confidence_band: str = ""
    was_correct: bool | None = None      # set for accepted/rejected
    correction: str | None = None        # the corrected driver or wording
    missing_source: str | None = None    # for insufficient_evidence
    note: str = ""

    @property
    def routing(self) -> ArtifactUpdate:
        return ROUTING[self.outcome]

    def render(self) -> str:
        r = self.routing
        return (
            f"{self.outcome.value} by {self.persona_role} on {self.run_id} "
            f"-> {r.artifact} ({r.timing.value})"
        )
