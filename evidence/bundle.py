"""The freeze boundary (Architecture Part 5.3).

`freeze_evidence_bundle` is the last function in the pipeline that is allowed
to touch anything. After it returns:

    no database access        no retrieval        no external calls
    no new evidence           no re-scoring       no mutation

The future LLM receives this object and nothing else. That is the architectural
invariant the whole trust story rests on: a claim can be checked against a
closed set instead of against "the data", and a number with no matching
`MetricFact` has nowhere to have come from.

Immutability is enforced structurally, not by convention — every model is a
frozen Pydantic model and every collection is a tuple, so `bundle.hypotheses`
has no `append` and assigning to a field raises. The hash is computed over a
canonical serialisation, so the same inputs and the same configuration always
produce the same hash, and any change to evidence, a fact, a hypothesis, the
persona, the lever list or the security context changes it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

import yaml

from attribution.types import AttributionResult
from detection.types import DetectionOutcome, DetectionResult
from evidence import hypothesis as hypothesis_mod
from evidence import levers as levers_mod
from evidence import scoring
from evidence.types import (
    CohortRef,
    DataQualityState,
    EvidenceBundle,
    EvidenceRef,
    EvidenceStance,
    EvidenceWeight,
    FreshnessRef,
    Hypothesis,
    HypothesisStatus,
    LeverRef,
    LineageRef,
    MetricFact,
    PersonaProfile,
    SecurityContext,
)
from retrieval.types import ContradictionDirection, RetrievalResult, SourceType
from security.entitlements import Principal, source_access
from semantic import registry

BUNDLE_VERSION = "1.0.0"
PERSONA_CONFIG = Path(__file__).resolve().parent.parent / "config" / "personas.yaml"

# What each persona's narrator should lead with. Selects emphasis, never
# content: both personas get identical facts (Part 7.6).
PERSONA_EMPHASIS: dict[str, tuple[str, ...]] = {
    "ops_lead": ("what_broke", "business_impact", "action", "owner", "monitoring"),
    "finance_director": (
        "business_impact", "margin_effect", "quarter_risk", "action",
    ),
    "analytics_lead": (
        "methodology", "evidence", "alternatives", "lineage", "gate_results",
    ),
}


class BundleError(ValueError):
    """The bundle cannot be built as requested."""


# --------------------------------------------------------------------------
# canonical serialisation
# --------------------------------------------------------------------------
def _canonical(value):
    """Convert to a form whose JSON encoding is stable across runs.

    Dict keys are sorted, sets become sorted lists, and datetimes become ISO
    strings. Without this, two structurally identical bundles can hash
    differently purely because a dict was built in a different order, which
    would make the hash useless as an audit key.
    """
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, set):
        return sorted(_canonical(v) for v in value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        # Round so that a difference below reporting precision does not change
        # the hash. Anything a narrative could state is well above 1e-9.
        return round(value, 9)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def canonical_payload(bundle: EvidenceBundle) -> dict:
    """The exact structure that gets hashed.

    `created_at` and `bundle_hash` are excluded on purpose: the first is wall
    clock, so including it would make every rebuild hash differently and the
    hash would prove nothing about content; the second is the output.

    Detection and attribution results are excluded from the hash and included
    in the bundle. They are the *inputs* that produced the hypotheses and
    facts, and they carry their own wall-clock timestamps (`computed_at`); the
    hash covers what the narrative may use.
    """
    data = bundle.model_dump(
        mode="python",
        exclude={"created_at", "bundle_hash", "detection", "attribution"},
    )
    return _canonical(data)


def compute_hash(bundle: EvidenceBundle) -> str:
    payload = canonical_payload(bundle)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# persona
# --------------------------------------------------------------------------
def load_persona(persona_id: str, path: Path | None = None) -> PersonaProfile:
    p = path or PERSONA_CONFIG
    personas = yaml.safe_load(p.read_text(encoding="utf-8"))["personas"]
    if persona_id not in personas:
        raise BundleError(
            f"unknown persona '{persona_id}'; known: {sorted(personas)}"
        )
    spec = personas[persona_id]
    return PersonaProfile(
        persona_id=persona_id,
        display_name=spec["display_name"],
        title=spec["title"],
        role=spec["role"],
        user_region=spec.get("user_region"),
        wants=spec.get("wants", ""),
        narrative_style=spec.get("narrative_style", ""),
        emphasis=PERSONA_EMPHASIS.get(spec["role"], ()),
    )


def principal_for(persona: PersonaProfile) -> Principal:
    return Principal(
        user_id=persona.persona_id,
        display_name=persona.display_name,
        role=persona.role,
        user_region=persona.user_region,
    )


# --------------------------------------------------------------------------
# metric facts
# --------------------------------------------------------------------------
def build_metric_facts(
    detection: DetectionResult, attribution: AttributionResult
) -> list[MetricFact]:
    """Enumerate every number the narrative is allowed to state.

    Raw tables never travel. This list is the numeric allowlist, and a figure
    absent from it is a figure the model cannot have got from anywhere.
    """
    facts: list[MetricFact] = []
    contract = registry.get(detection.kpi_id)
    lineage = detection.lineage
    slice_t = tuple(
        sorted((k, "/".join(v)) for k, v in (detection.slice or {}).items())
    )

    def add(fact_id, metric, label, value, unit, **kw):
        if value is None:
            return
        facts.append(
            MetricFact(
                fact_id=fact_id,
                metric=metric,
                label=label,
                value=float(value),
                unit=unit,
                period_start=detection.observed_start,
                period_end=detection.observed_end,
                slice=slice_t,
                source_id=lineage.source_id if lineage else "",
                source_table=lineage.source_table if lineage else "",
                contract_version=detection.contract_version,
                as_of=lineage.as_of if lineage else None,
                **kw,
            )
        )

    m = detection.materiality
    if m is not None:
        add("F-movement-abs", detection.kpi_id, f"{contract.name} movement",
            m.abs_effect, contract.unit,
            baseline=detection.baseline_value, observed=detection.observed_value,
            delta=m.abs_effect, delta_pct=m.rel_effect_pct,
            computed_by="detection.materiality")
        add("F-movement-pct", detection.kpi_id,
            f"{contract.name} movement, relative", m.rel_effect_pct, "pct",
            delta_pct=m.rel_effect_pct, computed_by="detection.materiality")
        add("F-duration", detection.kpi_id, "Movement duration",
            m.duration_days, "days", computed_by="detection.materiality")

    if detection.baseline_value is not None:
        add("F-baseline", detection.kpi_id, f"{contract.name} baseline",
            detection.baseline_value, contract.unit,
            computed_by="detection")
    if detection.observed_value is not None:
        add("F-observed", detection.kpi_id, f"{contract.name} observed",
            detection.observed_value, contract.unit, computed_by="detection")

    # identity factors: the LMDI decomposition, one fact per driver
    if attribution.identity:
        for d in attribution.identity.drivers:
            add(f"F-driver-{d.driver}", d.driver,
                f"{d.driver.replace('_', ' ')} contribution",
                d.contribution, contract.unit,
                baseline=d.baseline, observed=d.observed,
                delta=d.contribution, delta_pct=d.contribution_pct,
                dimension="identity_factor",
                computed_by="attribution.lmdi")
            add(f"F-driver-{d.driver}-change", d.driver,
                f"{d.driver.replace('_', ' ')} change", d.factor_change_pct,
                "pct", dimension="identity_factor",
                computed_by="attribution.lmdi")

    # the winning slice
    top = attribution.top_slice
    if top is not None:
        add("F-slice-ep", detection.kpi_id,
            f"Explanatory power, {top.dimension}={top.element}",
            top.explanatory_power, "ratio", dimension=top.dimension,
            computed_by="attribution.adtributor")
        add("F-slice-delta", detection.kpi_id,
            f"Movement in {top.dimension}={top.element}", top.delta,
            contract.unit, dimension=top.dimension,
            computed_by="attribution.adtributor")

    counter = attribution.counterfactual
    if counter is not None and counter.estimate is not None:
        add("F-did", detection.kpi_id,
            f"Difference-in-differences vs {counter.control}",
            counter.estimate, contract.unit, delta_pct=counter.estimate_pct,
            computed_by="attribution.counterfactual")

    return facts


# --------------------------------------------------------------------------
# evidence refs
# --------------------------------------------------------------------------
def _weight_for(source_type: SourceType, duplicate_count: int) -> EvidenceWeight:
    """Structured records outrank prose; a lone unstructured note is weak."""
    if source_type in (SourceType.DEPLOY_CHANGELOG, SourceType.SCHEMA_CHANGE,
                       SourceType.FINANCE_ADJUSTMENT):
        return EvidenceWeight.STRONG
    if duplicate_count >= 2:
        return EvidenceWeight.MODERATE
    return EvidenceWeight.WEAK


def build_evidence_refs(
    retrieval: RetrievalResult, hypotheses: list[Hypothesis]
) -> tuple[list[EvidenceRef], list[EvidenceRef], list[CohortRef]]:
    """Split retrieved evidence into supporting and contradicting.

    Kept as two lists rather than one signed score. Collapsing them would
    destroy the thing that makes Scenario 2 honest: a hypothesis with support
    AND a problem reads differently from a hypothesis with neither.
    """
    contradicting_ids: set[str] = set()
    for s in retrieval.contradictions:
        if s.direction is ContradictionDirection.CONTRADICTS:
            contradicting_ids.update(s.contradicting_evidence_ids)

    cited: set[str] = set()
    for h in hypotheses:
        cited.update(h.supporting_evidence_ids)
        cited.update(h.contradicting_evidence_ids)

    supporting: list[EvidenceRef] = []
    contradicting: list[EvidenceRef] = []

    for item in retrieval.all_items:
        # Only evidence some hypothesis actually cites travels. The bundle is
        # the minimum needed to narrate, not the whole retrieval result.
        if item.evidence_id not in cited:
            continue
        stance = (
            EvidenceStance.CONTRADICTING
            if item.evidence_id in contradicting_ids
            else EvidenceStance.SUPPORTING
        )
        ref = EvidenceRef(
            evidence_id=item.evidence_id,
            source_type=item.source_type,
            source_id=item.source_id,
            source_table=item.source_table,
            timestamp=item.timestamp,
            title=item.title,
            excerpt=item.excerpt,
            region=item.region,
            segment=item.segment,
            channel=item.channel,
            category=item.category,
            stance=stance,
            weight=_weight_for(item.source_type, item.duplicate_count),
            duplicate_count=item.duplicate_count,
            retrieval_method=item.retrieval_mode.value,
            relevance_score=item.rrf_score,
            bm25_rank=item.bm25_rank,
            dense_rank=item.dense_rank,
            freshness_lag_hours=item.freshness_lag_hours,
            as_of=item.as_of,
        )
        (contradicting if stance is EvidenceStance.CONTRADICTING
         else supporting).append(ref)

    cohorts = [
        CohortRef(
            cohort_id=c.cohort_id,
            statement=c.statement(),
            label=c.label,
            source_type=c.source_type,
            incident_count=c.incident_count,
            baseline_count=c.baseline_count,
            baseline_weeks=c.baseline_weeks,
            ratio=c.ratio,
            novel=c.novel,
            distinct_accounts=c.distinct_accounts,
            document_ids=tuple(c.document_ids),
            window_start=c.window_start,
            window_end=c.window_end,
        )
        for c in retrieval.cohorts
    ]

    supporting.sort(key=lambda e: (-(e.relevance_score or 0.0), e.evidence_id))
    contradicting.sort(key=lambda e: (-(e.relevance_score or 0.0), e.evidence_id))
    cohorts.sort(key=lambda c: (-c.incident_count, c.cohort_id))
    return supporting, contradicting, cohorts


# --------------------------------------------------------------------------
# the freeze
# --------------------------------------------------------------------------
def freeze_evidence_bundle(
    *,
    bundle_id: str,
    persona_id: str,
    detection: DetectionResult,
    attribution: AttributionResult,
    retrieval: RetrievalResult,
    history_days: int | None = None,
    has_stable_baseline: bool = True,
    persona_path: Path | None = None,
    config: dict | None = None,
) -> EvidenceBundle:
    """Assemble and freeze. Nothing downstream may read anything else.

    Every input is already computed: this function performs no database
    access, no retrieval and no external call. It selects, shapes, scores and
    hashes, and then the object is closed.
    """
    cfg = config or scoring.load_config()
    persona = load_persona(persona_id, persona_path)
    contract = registry.get(detection.kpi_id)

    # --- hypotheses ------------------------------------------------------
    if detection.outcome is DetectionOutcome.SPARSE_HISTORY:
        hypotheses: list[Hypothesis] = []
        overall = HypothesisStatus.INSUFFICIENT
        reason = (
            "detection returned SPARSE_HISTORY; there is no established "
            "movement to explain, so no hypothesis is offered"
        )
    elif attribution.outcome.value == "MULTI_DIMENSIONAL_CASE":
        hypotheses = []
        overall = HypothesisStatus.MULTI_DIMENSIONAL
        reason = (
            "no single dimension explains the movement; the cause appears to "
            "span a combination of dimensions, which this system does not "
            "localise. Routed to human review."
        )
    elif not detection.is_material:
        hypotheses = []
        overall = HypothesisStatus.INSUFFICIENT
        reason = (
            f"detection returned {detection.outcome.value}; attribution and "
            f"explanation run only on movements established as material"
        )
    else:
        hypotheses = hypothesis_mod.build_hypotheses(
            attribution,
            retrieval,
            persona_role=persona.role,
            contract_allowed_levers=list(contract.allowed_levers or []),
            history_days=history_days,
            has_stable_baseline=has_stable_baseline,
            config=cfg,
        )
        if not hypotheses:
            overall = HypothesisStatus.INSUFFICIENT
            reason = (
                f"no hypothesis reached the reporting floor of "
                f"{cfg['separation']['min_score_to_report']:.2f}"
            )
        else:
            overall = hypotheses[0].status
            reason = hypotheses[0].status_reason

    # --- facts and evidence ----------------------------------------------
    facts = build_metric_facts(detection, attribution)
    supporting, contradicting, cohorts = build_evidence_refs(retrieval, hypotheses)

    # --- levers ----------------------------------------------------------
    lever_refs: list[LeverRef] = []
    seen_levers: set[tuple[str, str]] = set()
    for h in hypotheses:
        for lever_id in h.eligible_lever_ids:
            key = (lever_id, h.hypothesis_id)
            if key in seen_levers:
                continue
            seen_levers.add(key)
            spec = levers_mod.get(lever_id)
            rights = spec.get("decision_rights") or {}
            monitoring = spec.get("monitoring") or {}
            lever_refs.append(
                LeverRef(
                    lever_id=lever_id,
                    name=spec.get("name", lever_id),
                    owner_role=spec.get("owner_role", ""),
                    applies_to_hypothesis_id=h.hypothesis_id,
                    can_approve=tuple(rights.get("can_approve") or []),
                    can_request=tuple(rights.get("can_request") or []),
                    persona_may_approve=persona.role in (rights.get("can_approve") or []),
                    persona_may_request=persona.role in (rights.get("can_request") or []),
                    monitoring_metric=monitoring.get("metric", ""),
                    check_after_days=int(monitoring.get("check_after_days", 0)),
                    success_threshold=monitoring.get("success_threshold", ""),
                    constraints=tuple(spec.get("constraints") or []),
                    eligibility_reason=f"eligible for {h.hypothesis_id}",
                )
            )

    # --- security --------------------------------------------------------
    access = source_access(principal_for(persona))
    withheld_sources = tuple(sorted(
        {w.source_type.value for w in retrieval.withheld}
    ))
    security = SecurityContext(
        persona_id=persona.persona_id,
        role=persona.role,
        policy_version=access.policy_version,
        permitted_sources=tuple(sorted(access.allowed_sources)),
        denied_sources=tuple(sorted(access.denied_sources)),
        permitted_regions=(persona.user_region,) if persona.user_region else (),
        withheld_source_ids=withheld_sources,
        withheld_item_count=len(retrieval.withheld),
        columns_masked=tuple(sorted(
            detection.lineage.columns_masked if detection.lineage else []
        )),
    )

    # --- lineage, freshness, quality -------------------------------------
    lineage_refs: list[LineageRef] = []
    if detection.lineage:
        lg = detection.lineage
        lineage_refs.append(
            LineageRef(
                metric_id=lg.metric_id,
                source_id=lg.source_id,
                source_table=lg.source_table,
                contract_version=lg.contract_version,
                as_of=lg.as_of,
                row_count=lg.row_count,
                filters_applied=tuple(lg.filters_applied),
                compiled_sql_hash=hashlib.sha256(
                    lg.compiled_sql.encode("utf-8")
                ).hexdigest()[:16],
            )
        )

    freshness_refs: list[FreshnessRef] = []
    if detection.freshness:
        f = detection.freshness
        freshness_refs.append(
            FreshnessRef(
                source_id=getattr(f, "source_id", ""),
                as_of=getattr(f, "as_of", None),
                lag_hours=getattr(f, "lag_hours", None),
                status=getattr(f, "status", "") or "",
                cadence=getattr(f, "cadence", "") or "",
            )
        )

    quality: list[DataQualityState] = []
    notes: list[str] = []
    for note in detection.preprocessing_notes:
        notes.append(note)
        if "imputed" in note.lower():
            quality.append(DataQualityState.IMPUTED)
        if "schema stitch" in note.lower():
            quality.append(DataQualityState.SCHEMA_CHANGE_APPLIED)
    if detection.outcome is DetectionOutcome.SPARSE_HISTORY:
        quality.append(DataQualityState.SPARSE)
    if not quality:
        quality.append(DataQualityState.OK)

    causal_permissions = tuple(
        (h.hypothesis_id, h.causal_language_allowed) for h in hypotheses
    )

    bundle = EvidenceBundle(
        bundle_id=bundle_id,
        bundle_version=BUNDLE_VERSION,
        created_at=datetime.now(),
        persona=persona,
        kpi_id=detection.kpi_id,
        kpi_name=contract.name,
        window_start=detection.observed_start or detection.analysis_start,
        window_end=detection.observed_end or detection.analysis_end,
        metric_facts=tuple(facts),
        detection=detection,
        attribution=attribution,
        hypotheses=tuple(hypotheses),
        overall_status=overall,
        status_reason=reason,
        supporting_evidence=tuple(supporting),
        contradicting_evidence=tuple(contradicting),
        cohorts=tuple(cohorts),
        allowed_levers=tuple(lever_refs),
        lineage=tuple(lineage_refs),
        freshness=tuple(freshness_refs),
        security_context=security,
        methods_used=(
            detection.method,
            attribution.method,
            retrieval.method,
        ),
        data_quality_state=tuple(dict.fromkeys(quality)),
        data_quality_notes=tuple(notes),
        causal_language_allowed=bool(
            hypotheses and hypotheses[0].causal_language_allowed
        ),
        causal_permissions=causal_permissions,
        scoring_version=cfg["version"],
        config_versions=(
            ("scoring", cfg["version"]),
            ("levers", levers_mod.load_catalogue()["version"]),
            ("security_policy", access.policy_version),
            ("bundle", BUNDLE_VERSION),
        ),
        notes=tuple(retrieval.notes),
    )

    # The hash is the last thing computed, over everything above.
    return bundle.model_copy(update={"bundle_hash": compute_hash(bundle)})


def verify_hash(bundle: EvidenceBundle) -> bool:
    """Recompute the hash. False means the bundle was altered after freezing."""
    return compute_hash(bundle) == bundle.bundle_hash
