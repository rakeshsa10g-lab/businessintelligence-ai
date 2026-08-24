"""Typed models for Stage 5 — evidence retrieval (Architecture Part 11).

The evidence layer answers one question: given a movement that detection
established and attribution localised, what text and what records support or
contradict the leading explanation?

It is deliberately not a second analytical engine. Nothing here computes a KPI,
re-ranks a driver, or forms a hypothesis. Retrieval finds documents; the
numbers stay in SQL and the ranking stays in `attribution/`.

Every model is plain Pydantic and knows nothing about LangGraph, Streamlit or
any LLM.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from semantic.types import PlainDateTime


# --------------------------------------------------------------------------
# enums
# --------------------------------------------------------------------------
class SourceType(str, Enum):
    """What kind of record this is, and therefore how it may be retrieved.

    The split is architectural, not cosmetic (Part 11.1). The first three are
    paraphrase-heavy prose where a dense model earns its place. The last three
    are records with exact keys — a deploy has a service and a timestamp, a
    schema change has a table and a column. Embedding those would replace an
    exact join with an approximate one, which is strictly worse.
    """

    # embedded
    SUPPORT_TICKET = "support_ticket"
    CRM_NOTE = "crm_note"
    MARKET_EVENT = "market_event"

    # never embedded — retrieved by deterministic SQL
    DEPLOY_CHANGELOG = "deploy_changelog"
    SCHEMA_CHANGE = "schema_change"
    FINANCE_ADJUSTMENT = "finance_adjustment"


EMBEDDABLE_SOURCES: frozenset[SourceType] = frozenset(
    {SourceType.SUPPORT_TICKET, SourceType.CRM_NOTE, SourceType.MARKET_EVENT}
)

STRUCTURED_SOURCES: frozenset[SourceType] = frozenset(
    {
        SourceType.DEPLOY_CHANGELOG,
        SourceType.SCHEMA_CHANGE,
        SourceType.FINANCE_ADJUSTMENT,
    }
)


class RetrievalMode(str, Enum):
    HYBRID = "hybrid"                # BM25 + dense, fused by RRF
    STRUCTURED = "structured"        # deterministic SQL filter, no embeddings
    BM25_ONLY = "bm25_only"
    DENSE_ONLY = "dense_only"


class EntitlementStatus(str, Enum):
    PERMITTED = "permitted"
    # Withheld documents are counted and reported, never silently dropped:
    # "2 items withheld — source crm_notes not permitted for role ops_lead"
    # is a stronger trust signal than a shorter list (Part 7.6).
    WITHHELD_SOURCE = "withheld_source"
    WITHHELD_ROW_FILTER = "withheld_row_filter"


class ContradictionType(str, Enum):
    """Deterministic contradiction signals only.

    No LLM and no semantic entailment model. Each of these is a checkable
    property of dates, slices and counts — if we cannot check it mechanically
    we do not claim it (Part 10.4's `contradicting_evidence` requirement made
    concrete without pretending to natural-language inference).
    """

    # supporting, not contradicting — kept in the same enum because both
    # directions are reported on one axis, and a signal type that could only
    # ever contradict would quietly bias the panel
    CONSISTENT_WITH_HYPOTHESIS = "consistent_with_hypothesis"

    TEMPORAL_PRECEDENCE_VIOLATED = "temporal_precedence_violated"
    COHORT_NOT_AFFECTED = "cohort_not_affected"
    OPPOSITE_DIRECTION = "opposite_direction"
    UNAFFECTED_PEER_SAME_MOVEMENT = "unaffected_peer_same_movement"
    COMPETING_EXPLANATION = "competing_explanation"


class ContradictionDirection(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


# --------------------------------------------------------------------------
# the atomic unit of evidence
# --------------------------------------------------------------------------
class EvidenceItem(BaseModel):
    """One document or record. Atomic: never a chunk (Part 11.3).

    A support ticket is ~80 words, a CRM note ~120, a market event ~60.
    Splitting them would break the metadata binding — which account, which
    region, which date — that the hard pre-filter depends on, and it would
    fragment the cohort signal that is the actual predictor.
    """

    model_config = ConfigDict(frozen=False)

    evidence_id: str
    source_type: SourceType
    source_id: str                       # S1 | S2 | S3
    source_table: str
    # PlainDateTime, not datetime: these rows are read out of pandas, which
    # yields `pandas.Timestamp` — a datetime subclass Pydantic accepts and the
    # LangGraph checkpointer then refuses to deserialise. See semantic.types.
    timestamp: PlainDateTime

    title: str | None = None             # subject / headline / summary
    excerpt: str = ""
    full_text: str = ""                  # what was embedded, kept for audit

    # slice metadata — drives the hard pre-filter, where most of the accuracy
    # lives (Part 11.4)
    region: str | None = None
    segment: str | None = None
    channel: str | None = None
    product_category: str | None = None
    account_id: str | None = None
    category: str | None = None
    severity: str | None = None
    service: str | None = None

    relevant_kpi: str | None = None

    # relevance signals, exposed rather than hidden behind an abstraction:
    # these are shown in the judge-facing evidence panel
    bm25_score: float | None = None
    bm25_rank: int | None = None
    dense_score: float | None = None
    dense_rank: int | None = None
    rrf_score: float | None = None
    rrf_rank: int | None = None
    retrieval_mode: RetrievalMode = RetrievalMode.HYBRID

    # How many near-identical documents this one stands for. Support tickets
    # about a single incident are frequently verbatim repeats; showing eight
    # copies of the same sentence wastes the whole result list, so one
    # representative is kept and the rest are counted here and rolled into the
    # cohort. The suppressed ids stay addressable for drill-down.
    duplicate_count: int = 0
    duplicate_ids: list[str] = Field(default_factory=list)

    entitlement_status: EntitlementStatus = EntitlementStatus.PERMITTED
    entitlement_reason: str | None = None

    freshness_lag_hours: float | None = None
    as_of: PlainDateTime | None = None

    lineage: dict = Field(default_factory=dict)

    def short(self) -> str:
        head = self.title or self.excerpt[:60]
        return f"[{self.source_type.value}:{self.evidence_id}] {head}"


# --------------------------------------------------------------------------
# retrieval
# --------------------------------------------------------------------------
class RetrievalQuery(BaseModel):
    """A query built deterministically from analytical state, never by an LLM.

    Reproducible and auditable is the point: the same movement always produces
    the same query string and the same filters (Part 11.7).
    """

    text: str
    terms: list[str] = Field(default_factory=list)
    kpi_id: str | None = None
    driver: str | None = None
    slice: dict[str, list[str]] = Field(default_factory=dict)
    window_start: date | None = None
    window_end: date | None = None
    cause_keywords: list[str] = Field(default_factory=list)
    built_from: str = ""


class FilterConditions(BaseModel):
    """The hard pre-filter. Applied BEFORE any scoring, never after."""

    window_start: date | None = None
    window_end: date | None = None
    regions: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)
    product_categories: list[str] = Field(default_factory=list)
    source_types: list[SourceType] = Field(default_factory=list)
    allowed_sources: list[str] = Field(default_factory=list)
    denied_sources: list[str] = Field(default_factory=list)

    corpus_size: int = 0
    candidates_after_entitlement: int = 0
    candidates_after_metadata: int = 0
    withheld_by_entitlement: int = 0
    withheld_by_source: dict[str, int] = Field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"{self.corpus_size} documents -> "
            f"{self.candidates_after_entitlement} after entitlement -> "
            f"{self.candidates_after_metadata} after metadata filter"
        )


class RetrievalConfig(BaseModel):
    """Everything needed to reproduce a retrieval run byte for byte."""

    embedding_model: str
    embedding_dim: int
    model_revision: str | None = None
    corpus_hash: str
    rrf_k: int = 10
    top_k: int = 8
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    normalize_embeddings: bool = True


class RetrievalTiming(BaseModel):
    """Measured, not optimised. The dataset is deliberately small."""

    filter_ms: float = 0.0
    query_embed_ms: float = 0.0
    bm25_ms: float = 0.0
    dense_ms: float = 0.0
    rrf_ms: float = 0.0
    structured_ms: float = 0.0
    cohort_ms: float = 0.0
    total_ms: float = 0.0


class RetrievalResult(BaseModel):
    """The evidence bundle handed to the (later) hypothesis layer."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[EvidenceItem] = Field(default_factory=list)
    structured_items: list[EvidenceItem] = Field(default_factory=list)
    withheld: list[EvidenceItem] = Field(default_factory=list)

    query: RetrievalQuery
    filters: FilterConditions
    config: RetrievalConfig
    timing: RetrievalTiming = Field(default_factory=RetrievalTiming)

    cohorts: list[CohortEvidence] = Field(default_factory=list)
    contradictions: list[ContradictionSignal] = Field(default_factory=list)

    retrieved_at: PlainDateTime | None = None
    method: str = ""
    persona: str | None = None
    notes: list[str] = Field(default_factory=list)

    @property
    def all_items(self) -> list[EvidenceItem]:
        """Deterministic and structured evidence in one ordered collection."""
        return list(self.structured_items) + list(self.items)

    def by_id(self, evidence_id: str) -> EvidenceItem | None:
        for item in self.all_items:
            if item.evidence_id == evidence_id:
                return item
        return None

    def explain(self) -> str:
        lines = [
            f"query: {self.query.text!r}",
            f"filters: {self.filters.summary()}",
            f"returned: {len(self.structured_items)} structured, "
            f"{len(self.items)} retrieved, {len(self.withheld)} withheld",
        ]
        if self.cohorts:
            lines.append(f"cohorts: {len(self.cohorts)}")
        if self.contradictions:
            lines.append(f"contradiction signals: {len(self.contradictions)}")
        lines.append(f"latency: {self.timing.total_ms:.1f} ms")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# cohort roll-up (Part 11.5)
