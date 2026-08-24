"""Stage 7 types — the narrative schema and Gate 2's report.

Two ideas do all the work here.

**The model writes into slots, not paragraphs.** `Narrative` is a list of typed
`Claim` objects carrying references into the frozen bundle, not prose. Prose is
assembled from validated claims. The reverse — generate fluent text, then try
to check it — is the failure mode this architecture exists to avoid, because
checking prose means parsing intent, and parsing intent is exactly the thing a
verifier cannot do reliably.

**There is no `confidence` field.** Confidence is computed deterministically
and rendered by the UI. Omitting the field from the schema means there is no
slot for a model to hallucinate a number into — a stronger guarantee than any
instruction telling it not to.

No LLM appears in this stage. These models describe what a future model will
be *allowed* to emit; nothing here calls one.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------
# the narrative schema — what a future LLM may emit
# --------------------------------------------------------------------------
class ClaimType(str, Enum):
    OBSERVATION = "observation"      # what changed
    ATTRIBUTION = "attribution"      # which driver / slice, associative
    CAUSAL = "causal"                # X caused Y — licensed, not assumed
    RECOMMENDATION = "recommendation"
    UNCERTAINTY = "uncertainty"      # what we do not know


Direction = Literal["up", "down", "flat", "n/a"]

# Claim types that must cite something. An observation or an attribution with
# no reference is an assertion, and an assertion is what this whole layer
# exists to prevent.
SUBSTANTIVE_CLAIMS = frozenset(
    {ClaimType.OBSERVATION, ClaimType.ATTRIBUTION, ClaimType.CAUSAL}
)


class Claim(BaseModel):
    """One assertion, with its references into the bundle."""

    model_config = ConfigDict(frozen=True)

    claim_id: str
    text: str
    claim_type: ClaimType
    evidence_ids: tuple[str, ...] = ()
    metric_refs: tuple[str, ...] = ()
    direction: Direction = "n/a"
    hypothesis_id: str | None = None
    lever_id: str | None = None


class Narrative(BaseModel):
    """The complete structured output. No confidence, no free-form numbers."""

    model_config = ConfigDict(frozen=True)

    headline: str
    claims: tuple[Claim, ...] = ()
    caveats: tuple[str, ...] = ()
    recommendation_ids: tuple[str, ...] = ()      # lever_ids, never text

    # set by the deterministic builder; a model-authored narrative leaves it
    # false, and the report records which mode produced the text
    generated_deterministically: bool = False

    def claim(self, claim_id: str) -> Claim | None:
        for c in self.claims:
            if c.claim_id == claim_id:
                return c
        return None

    def all_text(self) -> str:
        parts = [self.headline]
        parts.extend(c.text for c in self.claims)
        parts.extend(self.caveats)
        return "\n".join(parts)


# --------------------------------------------------------------------------
# violations
# --------------------------------------------------------------------------
class Severity(str, Enum):
    """What a violation does to delivery.

    HARD blocks. The seven hard codes below are the ones where a wrong answer
    is worse than no answer: a number that is not in the bundle, a driver that
    does not exist, a direction that inverts the finding, a causal claim the
    counterfactual never licensed, a citation to something the reader may not
    see, or a business action nobody approved. Each of those reaches a human as
    an authoritative statement that is false.

    SOFT is correctable on retry — the content is defensible but the form is
    wrong for the audience.

    INFO is logged and never blocks.
    """

    HARD = "HARD"
    SOFT = "SOFT"
    INFO = "INFO"


class ViolationCode(str, Enum):
    # --- HARD -------------------------------------------------------------
    UNGROUNDED_NUMBER = "UNGROUNDED_NUMBER"
    UNGROUNDED_DATE = "UNGROUNDED_DATE"
    UNKNOWN_DRIVER = "UNKNOWN_DRIVER"
    DIRECTION_MISMATCH = "DIRECTION_MISMATCH"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INVALID_EVIDENCE_ID = "INVALID_EVIDENCE_ID"
    RESTRICTED_EVIDENCE = "RESTRICTED_EVIDENCE"
    DOMINANT_DRIVER_OMITTED = "DOMINANT_DRIVER_OMITTED"
    CAUSAL_LANGUAGE_NOT_LICENSED = "CAUSAL_LANGUAGE_NOT_LICENSED"
    UNKNOWN_LEVER = "UNKNOWN_LEVER"
    INVALID_METRIC_REF = "INVALID_METRIC_REF"
    # --- SOFT -------------------------------------------------------------
    MISSING_CAVEAT = "MISSING_CAVEAT"
    HEDGING_INCONSISTENT = "HEDGING_INCONSISTENT"
    PERSONA_DEPTH = "PERSONA_DEPTH"
    # --- INFO -------------------------------------------------------------
    UNUSED_EVIDENCE = "UNUSED_EVIDENCE"


# The severity of each code, declared in one place so it can be read off
# rather than inferred from where a check happens to raise it.
SEVERITY: dict[ViolationCode, Severity] = {
    ViolationCode.UNGROUNDED_NUMBER: Severity.HARD,
    ViolationCode.UNGROUNDED_DATE: Severity.HARD,
    ViolationCode.UNKNOWN_DRIVER: Severity.HARD,
    ViolationCode.DIRECTION_MISMATCH: Severity.HARD,
    ViolationCode.MISSING_EVIDENCE: Severity.HARD,
    ViolationCode.INVALID_EVIDENCE_ID: Severity.HARD,
    ViolationCode.RESTRICTED_EVIDENCE: Severity.HARD,
    ViolationCode.DOMINANT_DRIVER_OMITTED: Severity.HARD,
    ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED: Severity.HARD,
    ViolationCode.UNKNOWN_LEVER: Severity.HARD,
    ViolationCode.INVALID_METRIC_REF: Severity.HARD,
    ViolationCode.MISSING_CAVEAT: Severity.SOFT,
    ViolationCode.HEDGING_INCONSISTENT: Severity.SOFT,
    ViolationCode.PERSONA_DEPTH: Severity.SOFT,
    ViolationCode.UNUSED_EVIDENCE: Severity.INFO,
}

# Why each hard rule is hard, in one line. Carried in the report so a reader
# who has never seen this file learns why their narrative was blocked.
HARD_RATIONALE: dict[ViolationCode, str] = {
    ViolationCode.UNGROUNDED_NUMBER: (
        "a figure with no matching metric fact came from nowhere the system "
        "can point at, and a wrong number stated confidently is worse than no "
        "number"
    ),
    ViolationCode.UNGROUNDED_DATE: (
        "a date outside the analysis window or the evidence it cites places "
        "the movement somewhere it did not happen"
    ),
    ViolationCode.UNKNOWN_DRIVER: (
        "naming a driver the analysis never produced invents a finding"
    ),
    ViolationCode.DIRECTION_MISMATCH: (
        "saying a metric rose when it fell inverts the entire conclusion, and "
        "the reader has no way to catch it"
    ),
    ViolationCode.MISSING_EVIDENCE: (
        "a substantive claim with no citation is an assertion, which is the "
        "thing this layer exists to prevent"
    ),
    ViolationCode.INVALID_EVIDENCE_ID: (
        "a citation that resolves to nothing is indistinguishable from a "
        "fabricated one"
    ),
    ViolationCode.RESTRICTED_EVIDENCE: (
        "citing a source the persona may not read leaks it, whether or not "
        "the text quotes its contents"
    ),
    ViolationCode.DOMINANT_DRIVER_OMITTED: (
        "narrating a weaker explanation while omitting the strongest one is "
        "misleading by selection rather than by statement"
    ),
    ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED: (
        "asserting causation the counterfactual never established is the "
        "specific error the causal gate was built for"
    ),
    ViolationCode.UNKNOWN_LEVER: (
        "an action nobody approved must never reach a human as a "
        "recommendation"
    ),
    ViolationCode.INVALID_METRIC_REF: (
        "a metric reference that resolves to nothing cannot be checked, so "
        "the number it carries cannot be trusted"
    ),
}


class Violation(BaseModel):
    """One failed check, with enough detail to fix it."""

    model_config = ConfigDict(frozen=True)

    code: ViolationCode
    severity: Severity
    check: str
    claim_id: str | None = None
    detail: str = ""
    offending_value: str | None = None
    expected: str | None = None
    rationale: str = ""

    def __str__(self) -> str:  # pragma: no cover - display only
        where = f" [{self.claim_id}]" if self.claim_id else ""
        return f"{self.severity.value} {self.code.value}{where}: {self.detail}"


def make_violation(
    code: ViolationCode,
    check: str,
    detail: str,
    *,
    claim_id: str | None = None,
    offending_value: str | None = None,
    expected: str | None = None,
) -> Violation:
    return Violation(
        code=code,
        severity=SEVERITY[code],
        check=check,
        claim_id=claim_id,
        detail=detail,
        offending_value=offending_value,
        expected=expected,
        rationale=HARD_RATIONALE.get(code, ""),
    )


# --------------------------------------------------------------------------
# the report
# --------------------------------------------------------------------------
class CheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    violation_count: int = 0
    note: str = ""


VERIFICATION_VERSION = "1.0.0"


class VerificationReport(BaseModel):
    """Deterministic. Same bundle plus same narrative gives the same report."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    bundle_hash: str
    narrative_hash: str

    passed: bool
    violations: tuple[Violation, ...] = ()

    hard_violation_count: int = 0
    soft_violation_count: int = 0
    info_violation_count: int = 0

    checks_run: tuple[CheckResult, ...] = ()
    checks_passed: int = 0
    checks_failed: int = 0

    verification_version: str = VERIFICATION_VERSION
    verified_at: datetime | None = None
    mode: str = "structured"          # structured | deterministic_template

    @property
    def hard_violations(self) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.severity is Severity.HARD)

    @property
    def soft_violations(self) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.severity is Severity.SOFT)

    def by_code(self, code: ViolationCode) -> tuple[Violation, ...]:
        return tuple(v for v in self.violations if v.code is code)

    def explain(self) -> str:
        lines = [
            f"Gate 2 [{self.verification_version}] "
            f"{'PASSED' if self.passed else 'BLOCKED'}  "
            f"bundle {self.bundle_hash[:12]}  narrative {self.narrative_hash[:12]}",
            f"  {self.checks_passed}/{len(self.checks_run)} checks passed; "
            f"{self.hard_violation_count} hard, {self.soft_violation_count} soft, "
            f"{self.info_violation_count} info",
        ]
        for v in self.violations:
            lines.append(f"  {v}")
        return "\n".join(lines)
