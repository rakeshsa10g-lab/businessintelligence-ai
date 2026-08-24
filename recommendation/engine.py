"""Turning an approved hypothesis into a bounded recommendation (Part 14).

    driver -> eligible lever(s) -> computed impact -> owner -> monitoring plan

Eligibility was already decided in Stage 6 and frozen into the bundle; this
layer takes those levers and completes them. Nothing here re-derives whether a
lever applies, because that decision belongs to the bundle and re-deciding it
would create two answers to one question.

**The impact is read, not estimated.** `recover_to_baseline` uses the absolute
movement detection measured, multiplied by a recovery fraction the catalogue
declares. `elasticity_estimate` is deliberately wider and says so. A model is
never asked for a number, and there is no field for it to put one in.

**The monitoring metric is resolved against the semantic catalogue.** A plan
naming a KPI that does not exist is a plan nobody can execute, and in prose it
would be indistinguishable from a real one.
"""

from __future__ import annotations

from confidence.types import Confidence, ConfidenceBand
from evidence import levers as levers_mod
from evidence.types import EvidenceBundle, Hypothesis
from recommendation.types import (
    DecisionRight,
    ExpectedImpact,
    ImpactModel,
    MonitoringPlan,
    Recommendation,
    RecommendationSet,
)
from semantic import registry


class RecommendationError(ValueError):
    """A recommendation could not be built as requested."""


class LeverHallucination(RecommendationError):
    """A lever id that is not in the catalogue.

    Named for the telemetry event in Part 14.3. Because the field is a
    schema-constrained enum this should be near zero, and the counter being
    visibly zero is the point.
    """


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def validate_lever_id(lever_id: str) -> dict:
    """Reject anything not in the catalogue. The hard rule from Part 14.3."""
    try:
        return levers_mod.get(lever_id)
    except levers_mod.LeverError as exc:
        raise LeverHallucination(
            f"lever '{lever_id}' is not in the catalogue "
            f"(v{levers_mod.load_catalogue()['version']}); the recommendation "
            f"is dropped. Known levers: "
            f"{', '.join(sorted(levers_mod.known_lever_ids()))}"
        ) from exc


def persona_right(spec: dict, persona_role: str) -> DecisionRight:
    rights = spec.get("decision_rights") or {}
    if persona_role in (rights.get("can_approve") or []):
        return DecisionRight.APPROVE
    if persona_role in (rights.get("can_request") or []):
        return DecisionRight.REQUEST
    if persona_role in (rights.get("notify") or []):
        return DecisionRight.NOTIFY
    return DecisionRight.NONE


# --------------------------------------------------------------------------
# impact — computed, never generated
# --------------------------------------------------------------------------
def compute_impact(
    spec: dict, bundle: EvidenceBundle, hypothesis: Hypothesis
) -> ExpectedImpact:
    """The expected impact range, from state the system already measured."""
    impact_cfg = spec.get("expected_impact") or {}
    model = ImpactModel(impact_cfg.get("formula", "none"))
    unit = impact_cfg.get("unit", "INR")
    basis = impact_cfg.get("basis", "")
    high_frac = float(impact_cfg.get("recovery_fraction", 0.0))
    low_frac = float(impact_cfg.get("recovery_fraction_low", 0.0))

    if model in (ImpactModel.NO_BUSINESS_IMPACT, ImpactModel.NONE):
        return ExpectedImpact(
            model=model, low=0.0, high=0.0, unit=unit, basis=basis,
            recovery_fraction_low=0.0, recovery_fraction_high=0.0,
        )

    movement_fact = bundle.fact("F-movement-abs")
    if movement_fact is None:
        # No measured movement means no recoverable amount. Returning a
        # plausible-looking number here would be inventing the one figure this
        # whole layer exists to keep honest.
        return ExpectedImpact(
            model=model, low=0.0, high=0.0, unit=unit,
            basis="no measured movement in the bundle; no amount is claimed",
            recovery_fraction_low=low_frac, recovery_fraction_high=high_frac,
        )

    measured = abs(movement_fact.value)
    return ExpectedImpact(
        model=model,
        low=measured * low_frac,
        high=measured * high_frac,
        unit=unit,
        basis=basis or "movement measured by detection",
        source_fact_id=movement_fact.fact_id,
        measured_movement=movement_fact.value,
        recovery_fraction_low=low_frac,
        recovery_fraction_high=high_frac,
    )


# --------------------------------------------------------------------------
# monitoring — resolved against the semantic catalogue
# --------------------------------------------------------------------------
def build_monitoring_plan(spec: dict, bundle: EvidenceBundle) -> MonitoringPlan:
    monitoring = spec.get("monitoring") or {}
    metric_id = monitoring.get("metric", "")

    try:
        contract = registry.get(metric_id)
        metric_name = contract.name
        from_catalogue = True
    except Exception:
        raise RecommendationError(
            f"lever '{spec['lever_id']}' names monitoring metric "
            f"'{metric_id}', which is not in the semantic catalogue. A "
            f"monitoring plan pointing at a KPI that does not exist cannot be "
            f"executed."
        ) from None

    baseline_fact = bundle.fact("F-baseline")
    return MonitoringPlan(
        metric_id=metric_id,
        metric_name=metric_name,
        check_after_days=int(monitoring.get("check_after_days", 0)),
        success_threshold=monitoring.get("success_threshold", ""),
        baseline_value=baseline_fact.value if baseline_fact else None,
        baseline_fact_id=baseline_fact.fact_id if baseline_fact else None,
        from_semantic_catalogue=from_catalogue,
    )


