"""Check 3 — direction consistency.

Saying a metric rose when it fell inverts the conclusion, and a reader has no
way to catch it: the sentence is fluent, the number may even be right, and the
meaning is backwards.

Two comparisons, both mechanical:

1. `claim.direction` against the sign of the metric facts it references.
2. The direction WORDS in the claim text against `claim.direction`, so a claim
   declaring `direction="down"` while its prose says "increased" is caught even
   when the structured field is correct.

The second matters because the field is what a verifier can check and the prose
is what a human reads. If they disagree, the human is misled regardless of
which one is right.

Deliberately not a semantic judge. It matches a fixed vocabulary of rise and
fall words, and where the text uses both or neither it says nothing rather than
guessing — "conversion fell while sessions rose" is a legitimate sentence, and
a checker that forced a single direction onto it would produce false rejections
that train people to ignore the gate.
"""

from __future__ import annotations

import re

from evidence.types import EvidenceBundle
from verification.types import (
    Claim,
    Narrative,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK = "direction_consistency"

UP_WORDS = re.compile(
    r"\b(increase[sd]?|increasing|rose|rise[sn]?|grew|growth|growing|up|"
    r"higher|improve[sd]?|improving|improvement|gain|gained|gains|"
    r"climbed|climbing|recovered|recovery|surge|surged|jumped)\b",
    re.IGNORECASE,
)
DOWN_WORDS = re.compile(
    r"\b(decrease[sd]?|decreasing|fell|fall|falls|fallen|falling|"
    r"drop|dropped|drops|dropping|decline[sd]?|declining|down|lower|worse|"
    r"weakened|weakening|deteriorated|deteriorating|shortfall|loss|losses|"
    r"collapse|collapsed|contracted|contraction)\b",
    re.IGNORECASE,
)


def words_in(text: str) -> str | None:
    """The direction the prose asserts: 'up', 'down', or None if unclear."""
    up = bool(UP_WORDS.search(text))
    down = bool(DOWN_WORDS.search(text))
    if up and not down:
        return "up"
    if down and not up:
        return "down"
    return None


def fact_direction(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def check_claim(claim: Claim, bundle: EvidenceBundle) -> list[Violation]:
    violations: list[Violation] = []

    # 1. structured direction against the referenced facts
    if claim.direction in ("up", "down"):
        for ref in claim.metric_refs:
            fact = bundle.fact(ref)
            if fact is None:
                continue          # the membership check owns that failure
            raw = fact.delta if fact.delta is not None else fact.value
            computed = fact_direction(raw)
            if computed in ("up", "down") and computed != claim.direction:
                violations.append(make_violation(
                    ViolationCode.DIRECTION_MISMATCH, CHECK,
                    f"claim says '{claim.direction}' but {ref} "
                    f"({fact.label}) moved {computed} ({raw:+,.2f})",
                    claim_id=claim.claim_id,
                    offending_value=claim.direction, expected=computed,
                ))

    # 2. prose against the structured direction
    asserted = words_in(claim.text)
    if asserted and claim.direction in ("up", "down") and asserted != claim.direction:
        violations.append(make_violation(
            ViolationCode.DIRECTION_MISMATCH, CHECK,
            f"claim is typed '{claim.direction}' but its wording asserts "
            f"'{asserted}'; the field is what the verifier checks and the "
            f"wording is what the reader believes",
            claim_id=claim.claim_id,
            offending_value=asserted, expected=claim.direction,
        ))
    return violations


def check(narrative: Narrative, bundle: EvidenceBundle) -> list[Violation]:
    violations: list[Violation] = []
    for claim in narrative.claims:
        violations.extend(check_claim(claim, bundle))
    return violations
