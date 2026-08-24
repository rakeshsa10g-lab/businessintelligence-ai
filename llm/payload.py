"""The narration view of a bundle — exactly what the model is shown.

The acceptance criterion is that the LLM receives only the EvidenceBundle. This
module builds a *projection* of it: the fields a narrator needs, and nothing
else.

Two things are deliberately withheld, and neither is a fact the narrative could
have used:

**Compiled SQL and raw analytical objects.** `bundle.detection` and
`bundle.attribution` carry the full statistical state — residual arrays, the
compiled query text, bootstrap distributions. A narrator has no use for them,
they would dominate the token budget, and the compiled SQL contains the
entitlement predicates. Their *conclusions* are already in the bundle as metric
facts, hypotheses and lineage.

**Scores and internal thresholds.** A hypothesis score is a ranking artefact,
not a business figure. Showing it invites the model to quote it, and quoting it
would fail the numeric check — which is the right outcome, but a prompt design
that tempts a model into a violation is a bad prompt design.

What the model does see is every metric fact, every hypothesis with its status
and causal permission, every evidence excerpt, the cohort statements, the
eligible levers and the persona. If a narrative cannot be written from that,
the bundle is the thing to fix.
"""

from __future__ import annotations

import json

from evidence.types import EvidenceBundle

MAX_EVIDENCE_ITEMS = 12
MAX_EXCERPT_CHARS = 220


def build_payload(bundle: EvidenceBundle) -> dict:
    """The JSON the narrator is given."""
    return {
        "bundle_id": bundle.bundle_id,
        "bundle_hash": bundle.bundle_hash,
        "kpi": {
            "id": bundle.kpi_id,
            "name": bundle.kpi_name,
            "window_start": bundle.window_start.isoformat(),
            "window_end": bundle.window_end.isoformat(),
        },
        "persona": {
            "name": bundle.persona.display_name,
            "title": bundle.persona.title,
            "role": bundle.persona.role,
            "wants": bundle.persona.wants,
            "style": bundle.persona.narrative_style,
            "lead_with": list(bundle.persona.emphasis),
        },
        "overall_status": bundle.overall_status.value,
        "status_reason": bundle.status_reason,
        "metric_facts": [
            {
                "fact_id": f.fact_id,
                "label": f.label,
                "value": f.value,
                "unit": f.unit,
                "baseline": f.baseline,
                "observed": f.observed,
                "delta_pct": f.delta_pct,
                "period": (
                    f"{f.period_start}..{f.period_end}"
                    if f.period_start else None
                ),
            }
            for f in bundle.metric_facts
        ],
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "statement": h.statement,
                "cause_bucket": h.cause_bucket,
                "status": h.status.value,
                "rank": h.rank,
                "driver": h.driver_name,
                "slice": {k: v for k, v in h.slice},
                "causal_language_allowed": h.causal_language_allowed,
                "causal_language_reason": h.causal_language_reason,
                "temporal_precedence": h.temporal_precedence,
                "robustness": h.robustness,
                "evidence_quality": h.evidence_quality.value,
                "distinct_supporting_documents": h.evidence_count,
                "supporting_evidence_ids": list(h.supporting_evidence_ids),
                "contradicting_evidence_ids": list(h.contradicting_evidence_ids),
                "cohort_ids": list(h.cohort_ids),
                "eligible_lever_ids": list(h.eligible_lever_ids),
            }
            for h in bundle.hypotheses
        ],
        "supporting_evidence": _evidence(bundle.supporting_evidence),
        "contradicting_evidence": _evidence(bundle.contradicting_evidence),
        "cohorts": [
            {
                "cohort_id": c.cohort_id,
                "statement": c.statement,
                "source_type": c.source_type.value,
            }
            for c in bundle.cohorts
        ],
        "allowed_levers": [
            {
                "lever_id": lever.lever_id,
                "name": lever.name,
                "owner_role": lever.owner_role,
                "applies_to_hypothesis_id": lever.applies_to_hypothesis_id,
                "persona_may_approve": lever.persona_may_approve,
                "persona_may_request": lever.persona_may_request,
                "monitoring_metric": lever.monitoring_metric,
                "check_after_days": lever.check_after_days,
                "success_threshold": lever.success_threshold,
                "constraints": list(lever.constraints),
            }
            for lever in bundle.allowed_levers
        ],
        "security_context": {
            "role": bundle.security_context.role,
            "permitted_regions": list(bundle.security_context.permitted_regions),
            "withheld_sources": list(bundle.security_context.withheld_source_ids),
            "withheld_item_count": bundle.security_context.withheld_item_count,
        },
        "data_quality": {
            "state": [q.value for q in bundle.data_quality_state],
            "notes": list(bundle.data_quality_notes),
        },
        "causal_permissions": {
            hid: allowed for hid, allowed in bundle.causal_permissions
        },
    }


def _evidence(items) -> list[dict]:
    return [
        {
            "evidence_id": e.evidence_id,
            "source_type": e.source_type.value,
            "date": e.timestamp.date().isoformat(),
            "title": e.title,
            "excerpt": e.excerpt[:MAX_EXCERPT_CHARS],
            "region": e.region,
            "channel": e.channel,
            "weight": e.weight.value,
            "near_identical_duplicates": e.duplicate_count,
        }
        for e in items[:MAX_EVIDENCE_ITEMS]
    ]


def render_user_message(bundle: EvidenceBundle) -> str:
    payload = build_payload(bundle)
    return (
        "Here is the frozen EvidenceBundle. Narrate it for the persona it "
        "names.\n\n"
        + json.dumps(payload, indent=2, ensure_ascii=False)
    )


def render_retry_message(
    bundle: EvidenceBundle, previous: dict, violations: list
) -> str:
    """The retry message: the same bundle, the failed output, the violations.

    No new evidence, no new facts, no tools. The model is being asked to fix
    what it wrote, not to look again — which is the difference between a
    correction and a second investigation.
    """
    lines = [
        "Your previous narrative failed deterministic verification and was "
        "not delivered.",
        "",
        "Below are the typed violations. Each names a specific rule and the "
        "value that broke it. Rewrite the narrative so that none of them "
        "fires.",
        "",
        "You are NOT being given new evidence. The bundle is unchanged and is "
        "repeated below. Every fix must come from what is already there: if a "
        "number cannot be cited, remove it; if a claim cannot be supported, "
        "drop the claim; if causal wording was refused, rewrite it as an "
        "association.",
        "",
        "VIOLATIONS",
    ]
    for v in violations:
        lines.append(f"- [{v.severity.value}] {v.code.value}"
                     + (f" in claim {v.claim_id}" if v.claim_id else ""))
        lines.append(f"    {v.detail}")
        if v.expected:
            lines.append(f"    expected: {v.expected}")
    lines += [
        "",
        "YOUR PREVIOUS OUTPUT",
        json.dumps(previous, indent=2, ensure_ascii=False),
        "",
        "THE UNCHANGED BUNDLE",
        json.dumps(build_payload(bundle), indent=2, ensure_ascii=False),
    ]
    return "\n".join(lines)
