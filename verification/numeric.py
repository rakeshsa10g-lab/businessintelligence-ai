"""Check 1 — the numeric allowlist (Architecture Part 6.3, Rule 3).

Every number in every claim must match a value the bundle actually contains.
Not "look plausible", not "be close to something" — match, within a stated
rounding tolerance. A figure with no matching fact came from nowhere the
system can point at.

Dates are extracted and checked FIRST, then removed from the text before
number extraction. Without that, `2026-07-12` decomposes into 2026, 07 and 12
and the checker reports three ungrounded numbers for a correctly cited date.
That is not a hypothetical: it is what a naive regex does to every narrative
that mentions when something happened.

**What counts as an allowed number.** Primarily `bundle.metric_facts`, which
is the numeric allowlist Stage 6 built for exactly this purpose. Cohort counts
are also admitted, and that is a deliberate extension rather than a loophole:
a cohort's incident count, baseline and ratio are computed deterministically in
Stage 5 and frozen into the bundle, so a narrative quoting "35 payment tickets
against none in the preceding 8 weeks" is quoting the bundle, not inventing.
The test the rule is protecting is "could the model have made this up?", and
for a value physically present in the frozen object the answer is no.
"""

from __future__ import annotations

import re
from datetime import date

from evidence.types import EvidenceBundle
from verification.types import (
    Claim,
    Violation,
    ViolationCode,
    make_violation,
)

CHECK = "numeric_allowlist"

# Ordinals and small structural integers a narrative uses to organise itself
# ("hypothesis 1", "2 of 3 checks"). Allowing 1-3 unconditionally is a
# deliberate, bounded concession: no business figure in this system is a bare
# single digit, and requiring a metric fact for the "1" in "#1" would make
# every ranked list unverifiable.
STRUCTURAL_INTEGERS = {0.0, 1.0, 2.0, 3.0}

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# 12 Jul, 12 July, Jul 12 - written dates carry no digits a fact would match
WRITTEN_DATE = re.compile(
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}\b",
    re.IGNORECASE,
)


def allowed_numbers(bundle: EvidenceBundle) -> set[float]:
    """Every numeric value the bundle contains."""
    allowed: set[float] = set(STRUCTURAL_INTEGERS)

    for fact in bundle.metric_facts:
        for value in (
            fact.value, fact.baseline, fact.observed, fact.delta, fact.delta_pct
        ):
            if value is None:
                continue
            allowed.add(float(value))
            # magnitude too: a narrative usually states the direction in words
            # ("declined 27.2%") while the fact carries the sign (-27.22)
            allowed.add(abs(float(value)))

    for cohort in bundle.cohorts:
        allowed.add(float(cohort.incident_count))
        allowed.add(float(cohort.baseline_count))
        allowed.add(float(cohort.distinct_accounts))
        allowed.add(float(cohort.baseline_weeks))
        if cohort.ratio is not None:
            allowed.add(float(cohort.ratio))
    return allowed


def allowed_dates(bundle: EvidenceBundle) -> set[date]:
    """Dates the bundle can vouch for: the window, fact periods, evidence."""
    dates: set[date] = {bundle.window_start, bundle.window_end}
    for fact in bundle.metric_facts:
        if fact.period_start:
            dates.add(fact.period_start)
        if fact.period_end:
            dates.add(fact.period_end)
    for ev in bundle.supporting_evidence + bundle.contradicting_evidence:
        dates.add(ev.timestamp.date())
    for cohort in bundle.cohorts:
        for d in (cohort.window_start, cohort.window_end):
            if d:
                dates.add(d)
    if bundle.detection is not None:
        for d in (
            bundle.detection.changepoint_date,
            bundle.detection.observed_start,
            bundle.detection.observed_end,
            bundle.detection.baseline_start,
            bundle.detection.baseline_end,
        ):
            if d:
                dates.add(d)
    return dates


def tolerance_for(value: float) -> float:
    """The rounding budget for one allowed value.

    `max(0.05, |value| * 0.005)` — half a percent, with an absolute floor so
    small values are not held to an impossible standard. A narrative rounding
    -888,745.03 to "888,745" or -27.22% to "27.2%" is being readable, not
    inaccurate.
    """
    return max(0.05, abs(value) * 0.005)


def matches_any(number: float, allowed: set[float]) -> bool:
    return any(abs(number - a) <= tolerance_for(a) for a in allowed)


def strip_dates(text: str) -> str:
    """Remove dates so their digits are not read as quantities."""
    return WRITTEN_DATE.sub(" ", ISO_DATE.sub(" ", text))


def check_claim(
    claim: Claim, bundle: EvidenceBundle, allowed: set[float] | None = None,
    dates: set[date] | None = None,
) -> list[Violation]:
    allowed = allowed if allowed is not None else allowed_numbers(bundle)
    dates = dates if dates is not None else allowed_dates(bundle)
    violations: list[Violation] = []

    for match in ISO_DATE.finditer(claim.text):
        try:
            found = date(int(match.group(1)), int(match.group(2)),
                         int(match.group(3)))
        except ValueError:
            violations.append(make_violation(
                ViolationCode.UNGROUNDED_DATE, CHECK,
                f"'{match.group(0)}' is not a valid date",
                claim_id=claim.claim_id, offending_value=match.group(0),
            ))
            continue
        if found not in dates:
            violations.append(make_violation(
                ViolationCode.UNGROUNDED_DATE, CHECK,
                f"date {found} appears in no metric fact, evidence item or "
                f"analysis window in this bundle",
                claim_id=claim.claim_id, offending_value=str(found),
            ))

    for token in NUMBER.findall(strip_dates(claim.text).replace(",", "")):
        number = float(token)
        if not matches_any(number, allowed):
            violations.append(make_violation(
                ViolationCode.UNGROUNDED_NUMBER, CHECK,
                f"{number:g} matches no value in the bundle within tolerance",
                claim_id=claim.claim_id, offending_value=token,
                expected="a value from bundle.metric_facts or bundle.cohorts",
            ))
    return violations


def check(narrative, bundle: EvidenceBundle) -> list[Violation]:
    allowed = allowed_numbers(bundle)
    dates = allowed_dates(bundle)
    violations: list[Violation] = []
    for claim in narrative.claims:
        violations.extend(check_claim(claim, bundle, allowed, dates))
    # the headline is narrative text too, and it is the part a reader
    # remembers, so it is checked with the same rule
    headline = Claim(
        claim_id="headline", text=narrative.headline,
        claim_type=narrative.claims[0].claim_type if narrative.claims
        else __import__("verification.types", fromlist=["ClaimType"]).ClaimType.OBSERVATION,
    )
    violations.extend(check_claim(headline, bundle, allowed, dates))
    return violations
