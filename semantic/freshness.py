"""Source freshness.

The S3 finance source is stamped T+3 by design, so the most recent week
genuinely does not exist yet. Reporting that honestly is a Round 2 requirement
(R2-CX-2, R2-MPE-8) — a zero would be a lie and a silent gap would be worse.
"""

from __future__ import annotations

from datetime import datetime

from data import spec
from semantic.contract import KPIContract
from semantic.types import FreshnessStatus

# This module is deliberately pure: it performs no database access at all.
# The gateway reads the source watermark and passes it in, which keeps the
# number of modules that can execute SQL down to the gateway plus the audit
# writer (ADR-011).


def assess(
    contract: KPIContract, as_of: datetime, now: datetime | None = None
) -> FreshnessStatus:
    now = now or spec.DEMO_NOW
    lag_hours = (now - as_of).total_seconds() / 3600.0
    rule = contract.freshness
    is_stale = lag_hours > rule.stale_after_hours

    if is_stale:
        note = (
            f"Source {contract.lineage.source_id} is stale: {lag_hours:.1f}h "
            f"since watermark, threshold {rule.stale_after_hours:.0f}h."
        )
    elif lag_hours > rule.expected_lag_hours:
        note = (
            f"Source {contract.lineage.source_id} is behind its expected "
            f"{rule.expected_lag_hours:.0f}h lag but within tolerance."
        )
    else:
        note = f"Source {contract.lineage.source_id} is within its expected lag."

    return FreshnessStatus(
        cadence=rule.cadence,
        as_of=as_of,
        lag_hours=round(lag_hours, 2),
        expected_lag_hours=rule.expected_lag_hours,
        stale_after_hours=rule.stale_after_hours,
        is_stale=is_stale,
        note=note,
    )
