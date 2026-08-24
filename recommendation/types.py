"""Typed recommendations (Architecture Part 14.1).

    driver -> controllable lever -> action -> expected impact -> owner
           -> confidence -> monitoring plan

Seven elements. **One** of them is LLM-generated: the action sentence, which
fills slots in a template the catalogue owns. Everything else — which levers
are eligible, what the impact is, who owns it, what to watch and for how long —
is looked up or computed.

The expected impact is the element most systems get wrong, because a number is
easy to generate and hard to check. Here it is read from the movement detection
already measured, rendered as a range with the method named, and the model
never sees a blank to fill.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from confidence.types import ConfidenceBand


class ImpactModel(str, Enum):
    """How an expected impact is computed. Never generated."""

    RECOVER_TO_BASELINE = "recover_to_baseline"
    ELASTICITY_ESTIMATE = "elasticity_estimate"
    NO_BUSINESS_IMPACT = "no_business_impact"
    NONE = "none"


class DecisionRight(str, Enum):
    APPROVE = "approve"
    REQUEST = "request"
    NOTIFY = "notify"
    NONE = "none"


class ExpectedImpact(BaseModel):
    """A computed range, with the method named.

    A range rather than a point estimate, because the recovery fraction is an
    assumption and a single number would hide that. The `basis` string says
    where the underlying figure came from, so a reader can go and check it.
    """

    model_config = ConfigDict(frozen=True)

    model: ImpactModel
    low: float
    high: float
    unit: str = "INR"
    basis: str = ""
    source_fact_id: str | None = None
    measured_movement: float | None = None
    recovery_fraction_low: float = 0.0
    recovery_fraction_high: float = 0.0
    computed: bool = True          # always True; the field exists to be asserted

    def render(self) -> str:
        if self.model is ImpactModel.NO_BUSINESS_IMPACT:
            return "no business impact - this is a reporting artefact"
        if self.model is ImpactModel.NONE:
            return "no impact claimed - no action is being taken"
        return (
            f"{self.low:,.0f} to {self.high:,.0f} {self.unit} "
            f"({self.model.value}, from {self.basis})"
        )


class MonitoringPlan(BaseModel):
    """What to watch, for how long, and what success looks like.

    The metric comes from the semantic catalogue, not from the model: a
    monitoring plan naming a KPI that does not exist is a plan nobody can
    execute, and it would be indistinguishable from a real one in prose.
    """

    model_config = ConfigDict(frozen=True)

    metric_id: str
    metric_name: str
    check_after_days: int
    success_threshold: str
    baseline_value: float | None = None
    baseline_fact_id: str | None = None
    from_semantic_catalogue: bool = True

    def render(self) -> str:
        return (
            f"watch {self.metric_name} for {self.check_after_days} day(s); "
            f"success = {self.success_threshold}"
        )


class Recommendation(BaseModel):
    """One bounded, business-actionable recommendation."""

    model_config = ConfigDict(frozen=True)

    recommendation_id: str
    lever_id: str
    lever_name: str
    driver_id: str | None = None
    hypothesis_id: str | None = None

    # The template the LLM may fill. `action_text` stays None until a narrator
    # renders it; the recommendation is complete and usable without one.
    action_template: str = ""
    action_text: str | None = None

    owner_role: str = ""
    persona_right: DecisionRight = DecisionRight.NONE
    approver_roles: tuple[str, ...] = ()

    expected_impact: ExpectedImpact
    monitoring: MonitoringPlan

    confidence_band: ConfidenceBand = ConfidenceBand.UNCALIBRATED
    constraints: tuple[str, ...] = ()
    urgency: str = "normal"
    rationale: str = ""

    catalogue_version: str = ""

    def render(self) -> str:
        return (
            f"[{self.lever_id}] {self.lever_name}\n"
            f"    owner: {self.owner_role} "
            f"({self.persona_right.value} rights for this persona)\n"
            f"    impact: {self.expected_impact.render()}\n"
            f"    monitor: {self.monitoring.render()}"
        )


class RecommendationSet(BaseModel):
    """Everything recommended for one bundle, plus what was refused and why."""

    model_config = ConfigDict(frozen=True)

    bundle_id: str
    bundle_hash: str
    persona_id: str
    recommendations: tuple[Recommendation, ...] = ()
    rejected_lever_ids: tuple[tuple[str, str], ...] = ()   # (lever_id, reason)
    catalogue_version: str = ""
    notes: tuple[str, ...] = ()

    @property
    def primary(self) -> Recommendation | None:
        return self.recommendations[0] if self.recommendations else None
