"""Check 7 — citation validity and entitlement leakage.

Every evidence id a narrative cites must exist **in this bundle**, not merely
somewhere in the database. That distinction is the check: a citation to a real
document from another run, another KPI or another persona's entitlement scope
is exactly as invalid as a fabricated one, and considerably more convincing.

The entitlement half is security rather than presentation. A narrative for an
ops lead may not cite a CRM note even if the note exists, even if it is
relevant, and even if the text does not quote it — the citation itself reveals
that a document of that kind exists in that window for that slice, which is a
thing the role is not entitled to learn.

In practice the bundle for a restricted persona will not contain the document
at all, because Stage 5 refuses it at the gateway and Stage 6 freezes only what
retrieval returned. This check is the belt to that braces: it fails on any
citation outside the frozen set, so a model that guesses an id it saw in a
previous run gets caught here regardless of what the bundle happens to hold.
"""

from __future__ import annotations

from evidence.types import EvidenceBundle
from retrieval.types import SourceType
from verification.types import (
    Narrative,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK = "citation_validity"


def _source_type_of(evidence_id: str, bundle: EvidenceBundle) -> SourceType | None:
    ref = bundle.evidence(evidence_id)
    return ref.source_type if ref else None


def check(narrative: Narrative, bundle: EvidenceBundle) -> list[Violation]:
    in_bundle = {
        e.evidence_id
        for e in bundle.supporting_evidence + bundle.contradicting_evidence
    }
    cohort_ids = {c.cohort_id for c in bundle.cohorts}
    denied = set(bundle.security_context.denied_sources)
    violations: list[Violation] = []

    for claim in narrative.claims:
        for evidence_id in claim.evidence_ids:
            if evidence_id in cohort_ids:
                continue          # cohorts are bundle-resident evidence too

            if evidence_id not in in_bundle:
                violations.append(make_violation(
                    ViolationCode.INVALID_EVIDENCE_ID, CHECK,
                    f"evidence '{evidence_id}' is not in this bundle; a "
                    f"citation that resolves to nothing is indistinguishable "
                    f"from a fabricated one",
                    claim_id=claim.claim_id, offending_value=evidence_id,
                ))
                continue

            source_type = _source_type_of(evidence_id, bundle)
            if source_type is None:
                continue

            # The source-name form the policy uses (crm_notes) against the
            # source-type form the evidence carries (crm_note).
            candidates = {source_type.value, f"{source_type.value}s"}
            if candidates & denied:
                violations.append(make_violation(
                    ViolationCode.RESTRICTED_EVIDENCE, CHECK,
                    f"evidence '{evidence_id}' is from source "
                    f"'{source_type.value}', which role "
                    f"'{bundle.security_context.role}' may not read",
                    claim_id=claim.claim_id, offending_value=evidence_id,
                ))
    return violations


def check_foreign_citation(
    narrative: Narrative, bundle: EvidenceBundle, known_ids: set[str]
) -> list[Violation]:
    """Citations that exist in the corpus but not in this bundle.

    Separated so a caller with corpus knowledge can distinguish "invented id"
    from "real document, wrong run" in the report. The verdict is the same —
    both are HARD — but the two failures mean different things about what went
    wrong, and a retry prompt that says which one is more useful.
    """
    in_bundle = {
        e.evidence_id
        for e in bundle.supporting_evidence + bundle.contradicting_evidence
    }
    violations: list[Violation] = []
    for claim in narrative.claims:
        for evidence_id in claim.evidence_ids:
            if evidence_id in in_bundle:
                continue
            if evidence_id in known_ids:
                violations.append(make_violation(
                    ViolationCode.INVALID_EVIDENCE_ID, CHECK,
                    f"evidence '{evidence_id}' exists in the corpus but was "
                    f"not retrieved for this run, persona and window; citing "
                    f"it asserts a link this analysis never made",
                    claim_id=claim.claim_id, offending_value=evidence_id,
                ))
    return violations
