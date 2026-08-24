"""Checks 4 and 5 — evidence coverage and dominant-driver coverage.

**Evidence coverage.** A substantive claim with no citation is an assertion.
"Payment failures increased during the incident" is either backed by evidence
in the bundle or it is the model's opinion, and the reader cannot tell which
from the sentence alone.

**Dominant-driver coverage.** The narrative must mention the strongest
supported hypothesis. This is the check against misleading by *selection*
rather than by statement: every individual sentence can be true while the
narrative as a whole points at the wrong thing, simply by discussing the
third-ranked explanation and never mentioning the first. Nothing in the other
checks catches that, because nothing false was said.

The rule only bites when the bundle actually has a dominant driver. If the top
two hypotheses are CONFLICTED, there is no single thing to require, and
demanding one would push the narrative towards a certainty the analysis
refused to claim.
"""

from __future__ import annotations

from evidence.types import EvidenceBundle, HypothesisStatus
from verification.types import (
    SUBSTANTIVE_CLAIMS,
    Narrative,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK_EVIDENCE = "evidence_coverage"
CHECK_DOMINANT = "dominant_driver_coverage"


def check_evidence_coverage(
    narrative: Narrative, bundle: EvidenceBundle
) -> list[Violation]:
    """Every substantive claim cites at least one evidence item or fact."""
    violations: list[Violation] = []

    for claim in narrative.claims:
        if claim.claim_type not in SUBSTANTIVE_CLAIMS:
            continue
        if claim.evidence_ids or claim.metric_refs:
            continue
        violations.append(make_violation(
            ViolationCode.MISSING_EVIDENCE, CHECK_EVIDENCE,
            f"{claim.claim_type.value} claim cites neither evidence nor a "
            f"metric fact",
            claim_id=claim.claim_id,
            expected="at least one evidence_id or metric_ref",
        ))
    return violations


def dominant_hypothesis(bundle: EvidenceBundle):
    """The hypothesis the narrative may not omit, or None.

    Only a SUPPORTED top hypothesis qualifies. Under CONFLICTED the analysis
    declined to separate two explanations, so requiring one of them to be
    named would be asking the narrative to assert what the analysis would not.
    """
    if not bundle.hypotheses:
        return None
    top = bundle.hypotheses[0]
    if top.status is not HypothesisStatus.SUPPORTED:
        return None
    return top


def check_dominant_driver(
    narrative: Narrative, bundle: EvidenceBundle
) -> list[Violation]:
    dominant = dominant_hypothesis(bundle)
    if dominant is None:
        return []

    referenced = {c.hypothesis_id for c in narrative.claims if c.hypothesis_id}
    if dominant.hypothesis_id in referenced:
        return []

    # A narrative may also name it in prose without the structured field; that
    # is weaker but not a fabrication, so the text is checked as a fallback
    # before failing.
    haystack = narrative.all_text().lower()
    if dominant.cause_bucket.replace("_", " ") in haystack:
        return []
    if dominant.driver_id.replace("_", " ").lower() in haystack:
        return []

    return [make_violation(
        ViolationCode.DOMINANT_DRIVER_OMITTED, CHECK_DOMINANT,
        f"the strongest supported hypothesis "
        f"('{dominant.hypothesis_id}', score {dominant.score:.3f}) is not "
        f"mentioned in any claim; narrating a weaker explanation while "
        f"omitting the strongest is misleading by selection",
        offending_value=", ".join(sorted(referenced)) or "(none referenced)",
        expected=dominant.hypothesis_id,
    )]


def check_unused_evidence(
    narrative: Narrative, bundle: EvidenceBundle
) -> list[Violation]:
    """INFO only: evidence the bundle carried but the narrative never used.

    Not a failure — a narrative is a summary, and a summary that cited
    everything would be a list. Logged because a large unused fraction is a
    useful signal about retrieval precision.
    """
    cited = {e for c in narrative.claims for e in c.evidence_ids}
    available = {
        e.evidence_id
        for e in bundle.supporting_evidence + bundle.contradicting_evidence
    }
    unused = available - cited
    if not unused:
        return []
    return [make_violation(
        ViolationCode.UNUSED_EVIDENCE, CHECK_EVIDENCE,
        f"{len(unused)} of {len(available)} evidence items were not cited",
        offending_value=str(len(unused)),
    )]
