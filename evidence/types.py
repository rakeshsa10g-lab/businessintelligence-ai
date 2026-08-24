"""Stage 6 types — hypotheses and the frozen EvidenceBundle.

This stage is the boundary between deterministic analysis and the future LLM.
Everything the model will ever be allowed to see is assembled here, hashed,
and frozen. **If a fact is not in the bundle, it does not exist as far as the
narrative is concerned** (Architecture Part 5.3).

That single sentence is what makes the later verification gate mechanically
checkable rather than aspirational: a claim can be checked against a closed set
instead of against "the database", and a number the model invents has nowhere
to have come from.

No LLM appears in this stage. No prompts, no SDK, no model of any kind.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from attribution.types import AttributionResult, CounterfactualResult
from detection.types import DetectionResult
from retrieval.types import CohortEvidence, SourceType
from semantic.types import PlainDateTime


# --------------------------------------------------------------------------
# enums
# --------------------------------------------------------------------------
class HypothesisStatus(str, Enum):
    """What the evidence actually supports.

    `SUPPORTED` is deliberately hard to reach. A system that returns a
    confident winner for every movement is not measuring anything - the
    interesting cases are the ones where it declines.
    """

    SUPPORTED = "SUPPORTED"
    PLAUSIBLE = "PLAUSIBLE"
    # Two or more hypotheses within the ambiguity margin. Both are reported;
    # neither is promoted. This is the correct answer to Scenario 2, not a
    # failure to decide.
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"
    MULTI_DIMENSIONAL = "MULTI_DIMENSIONAL"
    REJECTED = "REJECTED"


class EvidenceStance(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    NEUTRAL = "neutral"


class EvidenceWeight(str, Enum):
    """How much one piece of evidence is allowed to count.

    The tiers are a business judgement, not a statistical one, and they are
    stated rather than buried: a deploy record timed to the changepoint is
    stronger evidence than a CRM note that mentions the same topic, because
    one is a fact about the system and the other is a person's summary of a
    conversation.
    """

    STRONG = "strong"          # structured records, cohort rate changes
    MODERATE = "moderate"      # CRM notes, market events
    WEAK = "weak"              # single unstructured document, no corroboration


class DataQualityState(str, Enum):
    OK = "ok"
    IMPUTED = "imputed"
    SPARSE = "sparse"
    STALE = "stale"
    SCHEMA_CHANGE_APPLIED = "schema_change_applied"


# --------------------------------------------------------------------------
# metric facts — the numeric allowlist
# --------------------------------------------------------------------------
class MetricFact(BaseModel):
    """One number the narrative is allowed to state.

    Raw tables never reach the model. Every figure it may use is enumerated
    here with its provenance, which is what turns "the LLM must not invent
    numbers" from a prompt instruction into a set membership test.
    """

    model_config = ConfigDict(frozen=True)

    fact_id: str
    metric: str
    label: str
    value: float
    unit: str

    baseline: float | None = None
    observed: float | None = None
    delta: float | None = None
    delta_pct: float | None = None

    period_start: date | None = None
    period_end: date | None = None

    dimension: str | None = None
    slice: tuple[tuple[str, str], ...] = ()     # tuples so the model can hash

    source_id: str = ""
    source_table: str = ""
    contract_version: str = ""
    as_of: PlainDateTime | None = None
    computed_by: str = ""                        # which stage produced it

    def render(self) -> str:
        """A deterministic rendering. No model wrote this string."""
        if self.unit == "INR":
            body = f"{self.value:,.0f} INR"
        elif self.unit in ("pct", "%"):
            body = f"{self.value:+.2f}%"
        elif self.unit == "ratio":
            body = f"{self.value:.4f}"
        else:
            body = f"{self.value:,.2f} {self.unit}".strip()
        return f"{self.label}: {body}"


# --------------------------------------------------------------------------
# evidence references
# --------------------------------------------------------------------------
class EvidenceRef(BaseModel):
    """A pointer to one document, with just enough context to narrate it.

    The raw document store stays outside the bundle. What travels is the id,
    a short excerpt, the metadata needed to date and place it, and the
    retrieval scores that put it here - so a reader can ask "why is this in
    front of me?" and get an answer.
    """

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    source_type: SourceType
    source_id: str
    source_table: str
    # Mirrors EvidenceItem.timestamp, which is pandas-sourced. See
    # semantic.types.PlainDateTime for why a bare `datetime` is not enough.
    timestamp: PlainDateTime

    title: str | None = None
    excerpt: str = ""

    region: str | None = None
    segment: str | None = None
    channel: str | None = None
    category: str | None = None

    stance: EvidenceStance = EvidenceStance.NEUTRAL
    weight: EvidenceWeight = EvidenceWeight.MODERATE

    cohort_id: str | None = None
    duplicate_count: int = 0

    retrieval_method: str = ""
    relevance_score: float | None = None
    bm25_rank: int | None = None
    dense_rank: int | None = None

    freshness_lag_hours: float | None = None
    as_of: PlainDateTime | None = None


class CohortRef(BaseModel):
    """A cohort roll-up carried into the bundle as one piece of evidence."""

    model_config = ConfigDict(frozen=True)

    cohort_id: str
    statement: str
    label: str
    source_type: SourceType
    incident_count: int
    baseline_count: float
    baseline_weeks: int = 0
    ratio: float | None = None
    novel: bool = False
    distinct_accounts: int = 0
    document_ids: tuple[str, ...] = ()
    # the window the statement quotes; carried so a verifier can validate the
    # dates that appear inside `statement`
    window_start: date | None = None
    window_end: date | None = None
    stance: EvidenceStance = EvidenceStance.SUPPORTING
    weight: EvidenceWeight = EvidenceWeight.STRONG


# --------------------------------------------------------------------------
# hypotheses
# --------------------------------------------------------------------------
class EvidenceProfile(BaseModel):
    """The counts a score is built from, exposed so the score is checkable.

    `distinct_documents` is the number of UNIQUE documents, after near-
    duplicate collapsing. `total_documents` includes the duplicates. Keeping
    both visible is what stops thirty copies of one ticket reading as thirty
    findings - and lets a reader see that it was thirty copies.
    """

    model_config = ConfigDict(frozen=True)

    distinct_documents: int = 0
    total_documents: int = 0
    duplicate_documents: int = 0
    source_types: tuple[str, ...] = ()
    cohort_count: int = 0
    contradiction_count: int = 0
    contradiction_strength: float = 0.0
    temporal_tightness: float = 0.0
    days_from_changepoint_median: float | None = None

    @property
    def duplicate_ratio(self) -> float:
        if not self.total_documents:
            return 0.0
        return self.duplicate_documents / self.total_documents


class ScoreBreakdown(BaseModel):
    """Every term of the score, so the ranking can be recomputed by hand."""

    model_config = ConfigDict(frozen=True)

    components: tuple[tuple[str, float], ...] = ()      # (name, normalised)
    weighted: tuple[tuple[str, float], ...] = ()        # (name, contribution)
    weighted_sum: float = 0.0
    contradiction_multiplier: float = 1.0
    final: float = 0.0
    scoring_version: str = ""

    # The two halves of the product, kept separately because they answer
    # different questions: "is this movement real?" is identical across every
    # hypothesis, while "does this explanation fit?" is what ranks them.
    movement_confidence: float = 0.0
    evidence_fit: float = 0.0

    def explain(self) -> str:
        parts = [f"{n}={v:.3f}" for n, v in self.weighted]
        return (
            f"{' + '.join(parts)} = {self.weighted_sum:.3f} "
            f"x {self.contradiction_multiplier:.3f} = {self.final:.3f}"
        )


class Hypothesis(BaseModel):
    """One candidate explanation, with the evidence for and against it."""

    model_config = ConfigDict(frozen=True)

    hypothesis_id: str
    statement: str                       # deterministic template, not generated

    driver_id: str
    driver_name: str
    cause_bucket: str

    dimension: str | None = None
    slice: tuple[tuple[str, str], ...] = ()

    # quantitative inputs, all carried forward from Stages 3-4
    contribution: float | None = None            # in KPI units
    contribution_share: float | None = None      # 0-1
    surprise: float | None = None
    robustness: str | None = None                # STRONG / WEAK / UNSTABLE
    robustness_score: float = 0.0
    effect_size: float | None = None
    statistical_significance: float | None = None   # diagnostic only, see below

    counterfactual: CounterfactualResult | None = None
    temporal_precedence: bool = False
    causal_language_allowed: bool = False
    causal_language_reason: str = ""

    # evidence, kept as two separate lists on purpose
    supporting_evidence_ids: tuple[str, ...] = ()
    contradicting_evidence_ids: tuple[str, ...] = ()
    cohort_ids: tuple[str, ...] = ()
    evidence_profile: EvidenceProfile = Field(default_factory=EvidenceProfile)
    evidence_quality: EvidenceWeight = EvidenceWeight.WEAK

    score: float = 0.0
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    rank: int = 0
    status: HypothesisStatus = HypothesisStatus.INSUFFICIENT
    status_reason: str = ""

    eligible_lever_ids: tuple[str, ...] = ()

    @property
    def evidence_count(self) -> int:
        """Distinct, not total. Duplicates cannot inflate this."""
        return self.evidence_profile.distinct_documents

    @property
    def contradiction_count(self) -> int:
        return len(self.contradicting_evidence_ids)

    def summary(self) -> str:
        return (
            f"#{self.rank} {self.statement} "
            f"[{self.status.value}, score {self.score:.3f}, "
            f"{self.evidence_count} distinct supporting, "
            f"{self.contradiction_count} contradicting, "
            f"causal {'LICENSED' if self.causal_language_allowed else 'DENIED'}]"
        )


# --------------------------------------------------------------------------
# persona and security
# --------------------------------------------------------------------------
class PersonaProfile(BaseModel):
    """Who the bundle is for. Same facts, different future narrative."""

    model_config = ConfigDict(frozen=True)

    persona_id: str
    display_name: str
    title: str
    role: str
    user_region: str | None = None
    wants: str = ""
    narrative_style: str = ""
    # what a narrator for this persona should lead with; deterministic, and
    # it selects emphasis rather than content - the facts are identical
    emphasis: tuple[str, ...] = ()


class SecurityContext(BaseModel):
    """The entitlement context that produced this bundle.

    Carried so that a downstream consumer cannot widen access by forgetting
    which principal the analysis ran as. Restricted source ids are listed by
    NAME only - never with their contents - so the bundle can say "2 items
    withheld" without leaking what was withheld.
    """

    model_config = ConfigDict(frozen=True)

    persona_id: str
    role: str
    policy_version: str
    permitted_sources: tuple[str, ...] = ()
    denied_sources: tuple[str, ...] = ()
    permitted_regions: tuple[str, ...] = ()      # empty tuple = all regions
    withheld_source_ids: tuple[str, ...] = ()
    withheld_item_count: int = 0
    columns_masked: tuple[str, ...] = ()


class LeverRef(BaseModel):
    """An eligible lever. The model may phrase it; it may not invent one."""

    model_config = ConfigDict(frozen=True)

    lever_id: str
    name: str
    owner_role: str
    applies_to_hypothesis_id: str | None = None
    can_approve: tuple[str, ...] = ()
    can_request: tuple[str, ...] = ()
    persona_may_approve: bool = False
    persona_may_request: bool = False
    monitoring_metric: str = ""
    check_after_days: int = 0
    success_threshold: str = ""
    constraints: tuple[str, ...] = ()
    eligibility_reason: str = ""


class FreshnessRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    as_of: PlainDateTime | None = None
    lag_hours: float | None = None
    status: str = ""
    cadence: str = ""


class LineageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_id: str
    source_id: str
    source_table: str
    contract_version: str
    as_of: PlainDateTime | None = None
    row_count: int = 0
    filters_applied: tuple[str, ...] = ()
    compiled_sql_hash: str = ""


# --------------------------------------------------------------------------
# the bundle
# --------------------------------------------------------------------------
class EvidenceBundle(BaseModel):
    """Immutable. Hashed. Everything the LLM will ever see.

    Frozen at every level: the model config forbids mutation, and every
    collection is a tuple rather than a list, so `bundle.hypotheses.append(...)`
    raises instead of quietly changing an object whose hash is already in the
    audit trail.

    The hash covers a canonical serialisation, so two bundles built from the
    same inputs and the same configuration hash identically, and any change to
    evidence, a metric fact, a hypothesis, the persona, the lever list or the
    security context changes it.
    """

    model_config = ConfigDict(frozen=True)

    bundle_id: str
    bundle_version: str
    created_at: datetime
    bundle_hash: str = ""            # filled by freeze_evidence_bundle

    # who and what
    persona: PersonaProfile
    kpi_id: str
    kpi_name: str
    window_start: date
    window_end: date

    # the numbers, enumerated
    metric_facts: tuple[MetricFact, ...] = ()

    # the analysis that produced them, carried whole for auditability
    detection: DetectionResult | None = None
    attribution: AttributionResult | None = None

    # the ranked explanations
    hypotheses: tuple[Hypothesis, ...] = ()
    overall_status: HypothesisStatus = HypothesisStatus.INSUFFICIENT
    status_reason: str = ""

    # evidence, split and kept split
    supporting_evidence: tuple[EvidenceRef, ...] = ()
    contradicting_evidence: tuple[EvidenceRef, ...] = ()
    cohorts: tuple[CohortRef, ...] = ()

    allowed_levers: tuple[LeverRef, ...] = ()

    lineage: tuple[LineageRef, ...] = ()
    freshness: tuple[FreshnessRef, ...] = ()
    security_context: SecurityContext

    methods_used: tuple[str, ...] = ()
    data_quality_state: tuple[DataQualityState, ...] = ()
    data_quality_notes: tuple[str, ...] = ()

    causal_language_allowed: bool = False
    causal_permissions: tuple[tuple[str, bool], ...] = ()   # per hypothesis

    scoring_version: str = ""
    config_versions: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()

    # ----------------------------------------------------------------------
    @property
    def top_hypothesis(self) -> Hypothesis | None:
        return self.hypotheses[0] if self.hypotheses else None

    def fact(self, fact_id: str) -> MetricFact | None:
        for f in self.metric_facts:
            if f.fact_id == fact_id:
                return f
        return None

    def evidence(self, evidence_id: str) -> EvidenceRef | None:
        for e in self.supporting_evidence + self.contradicting_evidence:
            if e.evidence_id == evidence_id:
                return e
        return None

    def allowed_numbers(self) -> set[float]:
        """The numeric allowlist a later verification gate checks against."""
        values: set[float] = set()
        for f in self.metric_facts:
            for v in (f.value, f.baseline, f.observed, f.delta, f.delta_pct):
                if v is not None:
                    values.add(round(float(v), 6))
        return values

    def lever(self, lever_id: str) -> LeverRef | None:
        for lever in self.allowed_levers:
            if lever.lever_id == lever_id:
                return lever
        return None
