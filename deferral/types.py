"""Typed deferral and abstention (Architecture Part 14.4).

Three outcomes, and the distinction between the last two matters:

  **automate** — the system acts, or presents the action as ready to take
  **review**   — a human decides, and gets a packet that makes that cheap
  **abstain**  — there is nothing for a human to review either

Six abstention reasons, each a different deterministic state rather than one
"insufficient evidence" bucket. A reader who is told *why* the system declined
can do something about it; a reader told only that it declined cannot.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from confidence.types import Confidence


class DeferralOutcome(str, Enum):
    AUTOMATE = "automate"
    REVIEW = "review"
    ABSTAIN = "abstain"


class AutomationScope(str, Enum):
    """What "automate" actually means for this persona and this lever.

    Raising a request automatically is not the same as performing an action
    automatically, and a system that cannot say which it means will either
    over-claim or defer everything.
    """

    NONE = "none"
    RAISE_REQUEST = "raise_request"     # the persona may request; we do that
    EXECUTE = "execute"                 # the persona may approve; we act


class AbstentionReason(str, Enum):
    """Why the system declined. Six states, not one.

    Each has a different remedy, which is the reason they are separate:
    NO_MATERIAL_EVENT needs nothing, SPARSE_HISTORY needs time,
    EVIDENCE_INSUFFICIENCY needs a source, CONFLICTING_EVIDENCE needs a human
    to disambiguate, UNAUTHORIZED_INFORMATION needs a different reader, and
    UNSUPPORTED_CAUSAL_CLAIM needs the wording changed rather than the
    analysis redone.
    """

    NONE = "none"
    NO_MATERIAL_EVENT = "no_material_event"
    SPARSE_HISTORY = "sparse_history"
    EVIDENCE_INSUFFICIENCY = "evidence_insufficiency"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    UNAUTHORIZED_INFORMATION = "unauthorized_information"
    UNSUPPORTED_CAUSAL_CLAIM = "unsupported_causal_claim"
    MULTI_DIMENSIONAL = "multi_dimensional"


ABSTENTION_REMEDY: dict[AbstentionReason, str] = {
    AbstentionReason.NO_MATERIAL_EVENT: (
        "nothing to do: no movement cleared the materiality gate"
    ),
    AbstentionReason.SPARSE_HISTORY: (
        "wait for history; this slice needs more observations before a "
        "seasonal baseline exists"
    ),
    AbstentionReason.EVIDENCE_INSUFFICIENCY: (
        "a movement is real but nothing corroborates an explanation; name the "
        "missing source and the gap closes"
    ),
    AbstentionReason.CONFLICTING_EVIDENCE: (
        "two explanations are equally supported; a human decides which, and "
        "they imply different owners"
    ),
    AbstentionReason.UNAUTHORIZED_INFORMATION: (
        "the evidence needed is not readable by this role; a permitted reader "
        "can answer it"
    ),
    AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM: (
        "the association holds but causation was not established; the finding "
        "stands, the wording must stay associative"
    ),
    AbstentionReason.MULTI_DIMENSIONAL: (
        "the cause spans a combination of dimensions, which this system does "
        "not localise"
    ),
}


class LossEstimate(BaseModel):
    """One arm of the expected-loss comparison."""

    model_config = ConfigDict(frozen=True)

    label: str
    accuracy: float
    cost_of_error: float
    error_loss: float
    additional_cost: float = 0.0
    total: float = 0.0
    basis: str = ""

    def render(self) -> str:
        extra = (
            f" + {self.additional_cost:,.0f} review/delay"
            if self.additional_cost else ""
        )
        return (
            f"{self.label}: (1 - {self.accuracy:.2f}) x "
            f"{self.cost_of_error:,.0f} = {self.error_loss:,.0f}{extra} "
            f"= {self.total:,.0f} INR"
        )


class DeferralDecision(BaseModel):
    """Who should decide this, and what the arithmetic said."""

    model_config = ConfigDict(frozen=True)

    outcome: DeferralOutcome
    automated: bool = False
    review: bool = False
    abstain: bool = False

    abstention_reason: AbstentionReason = AbstentionReason.NONE
    remedy: str = ""

    expected_model_loss: float = 0.0
    expected_human_loss: float = 0.0
    review_cost: float = 0.0
    model_arm: LossEstimate | None = None
    human_arm: LossEstimate | None = None

    p_model: float = 0.0
    p_human: float = 0.0
    cost_of_error: float = 0.0
    cause_bucket: str = ""

    automation_scope: AutomationScope = AutomationScope.NONE
    override_applied: str | None = None
    capacity_ok: bool = True
    queue_depth: int = 0

    rationale: str = ""
    policy_version: str = ""

    def render(self) -> str:
        if self.abstain:
            return (
                f"ABSTAIN ({self.abstention_reason.value}): {self.rationale}"
            )
        if self.automated:
            head = (
                "AUTOMATE (raise the request)"
                if self.automation_scope is AutomationScope.RAISE_REQUEST
                else "AUTOMATE (execute)"
            )
        else:
            head = "REVIEW"
        return f"{head}: {self.rationale}"


class AnalystPacket(BaseModel):
    """What a human receives when a decision is deferred.

    Not "contact an analyst". The packet is the investigation already done: the
    movement, the ranked hypotheses with their evidence for and against, the
    methods, the lineage, what is missing, and the specific question that would
    resolve it. The purpose is to reduce the manual work, not to hand it over.
    """

    model_config = ConfigDict(frozen=True)

    packet_id: str
    bundle_id: str
    bundle_hash: str
    created_at: datetime

    persona_id: str
    persona_role: str

    kpi_id: str
    kpi_name: str
    window_start: date
    window_end: date
    movement_summary: str = ""
    movement_facts: tuple[tuple[str, str], ...] = ()

    hypotheses: tuple[tuple[str, str, str], ...] = ()   # (id, statement, status)
    supporting_evidence: tuple[tuple[str, str], ...] = ()
    contradicting_evidence: tuple[tuple[str, str], ...] = ()
    cohorts: tuple[str, ...] = ()

    methods_used: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()

    missing_information: tuple[str, ...] = ()
    recommended_clarification: str = ""
    suggested_actions: tuple[tuple[str, str], ...] = ()   # (lever_id, name)

    confidence_render: str = ""
    confidence_band: str = ""
    deferral_rationale: str = ""
    estimated_review_minutes: int = 0

    def render(self) -> str:
        lines = [
            f"ANALYST PACKET {self.packet_id}",
            f"  bundle {self.bundle_hash[:16]}  for {self.persona_role}",
            f"  {self.kpi_name}, {self.window_start}..{self.window_end}",
            f"  movement: {self.movement_summary}",
            f"  confidence: {self.confidence_render}",
            f"  why you: {self.deferral_rationale}",
            "",
            "  THE QUESTION",
            f"    {self.recommended_clarification}",
            "",
            f"  HYPOTHESES ({len(self.hypotheses)})",
        ]
        for hid, statement, status in self.hypotheses:
            lines.append(f"    [{status}] {statement}  ({hid})")
        lines.append(f"\n  SUPPORTING EVIDENCE ({len(self.supporting_evidence)})")
        for eid, excerpt in self.supporting_evidence[:5]:
            lines.append(f"    {eid}: {excerpt[:70]}")
        if self.contradicting_evidence:
            lines.append(
                f"\n  CONTRADICTING EVIDENCE ({len(self.contradicting_evidence)})"
            )
            for eid, excerpt in self.contradicting_evidence[:5]:
                lines.append(f"    {eid}: {excerpt[:70]}")
        if self.missing_information:
            lines.append("\n  WHAT IS MISSING")
            for item in self.missing_information:
                lines.append(f"    - {item}")
        if self.suggested_actions:
            lines.append("\n  ACTIONS AVAILABLE IF YOU CONFIRM")
            for lever_id, name in self.suggested_actions:
                lines.append(f"    {lever_id}: {name}")
        lines.append(
            f"\n  estimated review time: {self.estimated_review_minutes} minutes"
        )
        return "\n".join(lines)
