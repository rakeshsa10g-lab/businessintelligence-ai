"""Typed results for Stage 4 — attribution.

Three questions, kept apart on purpose because they have different evidential
standing:

  1. which *factor* of the revenue identity moved      -> IdentityDecomposition
  2. which *slice* moved unusually                     -> AdtributorResult
  3. may we say one *caused* the other                 -> CounterfactualResult

Only the third licenses causal wording, and it is a boolean that a downstream
gate reads rather than a matter of narrative tone (Architecture Part 10.3).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from semantic.types import LineageRecord

# --------------------------------------------------------------------------
# enums
# --------------------------------------------------------------------------


class AttributionOutcome(str, Enum):
    """What the engine was able to conclude."""

    ATTRIBUTED = "ATTRIBUTED"
    # No single dimension explains the movement. Adtributor genuinely cannot
    # solve this; HotSpot/Squeeze are the research answer and are deliberately
    # out of scope (Architecture Part 4.2). Route to human review rather than
    # report the best of a bad set.
    MULTI_DIMENSIONAL_CASE = "MULTI_DIMENSIONAL_CASE"
    NO_EXPLANATION = "NO_EXPLANATION"
    NOT_ATTEMPTED_SPARSE_HISTORY = "NOT_ATTEMPTED_SPARSE_HISTORY"
    NOT_ATTEMPTED_NOT_MATERIAL = "NOT_ATTEMPTED_NOT_MATERIAL"


class DriverStrength(str, Enum):
    STRONG = "STRONG"
    WEAK = "WEAK"
    UNSTABLE = "UNSTABLE"


Sign = Literal["increase", "decrease", "flat"]


# --------------------------------------------------------------------------
# Stage A — identity decomposition (LMDI)
# --------------------------------------------------------------------------


class DriverContribution(BaseModel):
    """One factor's share of the KPI movement."""

    driver: str
    baseline: float
    observed: float
    factor_change_pct: float
    contribution: float          # in KPI units, additive across drivers
    contribution_pct: float      # share of the total change, sums to ~100
    sign: Sign

    # A factor read at a coarser grain than the slice asked for. The
    # architecture is explicit that this must be shown, not silently absorbed:
    # refund_rate has no channel dimension, so a region x channel slice can
    # only get refunds at region level.
    grain_limited: bool = False
    grain_note: str | None = None


class SourceReconciliation(BaseModel):
    """A measured difference between two sources for the same quantity.

    Explicitly represented, never used to make the identity balance.
    """

    quantity: str
    source_a: str
    source_b: str
    value_a: float
    value_b: float
    difference_pct: float
    classification: str          # population / timing / definition / grain / noise
    explanation: str
    material_to_identity: bool = False


class IdentityDecomposition(BaseModel):
    """LMDI decomposition of a multiplicative identity.

    Conservation is exact by construction, not by luck: the factor
    contributions sum to the change in the *reconstructed* identity value with
    no residual and no ordering dependence. `closure_gap_pct` separately
    reports how far that reconstructed value sits from the warehouse KPI,
    which is a data question rather than a mathematical one.
    """

    kpi: str
    identity: str
    baseline: float              # V0, reconstructed from the factors
    observed: float              # V1
    total_change: float
    drivers: list[DriverContribution] = Field(default_factory=list)
    method: str = "LMDI-I (logarithmic mean Divisia index, additive form)"

    conservation_error: float = 0.0
    conservation_tolerance: float = 0.0
    conserved: bool = True

    # the identity is evaluated on one analytical population, so this should
    # be ~0; a non-zero value means a source was mixed in and is a defect
    actual_kpi_baseline: float | None = None
    actual_kpi_observed: float | None = None
    closure_gap_pct: float | None = None
    closure_note: str | None = None

    # Cross-source differences are reported here rather than absorbed into a
    # plug term. These are data-quality facts about heterogeneous sources, not
    # drivers of the KPI, and conflating the two is how a reconciliation gap
    # gets narrated as a business event.
    reconciliation: list[SourceReconciliation] = Field(default_factory=list)

    lineage: list[LineageRecord] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def dominant_driver(self) -> str | None:
        if not self.drivers:
            return None
        return max(self.drivers, key=lambda d: abs(d.contribution)).driver

    def explain(self) -> str:
        parts = [
            f"{d.driver} {d.contribution:+,.0f} ({d.contribution_pct:+.1f}%)"
            for d in sorted(self.drivers, key=lambda x: -abs(x.contribution))
        ]
        return (
            f"{self.kpi} moved {self.total_change:+,.0f}: " + ", ".join(parts)
        )


