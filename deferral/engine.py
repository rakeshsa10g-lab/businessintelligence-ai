"""Cost-sensitive deferral and the analyst packet (Architecture Part 14.4).

    E[loss | model] = (1 - p_model) x cost_of_error
    E[loss | human] = (1 - p_human) x cost_of_error + review_cost
    defer  <=>  E[loss | model] >= E[loss | human]

Not `confidence < 0.7 -> human`. Selective prediction asks whether the model is
confident enough; learning to defer asks who is more likely to be right on this
case and whether review is worth its cost (Mozannar & Sontag 2020).

The difference shows up in two places a threshold cannot reach: a HIGH-band
call on a low-value decision can be automated even though a human would beat
it slightly, because the review costs more than the improvement is worth; and a
MEDIUM-band call on an expensive decision defers even though the threshold
would have passed it.

Abstention is a third outcome, not a severe deferral. When the bundle has
nothing to explain there is nothing for a reviewer to review, and sending it to
one wastes the scarcest resource in the system.
"""

from __future__ import annotations

import functools
from datetime import datetime
from pathlib import Path

import yaml

from confidence.types import Confidence, ConfidenceBand
from deferral.types import (
    ABSTENTION_REMEDY,
    AbstentionReason,
    AnalystPacket,
    AutomationScope,
    DeferralDecision,
    DeferralOutcome,
    LossEstimate,
)
from detection.types import DetectionOutcome
from evidence.types import EvidenceBundle, HypothesisStatus
from recommendation.types import RecommendationSet

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "deferral.yaml"


class DeferralError(ValueError):
    """The deferral policy is unusable."""


