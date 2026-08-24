"""Step 0 — the coverage gate.

Runs before any statistical method. Nothing downstream is valid without it:
STL on 20 points produces confident garbage, which is exactly the
"confidently wrong" failure this whole architecture exists to prevent
(Part 9.3).

Four distinct ways coverage can fail, each with its own status so the
abstention path downstream can say which one happened:

  SPARSE_HISTORY             too few days of history for seasonal detection
  INSUFFICIENT_OBSERVATIONS  enough calendar span, too few actual points
  EXCESSIVE_MISSINGNESS      more than max_missing_rate of the window absent
  UNSUITABLE_SEASONAL_PERIOD fewer than two full seasonal cycles

Architecture reference: Part 9.2 step 0, Part 9.4.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from detection.types import CoverageResult, CoverageStatus
from semantic.contract import KPIContract

# More than this fraction of the window missing and the window is not
# trustworthy even if the raw count clears min_history_days (Part 9.2 step 1).
MAX_MISSING_RATE = 0.10

# STL needs at least two full cycles to separate seasonality from trend.
MIN_SEASONAL_CYCLES = 2.0


def assess(
    series: pd.Series,
    contract: KPIContract,
    *,
    max_missing_rate: float = MAX_MISSING_RATE,
    min_seasonal_cycles: float = MIN_SEASONAL_CYCLES,
) -> CoverageResult:
    """Decide whether `series` can support the contract's detection method.

    `series` is indexed by date and may contain gaps; this function does not
    modify it.
    """
    period = contract.detection.seasonality_period
    required = contract.detection.min_history_days

    n_obs = int(series.notna().sum())

    if len(series) == 0:
        return CoverageResult(
            status=CoverageStatus.INSUFFICIENT_OBSERVATIONS,
            observations_available=0,
            observations_required=required,
            span_days=0,
            missing_days=0,
            missing_rate=1.0,
            seasonal_period=period,
            periods_covered=0.0,
            reason="no observations returned for this slice and window",
            recommended_action=(
                "Check the slice filter and the entitlement predicate before "
                "treating this as a data problem."
            ),
        )

    first: date = series.index.min()
    last: date = series.index.max()
    span = (last - first).days + 1
    expected_days = span
    missing = expected_days - n_obs
    missing_rate = missing / expected_days if expected_days else 1.0
    periods_covered = n_obs / period if period else 0.0

    # 1. sparse history — the designed path, not an error (Scenario 4)
    if n_obs < required:
        return CoverageResult(
            status=CoverageStatus.SPARSE_HISTORY,
            observations_available=n_obs,
            observations_required=required,
            span_days=span,
            missing_days=missing,
            missing_rate=round(missing_rate, 4),
            seasonal_period=period,
            periods_covered=round(periods_covered, 2),
            reason=(
                f"{n_obs} days of history; {required} required for seasonal "
                f"detection at period {period}."
            ),
            recommended_action=(
                "Route to the peer-cohort baseline path. Report a range, cap "
                "confidence at LOW, and suppress levers that require a stable "
                "baseline."
            ),
        )

    # 2. not enough seasonal cycles to identify a seasonal component
    if periods_covered < min_seasonal_cycles:
        return CoverageResult(
            status=CoverageStatus.UNSUITABLE_SEASONAL_PERIOD,
            observations_available=n_obs,
            observations_required=int(period * min_seasonal_cycles),
            span_days=span,
            missing_days=missing,
            missing_rate=round(missing_rate, 4),
            seasonal_period=period,
            periods_covered=round(periods_covered, 2),
            reason=(
                f"{periods_covered:.1f} seasonal cycles at period {period}; "
                f"STL needs at least {min_seasonal_cycles:.0f} to separate "
                "seasonality from trend."
            ),
            recommended_action=(
                "Either widen the analysis window or declare a shorter "
                "seasonality_period on the contract."
            ),
        )

    # 3. too much of the window absent
    if missing_rate > max_missing_rate:
        return CoverageResult(
            status=CoverageStatus.EXCESSIVE_MISSINGNESS,
            observations_available=n_obs,
            observations_required=required,
            span_days=span,
            missing_days=missing,
            missing_rate=round(missing_rate, 4),
            seasonal_period=period,
            periods_covered=round(periods_covered, 2),
            reason=(
                f"{missing} of {expected_days} days missing "
                f"({missing_rate:.1%}); threshold is {max_missing_rate:.0%}."
            ),
            recommended_action=(
                "Do not impute at this rate. Report the gap to the source "
                "owner and abstain for this window."
            ),
        )

    return CoverageResult(
        status=CoverageStatus.OK,
        observations_available=n_obs,
        observations_required=required,
        span_days=span,
        missing_days=missing,
        missing_rate=round(missing_rate, 4),
        seasonal_period=period,
        periods_covered=round(periods_covered, 2),
        reason=(
            f"{n_obs} observations over {span} days "
            f"({periods_covered:.1f} seasonal cycles), {missing_rate:.1%} missing."
        ),
        recommended_action="",
    )