# --------------------------------------------------------------------------
class CohortEvidence(BaseModel):
    """Many tickets about one incident are one piece of evidence, not many.

    Reporting each ticket separately would let volume masquerade as diversity
    and inflate any downstream count of distinct supporting documents 34-fold.
    The underlying ids are preserved so the UI can still drill down.
    """

    cohort_id: str
    label: str
    source_type: SourceType
    category: str | None = None
    cohort_dimensions: dict[str, str] = Field(default_factory=dict)

    incident_count: int = 0
    baseline_count: float = 0.0
    baseline_weeks: int = 0
    ratio: float | None = None
    delta: float = 0.0

    window_start: date | None = None
    window_end: date | None = None
    baseline_start: date | None = None
    baseline_end: date | None = None

    distinct_accounts: int = 0
    document_ids: list[str] = Field(default_factory=list)

    baseline_total: int = 0
    # nothing of this kind occurred in the whole baseline period
    novel: bool = False

    def statement(self) -> str:
        """A deterministic sentence. No LLM produced this."""
        where = ", ".join(f"{k}={v}" for k, v in self.cohort_dimensions.items())
        if self.novel:
            return (
                f"{self.incident_count} {self.label} across "
                f"{self.distinct_accounts} accounts in {where}, "
                f"{self.window_start}..{self.window_end}, against none at all "
                f"in the preceding {self.baseline_weeks} weeks"
            )
        if self.ratio is None:
            # Some prior occurrences, but the weekly median is zero, so a
            # ratio would divide by nothing. Report the counts instead of
            # inventing a multiple.
            return (
                f"{self.incident_count} {self.label} across "
                f"{self.distinct_accounts} accounts in {where}, "
                f"{self.window_start}..{self.window_end}, versus "
                f"{self.baseline_total} in the preceding "
                f"{self.baseline_weeks} weeks (weekly median 0, so no ratio "
                f"is defined)"
            )
        return (
            f"{self.incident_count} {self.label} across "
            f"{self.distinct_accounts} accounts in {where}, "
            f"{self.window_start}..{self.window_end}, versus a trailing "
            f"{self.baseline_weeks}-week median of {self.baseline_count:.1f} "
            f"({self.ratio:.1f}x)"
        )


# --------------------------------------------------------------------------
# contradiction (Part 10.4)
# --------------------------------------------------------------------------
class ContradictionSignal(BaseModel):
    """A mechanically checkable reason to doubt a hypothesis.

    Deliberately not semantic entailment: every type here is a property of
    dates, slices, directions or counts that can be recomputed and disputed.
    """

    hypothesis_id: str
    hypothesis_statement: str = ""
    contradiction_type: ContradictionType
    direction: ContradictionDirection
    strength: float = 0.0                # 0-1, deterministic

    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)

    detail: str = ""
    checked: str = ""                    # what was compared, so it is auditable


class CandidateHypothesis(BaseModel):
    """The minimal hypothesis shape retrieval needs.

    Stage 6 owns hypothesis ranking; this is only enough structure to ask
    "which evidence bears on this?" without importing that layer.
    """

    hypothesis_id: str
    statement: str
    cause_bucket: str
    slice: dict[str, list[str]] = Field(default_factory=dict)
    expected_direction: str = "decrease"      # of the KPI
    cause_date: date | None = None
    changepoint: date | None = None
    keywords: list[str] = Field(default_factory=list)


RetrievalResult.model_rebuild()
