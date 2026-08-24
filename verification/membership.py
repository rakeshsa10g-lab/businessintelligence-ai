"""Checks 2 and 9 — driver membership and lever membership.

Every cause a narrative names must be a hypothesis the analysis produced, and
every recommendation must name a lever from the approved catalogue. Both are
set-membership tests, which is the whole point: decidable, fast, and not open
to argument.

Naming a driver the analysis never produced is not a wording problem. It is a
finding the system did not make, presented as one it did.
"""

from __future__ import annotations

from evidence.types import EvidenceBundle
from verification.types import (
    Narrative,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK_DRIVER = "driver_membership"
CHECK_LEVER = "lever_membership"
CHECK_METRIC = "metric_ref_validity"


def check_drivers(narrative: Narrative, bundle: EvidenceBundle) -> list[Violation]:
    """Every referenced hypothesis must exist in this bundle."""
    known = {h.hypothesis_id for h in bundle.hypotheses}
    violations: list[Violation] = []

    for claim in narrative.claims:
        if claim.hypothesis_id is None:
            continue
        if claim.hypothesis_id not in known:
            violations.append(make_violation(
                ViolationCode.UNKNOWN_DRIVER, CHECK_DRIVER,
                f"hypothesis '{claim.hypothesis_id}' is not in this bundle",
                claim_id=claim.claim_id,
                offending_value=claim.hypothesis_id,
                expected=", ".join(sorted(known)) or "(no hypotheses)",
            ))
    return violations


def check_metric_refs(
    narrative: Narrative, bundle: EvidenceBundle
) -> list[Violation]:
    """Every metric reference must resolve to a fact in this bundle."""
    known = {f.fact_id for f in bundle.metric_facts}
    violations: list[Violation] = []
    for claim in narrative.claims:
        for ref in claim.metric_refs:
            if ref not in known:
                violations.append(make_violation(
                    ViolationCode.INVALID_METRIC_REF, CHECK_METRIC,
                    f"metric fact '{ref}' is not in this bundle",
                    claim_id=claim.claim_id, offending_value=ref,
                ))
    return violations


def check_levers(narrative: Narrative, bundle: EvidenceBundle) -> list[Violation]:
    """Recommendations name lever ids, never free-form actions.

    The model may phrase an approved action. It may not author one, and a
    lever id absent from the bundle is exactly that: an action nobody
    approved, arriving with the authority of the system behind it.
    """
    allowed = {lever.lever_id for lever in bundle.allowed_levers}
    violations: list[Violation] = []

    for lever_id in narrative.recommendation_ids:
        if lever_id not in allowed:
            violations.append(make_violation(
                ViolationCode.UNKNOWN_LEVER, CHECK_LEVER,
                f"lever '{lever_id}' is not eligible in this bundle",
                offending_value=lever_id,
                expected=", ".join(sorted(allowed)) or "(no eligible levers)",
            ))

    for claim in narrative.claims:
        if claim.lever_id and claim.lever_id not in allowed:
            violations.append(make_violation(
                ViolationCode.UNKNOWN_LEVER, CHECK_LEVER,
                f"claim references lever '{claim.lever_id}', which is not "
                f"eligible in this bundle",
                claim_id=claim.claim_id, offending_value=claim.lever_id,
                expected=", ".join(sorted(allowed)) or "(no eligible levers)",
            ))
    return violations
