"""Typed results for the detection pipeline.

Every stage returns its own result object rather than a bare number, because
the Round 2 case requires the *method* to be inspectable (R2-MPE-8, R2-MPE-9)
and because "why did you alert me?" must have a literal answer (Part 8.3).

Architecture reference: Part 9.2.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from semantic.types import FreshnessStatus, LineageRecord


# --------------------------------------------------------------------------
# 0. coverage
# --------------------------------------------------------------------------
class CoverageStatus(str, Enum):
    OK = "OK"
    SPARSE_HISTORY = "SPARSE_HISTORY"
    EXCESSIVE_MISSINGNESS = "EXCESSIVE_MISSINGNESS"
    INSUFFICIENT_OBSERVATIONS = "INSUFFICIENT_OBSERVATIONS"
    UNSUITABLE_SEASONAL_PERIOD = "UNSUITABLE_SEASONAL_PERIOD"


class CoverageResult(BaseModel):
    """Runs before any statistical method. Nothing downstream is valid without
    it, and it is what makes the sparse-history scenario a designed path
    rather than a crash (Part 9.3)."""

    status: CoverageStatus
    observations_available: int
    observations_required: int
    span_days: int
    missing_days: int
    missing_rate: float
    imputed_days: int = 0
    seasonal_period: int = 0
    periods_covered: float = 0.0
    reason: str = ""
    recommended_action: str = ""

    @property
    def passed(self) -> bool:
        return self.status is CoverageStatus.OK


# --------------------------------------------------------------------------
# 2. decomposition
# --------------------------------------------------------------------------
class DecompositionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    method: str = "STL"
    seasonal_period: int
    robust: bool
    dates: list[date]
    observed: list[float]
    trend: list[float]
    seasonal: list[float]
    residual: list[float]
    seasonal_strength: float = 0.0
    trend_smoother: int | None = None
    trend_strength: float = 0.0


# --------------------------------------------------------------------------
# 3. robust point-anomaly score
# --------------------------------------------------------------------------
class RobustScoreResult(BaseModel):
    """MAD-based, not mean/std: a single extreme day inflates sigma and hides
    the next real event (Part 9.3)."""

    method: str = "median_absolute_deviation"
    scale_constant: float = 1.4826
    residual_median: float
    mad: float
    robust_scale: float
    z_threshold: float
    z_scores: list[float]
    anomaly_flags: list[bool]
    n_anomalies: int
    max_abs_z: float
    degenerate_scale: bool = False


# --------------------------------------------------------------------------
# 4. regime shift
# --------------------------------------------------------------------------
class ShiftType(str, Enum):
    SPIKE = "SPIKE"                 # point anomaly only
    LEVEL_SHIFT = "LEVEL_SHIFT"     # changepoint plus a sustained move
    DRIFT = "DRIFT"                 # neither, but a trend slope
    NONE = "NONE"


class ChangepointResult(BaseModel):
    method: str = "PELT"
    cost_model: str = "l2"
    penalty: float
    min_size: int
    jump: int
    changepoint_indices: list[int] = Field(default_factory=list)
    changepoint_dates: list[date] = Field(default_factory=list)
    selected_index: int | None = None
    selected_date: date | None = None
    segment_end_index: int | None = None
    segments_merged: int = 0
    segment_end_date: date | None = None
    effective_penalty: float | None = None
    residual_sigma: float | None = None
    n_changepoints: int = 0
    shift_type: ShiftType = ShiftType.NONE
    selection_rule: str = ""


# --------------------------------------------------------------------------
# 5-6. quantification and the business gate
# --------------------------------------------------------------------------
class MaterialityResult(BaseModel):
    """Statistical significance and business materiality are reported
    separately and never collapsed into one unexplained score."""

    abs_effect: float
    rel_effect_pct: float
    duration_days: int
    min_abs_effect: float
    min_rel_effect_pct: float
    min_duration_days: int
    unit: str
    abs_effect_passed: bool
    rel_effect_passed: bool
    duration_passed: bool
    business_materiality: bool
    rule: str
    reason: str


class StatisticalSignal(BaseModel):
    significant: bool
    max_abs_z: float
    z_threshold: float
    z_passed: bool
    changepoint_found: bool
    p_value: float | None = None
    p_threshold: float = 0.05
    p_passed: bool | None = None
    effect_size_cohens_d: float | None = None
    test: str = "welch_t"
    reason: str = ""


# --------------------------------------------------------------------------
# the detection outcome
# --------------------------------------------------------------------------
class DetectionOutcome(str, Enum):
    MATERIAL_EVENT = "MATERIAL_EVENT"
    NO_MATERIAL_FINDING = "NO_MATERIAL_FINDING"
    SPARSE_HISTORY = "SPARSE_HISTORY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DetectionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # identity
    kpi_id: str
    contract_version: str
    slice: dict[str, list[str]] = Field(default_factory=dict)
    slice_label: str = "ALL"
    scenario_id: str | None = None

    # windows
    analysis_start: date
    analysis_end: date
    baseline_start: date | None = None
    baseline_end: date | None = None
    observed_start: date | None = None
    observed_end: date | None = None

    # magnitudes
    baseline_value: float | None = None
    observed_value: float | None = None
    abs_delta: float | None = None
    pct_delta: float | None = None

    # method outputs
    coverage: CoverageResult
    decomposition: DecompositionResult | None = None
    robust_score: RobustScoreResult | None = None
    changepoint: ChangepointResult | None = None
    statistical_signal: StatisticalSignal | None = None
    materiality: MaterialityResult | None = None

    # verdicts, kept separate on purpose
    outcome: DetectionOutcome
    is_material: bool = False

    # provenance
    method: str
    freshness: FreshnessStatus | None = None
    lineage: LineageRecord | None = None
    preprocessing_notes: list[str] = Field(default_factory=list)
    computed_at: datetime | None = None

    # sparse-history extras (Part 9.4)
    peer_cohort: dict | None = None
    confidence_ceiling: str | None = None
    caveat: str | None = None

    @property
    def changepoint_date(self) -> date | None:
        return self.changepoint.selected_date if self.changepoint else None

    def explain(self) -> str:
        """One-line answer to 'why did you alert me, or why did you not?'"""
        if self.outcome is DetectionOutcome.SPARSE_HISTORY:
            return (
                f"{self.kpi_id} [{self.slice_label}]: sparse history "
                f"({self.coverage.observations_available} of "
                f"{self.coverage.observations_required} days). {self.caveat or ''}"
            ).strip()
        if self.outcome is DetectionOutcome.INSUFFICIENT_DATA:
            return f"{self.kpi_id} [{self.slice_label}]: {self.coverage.reason}"
        if self.materiality is None or self.statistical_signal is None:
            return f"{self.kpi_id} [{self.slice_label}]: {self.outcome.value}"
        return (
            f"{self.kpi_id} [{self.slice_label}]: "
            f"statistical_signal={self.statistical_signal.significant}, "
            f"business_materiality={self.materiality.business_materiality} "
            f"-> {self.outcome.value}. {self.materiality.reason}"
        )
