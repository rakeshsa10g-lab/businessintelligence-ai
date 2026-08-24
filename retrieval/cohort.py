"""Cohort roll-up (Architecture Part 11.5).

Individual tickets are weak evidence. The useful statement is not

    "ticket #481 says payment failed"

but

    "34 payment-failure tickets across 29 accounts in West, 12-18 July,
     versus a trailing 8-week median of 6/week (5.7x)"

Two reasons this is a layer rather than a formatting choice:

1. **It is the signal.** A single complaint is noise; a rate change against
   the slice's own baseline is evidence.

2. **It prevents a real scoring bug.** 34 tickets about one incident would
   otherwise count as 34 distinct supporting documents, letting volume
   masquerade as diversity in any downstream evidence-strength calculation.

The underlying ids are preserved, so the roll-up summarises without hiding:
the UI can still drill down to the individual tickets.

The baseline uses a *median* of trailing weeks, not a mean. Ticket volume has
a weekday pattern and occasional spikes of its own (the S3 quality quirk in
Part 7.3); a mean would be dragged by exactly the kind of outlier week the
comparison is meant to be robust to.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta

from retrieval.types import CohortEvidence, EvidenceItem, SourceType

BASELINE_WEEKS = 8
MIN_COHORT_SIZE = 3


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def baseline_start_for(window_start: date, weeks: int) -> date:
    return window_start - timedelta(days=7 * weeks)


def aggregate(
    incident_documents: list[EvidenceItem],
    baseline_documents: list[EvidenceItem],
    *,
    window_start: date,
    window_end: date,
    cohort_dimensions: dict[str, str] | None = None,
    baseline_weeks: int = BASELINE_WEEKS,
    min_cohort_size: int = MIN_COHORT_SIZE,
    group_by_category: bool = True,
) -> list[CohortEvidence]:
    """Group incident-window documents and compare against a trailing baseline.

    `baseline_documents` are the same source and slice over the weeks *before*
    the window. They are supplied by the caller rather than re-queried here so
    that the entitlement filter that produced them is the same one that
    produced the incident set.
    """
    cohort_dimensions = cohort_dimensions or {}

    groups: dict[tuple, list[EvidenceItem]] = defaultdict(list)
    for doc in incident_documents:
        key = (
            doc.source_type,
            (doc.category or "uncategorised") if group_by_category else "all",
        )
        groups[key].append(doc)

    baseline_groups: dict[tuple, list[EvidenceItem]] = defaultdict(list)
    for doc in baseline_documents:
        key = (
            doc.source_type,
            (doc.category or "uncategorised") if group_by_category else "all",
        )
        baseline_groups[key].append(doc)

    cohorts: list[CohortEvidence] = []
    for (source_type, category), docs in sorted(
        groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))
    ):
        if len(docs) < min_cohort_size:
            continue

        base_docs = baseline_groups.get((source_type, category), [])
        per_week: dict[date, int] = defaultdict(int)
        for doc in base_docs:
            per_week[_week_start(doc.timestamp.date())] += 1

        # Every week in the baseline period counts, including the ones with no
        # matching document. A category that simply did not occur before has a
        # baseline of zero, which is the strongest possible signal - treating
        # it as "no baseline available" would discard exactly the case the
        # comparison exists to catch (35 payment tickets against a prior 0).
        all_weeks = [
            _week_start(baseline_start_for(window_start, baseline_weeks))
            + timedelta(days=7 * i)
            for i in range(baseline_weeks)
        ]
        counts = [per_week.get(w, 0) for w in all_weeks]
        weeks_observed = all_weeks
        baseline_median = float(statistics.median(counts)) if counts else 0.0
        baseline_total = sum(counts)

        window_days = (window_end - window_start).days + 1
        incident_per_week = len(docs) * 7.0 / max(1, window_days)

        ratio = (
            incident_per_week / baseline_median if baseline_median > 0 else None
        )
        novel = baseline_total == 0
        accounts = {d.account_id for d in docs if d.account_id}

        label = {
            SourceType.SUPPORT_TICKET: f"{category} tickets",
            SourceType.CRM_NOTE: f"{category} CRM notes",
            SourceType.MARKET_EVENT: f"{category} market events",
        }.get(source_type, f"{category} documents")

        cohorts.append(
            CohortEvidence(
                cohort_id=f"cohort:{source_type.value}:{category}",
                label=label,
                source_type=source_type,
                category=category,
                cohort_dimensions=dict(cohort_dimensions),
                incident_count=len(docs),
                baseline_count=baseline_median,
                baseline_weeks=len(counts),
                ratio=ratio,
                delta=incident_per_week - baseline_median,
                window_start=window_start,
                window_end=window_end,
                baseline_start=min(weeks_observed) if weeks_observed else None,
                baseline_end=max(weeks_observed) if weeks_observed else None,
                baseline_total=baseline_total,
                novel=novel,
                distinct_accounts=len(accounts),
                document_ids=sorted(d.evidence_id for d in docs),
            )
        )

    return cohorts