# --------------------------------------------------------------------------
# Stage B — dimensional attribution (Adtributor)
# --------------------------------------------------------------------------


class AdtributorElement(BaseModel):
    """One element (value) of one dimension.

    Field names carry the paper's notation so the mapping is checkable:
      forecast           F_ij
      actual             A_ij
      explanatory_power  EP_ij = (A_ij - F_ij) / (A - F)     (Eq. 4)
      prior              p_ij  = F_ij / F                    (Eq. 5)
      posterior          q_ij  = A_ij / A                    (Eq. 6)
      surprise           S_ij  = JS divergence term          (Eq. 7)
    """

    dimension: str
    element: str
    forecast: float
    actual: float
    explanatory_power: float
    prior: float
    posterior: float
    surprise: float
    selected: bool = False


class DimensionExplanation(BaseModel):
    dimension: str
    candidates: list[AdtributorElement] = Field(default_factory=list)
    all_elements: list[AdtributorElement] = Field(default_factory=list)
    explanatory_power: float = 0.0       # summed EP of the candidate set
    surprise: float = 0.0                # summed surprise of the candidate set
    n_candidates: int = 0
    n_elements: int = 0
    passed_ep_threshold: bool = False
    succinct: bool = True
    reason: str = ""

    @property
    def element_names(self) -> list[str]:
        return [e.element for e in self.candidates]


class AdtributorResult(BaseModel):
    """Ranked dimensions, most surprising first."""

    total_forecast: float
    total_actual: float
    total_change: float
    dimensions: list[DimensionExplanation] = Field(default_factory=list)
    winner: DimensionExplanation | None = None
    outcome: AttributionOutcome = AttributionOutcome.ATTRIBUTED
    t_ep: float = 0.67
    t_eep: float = 0.10
    method: str = (
        "Adtributor (Bhagwan et al., NSDI '14): explanatory power + "
        "succinctness + JS-divergence surprise, dimensions ranked by surprise"
    )
    reason: str = ""


# --------------------------------------------------------------------------
# Stage C1 — robustness
# --------------------------------------------------------------------------


class RobustnessResult(BaseModel):
    """Is the winning slice an artefact of exactly which days were in scope?

    Deliberately NOT a Welch p-value on the event window. Stage 3 established
    that the window is selected to maximise displacement, so such a p-value is
    a post-selection statistic and is small even on pure noise (ADR-017).
    """

    method: str = "moving-block bootstrap over event-window days"
    n_resamples: int = 0
    block_length: int = 0
    window_days: int = 0
    seed: int = 0

    top_element: str | None = None
    top_dimension: str | None = None
    selection_frequency: float = 0.0     # how often the same element wins
    dimension_frequency: float = 0.0

    ep_mean: float = 0.0
    ep_p05: float = 0.0
    ep_p95: float = 0.0
    ep_sign_consistency: float = 0.0

    strength: DriverStrength = DriverStrength.UNSTABLE
    reason: str = ""
    caveat: str | None = None


# --------------------------------------------------------------------------
# Stage C2/C3 — temporal precedence and difference-in-differences
# --------------------------------------------------------------------------


class CounterfactualResult(BaseModel):
    """Difference-in-differences against a matched control slice.

    This does not prove causality in general, and the code does not claim it
    does. It answers one narrower question: is the movement specific to this
    slice, or did comparable slices move with it? Only the former licenses
    causal wording (Architecture Part 10.3).
    """

    method: str = "difference-in-differences vs highest pre-period correlated control"

    treatment: str
    treatment_slice: dict[str, list[str]] = Field(default_factory=dict)
    control: str | None = None
    control_slice: dict[str, list[str]] | None = None
    control_correlation: float | None = None
    controls_considered: list[str] = Field(default_factory=list)

    pre_period: tuple[date, date] | None = None
    post_period: tuple[date, date] | None = None

    treatment_pre: float | None = None
    treatment_post: float | None = None
    control_pre: float | None = None
    control_post: float | None = None

    estimate: float | None = None            # the DiD estimate, KPI units
    estimate_pct: float | None = None        # relative to treatment_pre

    parallel_trend_passed: bool = False
    parallel_trend_stat: float | None = None
    parallel_trend_reason: str = ""

    temporal_precedence: bool = False
    temporal_precedence_reason: str = ""

    passed: bool = False
    reason: str = ""

    @property
    def causal_language_licensed(self) -> bool:
        """The single boolean the narrative gate reads."""
        return bool(self.passed and self.temporal_precedence)


