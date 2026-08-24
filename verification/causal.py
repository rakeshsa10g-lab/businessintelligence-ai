"""Check 6 — the causal-language licence (Architecture Part 6.3, Rule 5).

The mechanism behind the claim that this system does not confuse correlation
with causation. Without it, that claim is a slogan; with it, it is a regex and
a boolean that a gate reads.

A claim asserting causation — either typed `causal`, or containing a causal
verb in prose — is permitted only when its referenced hypothesis carries the
licence Stage 4 and Stage 6 granted: the counterfactual passed, temporal
precedence holds, and the hypothesis separated from its alternatives.

**Per hypothesis, never per bundle.** A licensed result for the leading
hypothesis does not license causal wording about a runner-up. That is the
mistake ADR-023 fixed one layer down, and repeating the check here means the
verifier does not simply trust that fix: a narrative citing hypothesis #2 with
"caused" is blocked on the referenced hypothesis's own licence, whatever the
bundle's top-level flag says.

**A causal verb with no hypothesis reference is also blocked.** Otherwise the
easiest way past the gate is to omit the reference, which would make the check
trivially avoidable by the one thing it is meant to stop.
"""

from __future__ import annotations

import re

from evidence.types import EvidenceBundle, HypothesisStatus
from verification.types import (
    ClaimType,
    Narrative,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK = "causal_language_licence"

# Part 6.3's vocabulary, extended with the forms that show up in practice.
CAUSAL = re.compile(
    r"\b(caused?|causing|because of|because|due to|drove|driven by|"
    r"resulted in|resulting in|led to|leading to|triggered|triggering|"
    r"responsible for|attributable to|the reason for|explains? the|"
    r"stemmed from|brought about)\b",
    re.IGNORECASE,
)

# Wording that explicitly declines to assert causation. A sentence containing
# both ("consistent with, but not established as, a cause") is hedged, and
# blocking it would push narratives towards omitting the topic rather than
# qualifying it — the opposite of what this gate wants.
ASSOCIATIVE = re.compile(
    r"\b(consistent with|associated with|coincid(?:es|ed|ing) with|"
    r"one plausible|plausible contributor|does not establish|"
    r"cannot establish|not established|correlat(?:ed|es|ion)|"
    r"may be related|appears alongside|no causal)\b",
    re.IGNORECASE,
)


def causal_phrases(text: str) -> list[str]:
    return [m.group(0) for m in CAUSAL.finditer(text)]


def is_hedged(text: str) -> bool:
    return bool(ASSOCIATIVE.search(text))


def check(narrative: Narrative, bundle: EvidenceBundle) -> list[Violation]:
    by_id = {h.hypothesis_id: h for h in bundle.hypotheses}
    violations: list[Violation] = []

    for claim in narrative.claims:
        phrases = causal_phrases(claim.text)
        asserts_cause = claim.claim_type is ClaimType.CAUSAL or bool(phrases)
        if not asserts_cause:
            continue

        # An explicitly associative sentence is not a causal assertion, even
        # when it contains the word "cause" - "the evidence does not establish
        # a cause" must be allowed to say so.
        if claim.claim_type is not ClaimType.CAUSAL and phrases and is_hedged(claim.text):
            continue

        found = ", ".join(sorted(set(phrases))) or "claim_type=causal"

        if claim.hypothesis_id is None:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) with no hypothesis reference; "
                f"there is nothing whose licence could permit it",
                claim_id=claim.claim_id, offending_value=found,
                expected="a hypothesis_id whose causal licence is granted",
            ))
            continue

        hypothesis = by_id.get(claim.hypothesis_id)
        if hypothesis is None:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) references hypothesis "
                f"'{claim.hypothesis_id}', which is not in this bundle",
                claim_id=claim.claim_id, offending_value=found,
            ))
            continue

        if not hypothesis.causal_language_allowed:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) about '{hypothesis.hypothesis_id}', "
                f"which is {hypothesis.status.value} and not licensed: "
                f"{hypothesis.causal_language_reason}",
                claim_id=claim.claim_id, offending_value=found,
                expected="associative phrasing, e.g. 'is consistent with'",
            ))
            continue

        # Licensed at the hypothesis level. The verifier still re-derives the
        # preconditions rather than trusting the flag, because the flag is set
        # one layer down and this is the layer that has to be right.
        counter = hypothesis.counterfactual
        if hypothesis.status is not HypothesisStatus.SUPPORTED:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) about a hypothesis that is "
                f"{hypothesis.status.value}, not SUPPORTED",
                claim_id=claim.claim_id, offending_value=found,
            ))
        elif not hypothesis.temporal_precedence:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) where temporal precedence was "
                f"never established: a cause cannot postdate its effect",
                claim_id=claim.claim_id, offending_value=found,
            ))
        elif counter is not None and not counter.passed:
            violations.append(make_violation(
                ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED, CHECK,
                f"causal wording ({found}) where the counterfactual did not "
                f"pass: {counter.reason}",
                claim_id=claim.claim_id, offending_value=found,
            ))
    return violations