# --------------------------------------------------------------------------
# urgency
# --------------------------------------------------------------------------
def urgency_for(spec: dict, confidence: Confidence) -> str:
    """Derived from how fast the lever asks to be checked, and the band.

    A one-day check window on a high-confidence finding is urgent; the same
    lever on an uncalibrated one is not, because nobody should be running at a
    reading the system cannot vouch for.
    """
    days = int((spec.get("monitoring") or {}).get("check_after_days", 7))
    if confidence.band is ConfidenceBand.HIGH and days <= 2:
        return "immediate"
    if confidence.band in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM) and days <= 7:
        return "same-week"
    return "routine"


# --------------------------------------------------------------------------
# the engine
# --------------------------------------------------------------------------
def recommend(
    bundle: EvidenceBundle,
    confidence: Confidence,
    *,
    max_recommendations: int = 3,
) -> RecommendationSet:
    """Complete every eligible lever the bundle carries for its top hypothesis."""
    catalogue_version = levers_mod.load_catalogue()["version"]
    persona_role = bundle.persona.role

    if not bundle.hypotheses:
        return RecommendationSet(
            bundle_id=bundle.bundle_id, bundle_hash=bundle.bundle_hash,
            persona_id=bundle.persona.persona_id,
            catalogue_version=catalogue_version,
            notes=(
                f"no hypothesis to act on: {bundle.status_reason}",
            ),
        )

    top = bundle.hypotheses[0]
    built: list[Recommendation] = []
    rejected: list[tuple[str, str]] = []
    notes: list[str] = []

    for lever_ref in bundle.allowed_levers:
        if lever_ref.applies_to_hypothesis_id != top.hypothesis_id:
            continue

        try:
            spec = validate_lever_id(lever_ref.lever_id)
        except LeverHallucination as exc:
            rejected.append((lever_ref.lever_id, str(exc)))
            continue

        # The confidence gate: some actions are too disruptive to recommend
        # off a weak reading, whatever the evidence strength was.
        allowed_bands = spec.get("allowed_confidence_context") or []
        if allowed_bands and confidence.band.value not in allowed_bands:
            rejected.append((
                lever_ref.lever_id,
                f"requires confidence in {allowed_bands}; this bundle is "
                f"{confidence.band.value}",
            ))
            continue

        eligible_personas = spec.get("eligible_personas") or []
        if eligible_personas and persona_role not in eligible_personas:
            rejected.append((
                lever_ref.lever_id,
                f"not offered to role '{persona_role}'",
            ))
            continue

        right = persona_right(spec, persona_role)
        if right is DecisionRight.NONE:
            rejected.append((
                lever_ref.lever_id,
                f"role '{persona_role}' has no decision rights on this lever",
            ))
            continue

        try:
            monitoring = build_monitoring_plan(spec, bundle)
        except RecommendationError as exc:
            rejected.append((lever_ref.lever_id, str(exc)))
            continue

        impact = compute_impact(spec, bundle, top)
        rights = spec.get("decision_rights") or {}

        built.append(Recommendation(
            recommendation_id=f"REC-{bundle.bundle_id}-{lever_ref.lever_id}",
            lever_id=lever_ref.lever_id,
            lever_name=spec.get("name", lever_ref.lever_id),
            driver_id=spec.get("driver_id"),
            hypothesis_id=top.hypothesis_id,
            action_template=(spec.get("action_template") or "").strip(),
            action_text=None,          # only a narrator fills this
            owner_role=spec.get("owner_role", ""),
            persona_right=right,
            approver_roles=tuple(rights.get("can_approve") or []),
            expected_impact=impact,
            monitoring=monitoring,
            confidence_band=confidence.band,
            constraints=tuple(spec.get("constraints") or []),
            urgency=urgency_for(spec, confidence),
            rationale=(
                f"{top.statement}; {top.status.value} with "
                f"{top.evidence_count} distinct supporting document(s)"
            ),
            catalogue_version=catalogue_version,
        ))

    # Monitor-only is a real recommendation, but it is the weakest one: it
    # ranks last so a substantive action is never buried beneath "wait".
    built.sort(key=lambda r: (r.lever_id == "L_MONITOR_ONLY", r.lever_id))

    if not built:
        notes.append(
            "no lever survived the eligibility, confidence and decision-rights "
            "checks; recommending nothing is the correct output"
        )

    return RecommendationSet(
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        persona_id=bundle.persona.persona_id,
        recommendations=tuple(built[:max_recommendations]),
        rejected_lever_ids=tuple(rejected),
        catalogue_version=catalogue_version,
        notes=tuple(notes),
    )