# --------------------------------------------------------------------------
# the assembled result
# --------------------------------------------------------------------------


class KPIMovement(BaseModel):
    """The established movement, carried forward from Stage 3."""

    kpi_id: str
    slice_label: str
    baseline_value: float | None = None
    observed_value: float | None = None
    abs_delta: float | None = None
    pct_delta: float | None = None
    changepoint_date: date | None = None
    event_start: date | None = None
    event_end: date | None = None
    is_material: bool = False
    detection_outcome: str = ""


class RankedSlice(BaseModel):
    """A candidate slice, ranked. Demoted slices are kept, not dropped."""

    dimension: str
    element: str
    slice: dict[str, list[str]] = Field(default_factory=dict)
    explanatory_power: float
    surprise: float
    forecast: float
    actual: float
    delta: float
    rank: int
    selected: bool


class AttributionResult(BaseModel):
    """The complete Stage 4 output — input to the later hypothesis layer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kpi_id: str
    contract_version: str
    slice: dict[str, list[str]] = Field(default_factory=dict)
    slice_label: str = "ALL"
    scenario_id: str | None = None

    movement: KPIMovement

    identity: IdentityDecomposition | None = None
    adtributor: AdtributorResult | None = None

    ranked_dimensions: list[DimensionExplanation] = Field(default_factory=list)
    ranked_slices: list[RankedSlice] = Field(default_factory=list)

    explanatory_power: float | None = None
    surprise: float | None = None

    robustness: RobustnessResult | None = None
    counterfactual: CounterfactualResult | None = None

    causal_language_licensed: bool = False
    causal_language_reason: str = ""

    outcome: AttributionOutcome = AttributionOutcome.NO_EXPLANATION
    requires_human_review: bool = False

    # ratio KPIs are never attributed directly; this records the redirection
    attributed_via: list[str] | None = None
    attribution_kpi: str | None = None

    grain_limit_note: str | None = None
    lineage: list[LineageRecord] = Field(default_factory=list)
    method: str = ""
    notes: list[str] = Field(default_factory=list)
    computed_at: datetime | None = None

    @property
    def top_slice(self) -> RankedSlice | None:
        selected = [s for s in self.ranked_slices if s.selected]
        return selected[0] if selected else None

    def descriptive_statement(self) -> str:
        """Always permitted: describes what moved, asserts no cause."""
        top = self.top_slice
        if top is None:
            return (
                f"{self.kpi_id} [{self.slice_label}]: no single dimension "
                f"explains the movement."
            )
        direction = "declined" if top.delta < 0 else "rose"
        return (
            f"{self.kpi_id} {direction} in the "
            f"{top.dimension}={top.element} slice "
            f"({top.explanatory_power:.0%} of the movement)."
        )

    def causal_statement(self, cause: str) -> str | None:
        """Permitted only when the counterfactual and precedence checks pass.

        Returns None when the licence was not granted. The caller cannot
        accidentally get causal wording by phrasing the request differently,
        because there is no other method that produces it.
        """
        if not self.causal_language_licensed:
            return None
        top = self.top_slice
        where = f"{top.dimension}={top.element}" if top else self.slice_label
        return f"{cause} caused the {self.kpi_id} movement in {where}."

    def explain(self) -> str:
        lines = [
            f"{self.kpi_id} [{self.slice_label}] -> {self.outcome.value}",
        ]
        if self.attributed_via:
            lines.append(
                f"  ratio KPI: attributed via {', '.join(self.attributed_via)}"
            )
        if self.identity:
            lines.append("  " + self.identity.explain())
        if self.adtributor and self.adtributor.winner:
            w = self.adtributor.winner
            lines.append(
                f"  dimension: {w.dimension} = {w.element_names} "
                f"(EP {w.explanatory_power:.2f}, surprise {w.surprise:.4f})"
            )
        if self.robustness:
            lines.append(
                f"  robustness: {self.robustness.strength.value} "
                f"({self.robustness.selection_frequency:.0%} of resamples)"
            )
        if self.counterfactual:
            lines.append(f"  counterfactual: {self.counterfactual.reason}")
        lines.append(
            f"  causal language: "
            f"{'LICENSED' if self.causal_language_licensed else 'DENIED'} "
            f"- {self.causal_language_reason}"
        )
        return "\n".join(lines)