@functools.lru_cache(maxsize=4)
def load_policy(path: str | None = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise DeferralError(f"no deferral policy at {p}")
    policy = yaml.safe_load(p.read_text(encoding="utf-8"))
    for key in ("version", "model_accuracy_fallback", "human_accuracy",
                "decision_value_inr", "review", "overrides"):
        if key not in policy:
            raise DeferralError(f"deferral policy is missing '{key}'")
    return policy


def reload_policy() -> None:
    load_policy.cache_clear()


# --------------------------------------------------------------------------
# abstention: which state is this?
# --------------------------------------------------------------------------
def classify_abstention(
    bundle: EvidenceBundle, confidence: Confidence
) -> AbstentionReason:
    """Six distinct states, checked most-specific first.

    Order matters. A sparse-history bundle is also evidence-insufficient, and
    reporting the general reason when the specific one is known tells the
    reader less than the system knows.
    """
    detection = bundle.detection

    if detection is not None:
        if detection.outcome is DetectionOutcome.SPARSE_HISTORY:
            return AbstentionReason.SPARSE_HISTORY
        if detection.outcome is DetectionOutcome.INSUFFICIENT_DATA:
            return AbstentionReason.SPARSE_HISTORY
        if not detection.is_material:
            return AbstentionReason.NO_MATERIAL_EVENT

    if bundle.overall_status is HypothesisStatus.MULTI_DIMENSIONAL:
        return AbstentionReason.MULTI_DIMENSIONAL

    # A restricted reader who lost the evidence that would have explained the
    # movement is a different failure from having no evidence at all: another
    # reader can answer this one.
    if (
        bundle.security_context.withheld_item_count > 0
        and (not bundle.hypotheses
             or bundle.hypotheses[0].evidence_count < 2)
    ):
        return AbstentionReason.UNAUTHORIZED_INFORMATION

    if not bundle.hypotheses:
        return AbstentionReason.EVIDENCE_INSUFFICIENCY

    top = bundle.hypotheses[0]
    if top.status is HypothesisStatus.CONFLICTED:
        return AbstentionReason.CONFLICTING_EVIDENCE
    if top.status is HypothesisStatus.INSUFFICIENT:
        return AbstentionReason.EVIDENCE_INSUFFICIENCY
    if confidence.band is ConfidenceBand.INSUFFICIENT:
        return AbstentionReason.EVIDENCE_INSUFFICIENCY

    # The movement and its driver stand; only the causal wording was refused.
    # This is NOT an abstention from the finding - it is a constraint on how
    # the finding may be phrased, and the decision path continues.
    if not top.causal_language_allowed:
        return AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM

    return AbstentionReason.NONE


# --------------------------------------------------------------------------
# the rule
# --------------------------------------------------------------------------
def model_accuracy(confidence: Confidence, policy: dict) -> tuple[float, str]:
    """p_model from observed calibration where it exists, else the fallback."""
    if confidence.calibration is not None and confidence.estimated_accuracy is not None:
        # The SMOOTHED rate, not the raw one: an unbeaten 12/12 would make the
        # model arm's loss identically zero and the comparison meaningless.
        return confidence.estimated_accuracy, (
            f"observed {confidence.calibration.render()}, "
            f"Laplace-smoothed to {confidence.estimated_accuracy:.3f} for the "
            f"loss comparison"
        )
    fallback = policy["model_accuracy_fallback"]
    band = confidence.band.value
    return float(fallback.get(band, fallback.get("UNCALIBRATED", 0.5))), (
        f"fallback for an uncalibrated {band} band"
    )


def human_accuracy(cause_bucket: str, policy: dict) -> float:
    table = policy["human_accuracy"]
    return float(table.get(cause_bucket, table["default"]))


def decide(
    bundle: EvidenceBundle,
    confidence: Confidence,
    recommendations: RecommendationSet,
    *,
    queue_depth: int = 0,
    policy: dict | None = None,
) -> DeferralDecision:
    """Automate, review, or abstain."""
    pol = policy or load_policy()
    version = pol["version"]

    reason = classify_abstention(bundle, confidence)
    hard_abstentions = {
        AbstentionReason.NO_MATERIAL_EVENT,
        AbstentionReason.SPARSE_HISTORY,
        AbstentionReason.EVIDENCE_INSUFFICIENCY,
        AbstentionReason.UNAUTHORIZED_INFORMATION,
        AbstentionReason.MULTI_DIMENSIONAL,
    }
    if reason in hard_abstentions:
        return DeferralDecision(
            outcome=DeferralOutcome.ABSTAIN, abstain=True,
            abstention_reason=reason, remedy=ABSTENTION_REMEDY[reason],
            rationale=(
                f"{reason.value}: {bundle.status_reason or 'nothing to explain'}. "
                f"There is nothing for a reviewer to review."
            ),
            policy_version=version,
            queue_depth=queue_depth,
        )

    top = bundle.hypotheses[0]
    cost_of_error = float(
        pol["decision_value_inr"].get(
            bundle.persona.role, pol["decision_value_inr"]["default"]
        )
    )
    p_model, model_basis = model_accuracy(confidence, pol)
    p_human = human_accuracy(top.cause_bucket, pol)

    review_cfg = pol["review"]
    review_cost = (
        review_cfg["analyst_hourly_inr"] * review_cfg["estimated_review_hours"]
        + review_cfg["delay_cost_per_hour_inr"] * review_cfg["delay_hours_if_deferred"]
    )

    model_arm = LossEstimate(
        label="model", accuracy=p_model, cost_of_error=cost_of_error,
        error_loss=(1 - p_model) * cost_of_error,
        total=(1 - p_model) * cost_of_error, basis=model_basis,
    )
    human_arm = LossEstimate(
        label="human", accuracy=p_human, cost_of_error=cost_of_error,
        error_loss=(1 - p_human) * cost_of_error,
        additional_cost=review_cost,
        total=(1 - p_human) * cost_of_error + review_cost,
        basis=f"seeded p_human for cause bucket '{top.cause_bucket}'",
    )

    defer = model_arm.total >= human_arm.total
    override: str | None = None

    # --- guardrails: where the average is the wrong frame -----------------
    primary = recommendations.primary
    never_automate = set(pol["overrides"].get("never_automate_lever_ids") or [])
    if primary is not None and primary.lever_id in never_automate:
        defer = True
        override = (
            f"lever {primary.lever_id} is never automated: the asymmetry "
            f"between a wrong action and a delayed one is not captured by a "
            f"single cost-of-error figure"
        )

    scope = AutomationScope.NONE
    if primary is not None:
        if primary.persona_right.value == "approve":
            scope = AutomationScope.EXECUTE
        elif primary.persona_right.value == "request":
            scope = AutomationScope.RAISE_REQUEST

    if pol["overrides"].get("require_persona_any_rights") and primary is not None:
        if scope is AutomationScope.NONE:
            defer = True
            override = override or (
                f"role '{bundle.persona.role}' has no rights on "
                f"{primary.lever_id}; nothing can be automated on behalf of "
                f"someone who could neither approve nor request it"
            )

    if confidence.band is ConfidenceBand.UNCALIBRATED:
        defer = True
        override = override or (
            "confidence is UNCALIBRATED: without an observed hit rate there is "
            "no p_model to put in the comparison, so the arithmetic that would "
            "justify automating is unavailable"
        )

    capacity_ok = queue_depth < review_cfg["max_queue_depth"]
    if defer and not capacity_ok:
        return DeferralDecision(
            outcome=DeferralOutcome.ABSTAIN, abstain=True,
            abstention_reason=AbstentionReason.EVIDENCE_INSUFFICIENCY,
            remedy=(
                "review capacity is exhausted; promising a human who will not "
                "arrive in time is worse than saying so"
            ),
            expected_model_loss=model_arm.total,
            expected_human_loss=human_arm.total,
            review_cost=review_cost,
            model_arm=model_arm, human_arm=human_arm,
            p_model=p_model, p_human=p_human, cost_of_error=cost_of_error,
            cause_bucket=top.cause_bucket,
            capacity_ok=False, queue_depth=queue_depth,
            rationale=(
                f"review is indicated but the queue is at {queue_depth} "
                f"against a maximum of {review_cfg['max_queue_depth']}"
            ),
            policy_version=version,
        )

    if defer:
        return DeferralDecision(
            outcome=DeferralOutcome.REVIEW, review=True,
            abstention_reason=(
                AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM
                if reason is AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM
                else (AbstentionReason.CONFLICTING_EVIDENCE
                      if reason is AbstentionReason.CONFLICTING_EVIDENCE
                      else AbstentionReason.NONE)
            ),
            remedy=ABSTENTION_REMEDY.get(reason, ""),
            expected_model_loss=model_arm.total,
            expected_human_loss=human_arm.total,
            review_cost=review_cost,
            model_arm=model_arm, human_arm=human_arm,
            p_model=p_model, p_human=p_human, cost_of_error=cost_of_error,
            cause_bucket=top.cause_bucket,
            # Scope describes what WAS automated, not what could have been.
            # A review carrying `execute` invites a consumer that reads the
            # scope without reading the outcome to act on a decision that
            # deliberately declined to act. The persona's authority is not
            # lost by this: it is on the recommendation, as `persona_right`.
            automation_scope=AutomationScope.NONE,
            override_applied=override, capacity_ok=capacity_ok,
            queue_depth=queue_depth,
            rationale=(
                override or (
                    f"E[loss|model] {model_arm.total:,.0f} >= "
                    f"E[loss|human]+review {human_arm.total:,.0f} INR"
                )
            ),
            policy_version=version,
        )

    return DeferralDecision(
        outcome=DeferralOutcome.AUTOMATE, automated=True,
        expected_model_loss=model_arm.total,
        expected_human_loss=human_arm.total,
        review_cost=review_cost,
        model_arm=model_arm, human_arm=human_arm,
        p_model=p_model, p_human=p_human, cost_of_error=cost_of_error,
        cause_bucket=top.cause_bucket,
        automation_scope=scope,
        capacity_ok=capacity_ok, queue_depth=queue_depth,
        rationale=(
            f"E[loss|model] {model_arm.total:,.0f} < "
            f"E[loss|human]+review {human_arm.total:,.0f} INR; review would "
            f"cost more than the accuracy it buys"
        ),
        policy_version=version,
    )


# --------------------------------------------------------------------------
# the packet
# --------------------------------------------------------------------------
def build_analyst_packet(
    bundle: EvidenceBundle,
    confidence: Confidence,
    decision: DeferralDecision,
    recommendations: RecommendationSet,
) -> AnalystPacket:
    """The investigation, already done, handed over.

    A generic "contact an analyst" message moves the work without reducing it.
    This packet carries the movement, the ranked hypotheses with evidence on
    both sides, the methods, the lineage, what is missing, and the one question
    that would resolve it.
    """
    movement = bundle.fact("F-movement-pct")
    movement_abs = bundle.fact("F-movement-abs")
    summary = (
        f"{movement.value:+.2f}%"
        + (f" ({movement_abs.value:+,.0f} INR)" if movement_abs else "")
        if movement else "no measured movement"
    )

    missing: list[str] = []
    if bundle.security_context.withheld_item_count:
        missing.append(
            f"{bundle.security_context.withheld_item_count} source(s) withheld "
            f"from this reader: "
            f"{', '.join(bundle.security_context.withheld_source_ids)}"
        )
    if bundle.hypotheses:
        top = bundle.hypotheses[0]
        if top.evidence_count < 3:
            missing.append(
                f"only {top.evidence_count} distinct document(s) corroborate "
                f"the leading hypothesis"
            )
        if not top.causal_language_allowed:
            missing.append(
                f"causal language was refused: {top.causal_language_reason}"
            )
    for note in bundle.data_quality_notes[:2]:
        missing.append(f"data preparation: {note}")

    question = _clarification_for(bundle, decision)

    return AnalystPacket(
        packet_id=f"PKT-{bundle.bundle_id}",
        bundle_id=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        created_at=datetime.now(),
        persona_id=bundle.persona.persona_id,
        persona_role=bundle.persona.role,
        kpi_id=bundle.kpi_id,
        kpi_name=bundle.kpi_name,
        window_start=bundle.window_start,
        window_end=bundle.window_end,
        movement_summary=summary,
        movement_facts=tuple(
            (f.fact_id, f.render()) for f in bundle.metric_facts[:8]
        ),
        hypotheses=tuple(
            (h.hypothesis_id, h.statement, h.status.value)
            for h in bundle.hypotheses
        ),
        supporting_evidence=tuple(
            (e.evidence_id, (e.title or e.excerpt))
            for e in bundle.supporting_evidence[:8]
        ),
        contradicting_evidence=tuple(
            (e.evidence_id, (e.title or e.excerpt))
            for e in bundle.contradicting_evidence[:8]
        ),
        cohorts=tuple(c.statement for c in bundle.cohorts[:4]),
        methods_used=tuple(bundle.methods_used),
        lineage=tuple(
            f"{lg.metric_id} from {lg.source_table} ({lg.source_id}), "
            f"contract {lg.contract_version}, {lg.row_count} rows"
            for lg in bundle.lineage
        ),
        missing_information=tuple(missing),
        recommended_clarification=question,
        suggested_actions=tuple(
            (r.lever_id, r.lever_name) for r in recommendations.recommendations
        ),
        confidence_render=confidence.render(),
        confidence_band=confidence.band.value,
        deferral_rationale=decision.rationale,
        estimated_review_minutes=int(
            load_policy()["review"]["estimated_review_hours"] * 60
        ),
    )


def _clarification_for(bundle: EvidenceBundle, decision: DeferralDecision) -> str:
    """A specific question, not "please review".

    "Two explanations are equally supported; which one?" is answerable in a
    minute. "Please review this insight" is an hour of re-deriving what the
    system already knows.
    """
    if decision.abstention_reason is AbstentionReason.CONFLICTING_EVIDENCE:
        options = [h.statement for h in bundle.hypotheses[:2]]
        return (
            f"Two explanations are equally supported and imply different "
            f"owners. Which is it: ({options[0]}) or ({options[1]})?"
        )
    if decision.abstention_reason is AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM:
        top = bundle.hypotheses[0]
        return (
            f"The association holds but the counterfactual did not license a "
            f"causal claim ({top.causal_language_reason}). Do you have "
            f"knowledge outside this evidence set that establishes causation?"
        )
    if bundle.hypotheses:
        top = bundle.hypotheses[0]
        return (
            f"Is '{top.statement}' the correct explanation, given the "
            f"{top.evidence_count} document(s) cited?"
        )
    return "No explanation was formed. What evidence source is missing?"
