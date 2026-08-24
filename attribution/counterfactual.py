"""Stage C2/C3 — temporal precedence and difference-in-differences.

This is the step that turns "we do not confuse correlation with causation"
from a slogan into a boolean a gate reads (Architecture Part 10.3).

What DiD is being asked here
----------------------------
Not "does this prove causality" - it does not, and nothing in this module
claims it does. It answers one narrower, checkable question:

    is the movement specific to this slice, or did comparable slices move too?

    DiD = (Y_treated,post - Y_treated,pre) - (Y_control,post - Y_control,pre)

  DiD large           the move is specific to the affected slice
                      -> causal language licensed
  DiD near zero       the control moved as well, so this is market-wide
                      -> causal language denied; the narrative must say
                         "consistent with a market-wide movement"
  no control          all comparable slices flagged, or too few
                      -> denied, with the reason recorded

Parallel trends
---------------
DiD is only meaningful if treated and control were tracking each other
*before* the event. That assumption is testable and is tested: fit a line to
the pre-period difference between the two series and check its slope is small
relative to the difference's own variability. A control that was already
diverging cannot serve as a counterfactual, and silently using one is how DiD
gets misused.

Temporal precedence
-------------------
A candidate cause dated after the changepoint cannot be the cause. Trivial to
check, embarrassing to miss, and the cheapest guard against the most common
error in this domain.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from attribution.types import CounterfactualResult

# A DiD smaller than this share of the treated slice's own pre-period level is
# treated as "the control moved too" rather than a slice-specific effect.
MIN_EFFECT_PCT = 5.0

# Pre-period slope of the treated-minus-control difference, expressed per day
# as a share of the mean difference. Above this the series were already
# diverging and the parallel-trend assumption fails.
MAX_PRE_TREND_DRIFT = 0.02

MIN_PRE_DAYS = 10
MIN_CORRELATION = 0.30


def select_control(
    treated: pd.Series,
    candidates: dict[str, pd.Series],
    pre_start: date,
    pre_end: date,
    *,
    excluded: set[str] | None = None,
    min_correlation: float = MIN_CORRELATION,
) -> tuple[str | None, float | None, list[str]]:
    """Pick the unflagged slice that tracked the treated slice most closely.

    Correlation is measured on the pre-period only. Using the full window
    would let the event itself influence the choice of control, which is the
    counterfactual equivalent of marking your own homework.
    """
    excluded = excluded or set()
    t = treated.loc[(treated.index >= pre_start) & (treated.index <= pre_end)]
    considered: list[str] = []
    best_name, best_corr = None, -np.inf

    for name, series in candidates.items():
        if name in excluded:
            continue
        c = series.loc[(series.index >= pre_start) & (series.index <= pre_end)]
        joined = pd.concat([t, c], axis=1, join="inner").dropna()
        if len(joined) < MIN_PRE_DAYS:
            continue
        if joined.iloc[:, 0].std() == 0 or joined.iloc[:, 1].std() == 0:
            continue
        corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))
        if not np.isfinite(corr):
            continue
        considered.append(name)
        if corr > best_corr:
            best_name, best_corr = name, corr

    if best_name is None or best_corr < min_correlation:
        return None, (best_corr if best_name else None), considered
    return best_name, best_corr, considered


def _parallel_trend(
    treated: pd.Series, control: pd.Series, pre_start: date, pre_end: date
) -> tuple[bool, float, str]:
    """Were the two series moving together before the event?"""
    t = treated.loc[(treated.index >= pre_start) & (treated.index <= pre_end)]
    c = control.loc[(control.index >= pre_start) & (control.index <= pre_end)]
    joined = pd.concat([t, c], axis=1, join="inner").dropna()
    if len(joined) < MIN_PRE_DAYS:
        return False, float("nan"), (
            f"only {len(joined)} overlapping pre-period days; "
            f"{MIN_PRE_DAYS} required to judge parallel trends"
        )

    diff = (joined.iloc[:, 0] - joined.iloc[:, 1]).to_numpy(dtype=float)
    x = np.arange(len(diff), dtype=float)
    slope = float(np.polyfit(x, diff, 1)[0])

    scale = float(np.mean(np.abs(diff)))
    if scale <= 0:
        scale = float(np.std(diff)) or 1.0
    drift = abs(slope) / scale

    if drift <= MAX_PRE_TREND_DRIFT:
        return True, drift, (
            f"pre-period gap drifts {drift:.3%} per day, within the "
            f"{MAX_PRE_TREND_DRIFT:.0%} tolerance - the series were tracking"
        )
    return False, drift, (
        f"pre-period gap drifts {drift:.2%} per day, above the "
        f"{MAX_PRE_TREND_DRIFT:.0%} tolerance - the slices were already "
        f"diverging, so a difference-in-differences is not interpretable"
    )


def check_temporal_precedence(
    cause_date: date | None, changepoint: date | None
) -> tuple[bool, str]:
    """A cause dated after the change cannot have produced it."""
    if changepoint is None:
        return False, "no changepoint date, so precedence cannot be established"
    if cause_date is None:
        return False, "no dated candidate cause to test against the changepoint"
    if cause_date <= changepoint:
        return True, (
            f"candidate cause dated {cause_date} precedes the changepoint "
            f"{changepoint}"
        )
    return False, (
        f"candidate cause dated {cause_date} occurs AFTER the changepoint "
        f"{changepoint}; it cannot be the cause"
    )


def difference_in_differences(
    treated: pd.Series,
    candidates: dict[str, pd.Series],
    *,
    treatment_label: str,
    treatment_slice: dict[str, list[str]],
    candidate_slices: dict[str, dict[str, list[str]]] | None = None,
    pre_start: date,
    pre_end: date,
    post_start: date,
    post_end: date,
    cause_date: date | None = None,
    changepoint: date | None = None,
    excluded: set[str] | None = None,
    min_effect_pct: float = MIN_EFFECT_PCT,
) -> CounterfactualResult:
    """Run the counterfactual check and decide whether causal wording is licensed."""
    candidate_slices = candidate_slices or {}
    precedence, precedence_reason = check_temporal_precedence(
        cause_date, changepoint
    )

    base = dict(
        treatment=treatment_label,
        treatment_slice=treatment_slice,
        pre_period=(pre_start, pre_end),
        post_period=(post_start, post_end),
        temporal_precedence=precedence,
        temporal_precedence_reason=precedence_reason,
    )

    control_name, corr, considered = select_control(
        treated, candidates, pre_start, pre_end, excluded=excluded
    )
    if control_name is None:
        return CounterfactualResult(
            **base,
            controls_considered=considered,
            passed=False,
            reason=(
                "no comparable control slice was available "
                f"({len(considered)} considered; best pre-period correlation "
                f"{corr if corr is not None else float('nan'):.2f} below the "
                f"{MIN_CORRELATION:.2f} floor). Causal language denied: with no "
                "counterfactual there is nothing to rule out a market-wide move."
            ),
        )

    control = candidates[control_name]

    def mean_between(s: pd.Series, a: date, b: date) -> float:
        w = s.loc[(s.index >= a) & (s.index <= b)]
        return float(w.mean()) if len(w) else float("nan")

    t_pre = mean_between(treated, pre_start, pre_end)
    t_post = mean_between(treated, post_start, post_end)
    c_pre = mean_between(control, pre_start, pre_end)
    c_post = mean_between(control, post_start, post_end)

    if not all(np.isfinite([t_pre, t_post, c_pre, c_post])):
        return CounterfactualResult(
            **base,
            control=control_name,
            control_slice=candidate_slices.get(control_name),
            control_correlation=corr,
            controls_considered=considered,
            passed=False,
            reason="one of the four DiD cells has no data; estimate withheld",
        )

    estimate = (t_post - t_pre) - (c_post - c_pre)
    estimate_pct = (estimate / t_pre * 100.0) if t_pre else 0.0

    parallel, drift, parallel_reason = _parallel_trend(
        treated, control, pre_start, pre_end
    )

    big_enough = abs(estimate_pct) >= min_effect_pct
    passed = bool(parallel and big_enough)

    if not parallel:
        reason = (
            f"parallel-trend check failed against control {control_name}: "
            f"{parallel_reason}. Causal language denied."
        )
    elif not big_enough:
        reason = (
            f"difference-in-differences is {estimate:+,.0f} "
            f"({estimate_pct:+.1f}% of the pre-period level), below the "
            f"{min_effect_pct:.0f}% specificity floor: control "
            f"{control_name} moved with the treated slice. This is consistent "
            f"with a market-wide movement, so causal language is denied."
        )
    else:
        reason = (
            f"difference-in-differences vs {control_name} is {estimate:+,.0f} "
            f"({estimate_pct:+.1f}% of the pre-period level); the control did "
            f"not move with it and pre-period trends were parallel "
            f"({drift:.3%}/day drift). The movement is specific to the "
            f"treated slice."
        )

    return CounterfactualResult(
        **base,
        control=control_name,
        control_slice=candidate_slices.get(control_name),
        control_correlation=corr,
        controls_considered=considered,
        treatment_pre=t_pre,
        treatment_post=t_post,
        control_pre=c_pre,
        control_post=c_post,
        estimate=estimate,
        estimate_pct=estimate_pct,
        parallel_trend_passed=parallel,
        parallel_trend_stat=drift,
        parallel_trend_reason=parallel_reason,
        passed=passed,
        reason=reason,
    )
