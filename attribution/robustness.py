"""Stage C1 — is the winning slice robust, or an artefact of the window?

Why not a Welch t-test
----------------------
The obvious move is a Welch t-test of pre- versus post-changepoint values for
each candidate slice, and Architecture Part 10.3 (C1) suggests exactly that.
Stage 3 established why it cannot carry the weight here: the event window is
*selected* by PELT to maximise displacement, so any test comparing inside the
window to outside it is a post-selection statistic. Measured on this dataset it
returns p < 0.001 on pure noise (ADR-017). A gate that fires on noise is not a
gate.

The Welch value is still computed and reported as diagnostic metadata, because
suppressing it would hide the problem rather than address it. It simply does
not decide anything.

What is used instead
--------------------
A **moving-block bootstrap over the days of the event window**, re-running the
full Adtributor ranking on each resample and asking how often the same answer
comes back.

Four candidate methods were considered:

  bootstrap stability   chosen - perturbs the window composition itself, which
                        is the exact weakness post-selection introduces
  effect-size only      no notion of stability; a single freak day passes
  permutation test      tests a null about slice labels, not about whether the
                        window boundaries drove the result
  split-window          same idea but with n = 2, far too coarse on a 15-day
                        event to distinguish weak from unstable

Blocks rather than individual days because daily KPI residuals are
autocorrelated; resampling single days would break the weekly structure and
manufacture stability that is not there. Block length defaults to one seasonal
cycle where the window allows it.

The output is a three-way verdict - STRONG, WEAK, UNSTABLE - rather than a
p-value, because "the same slice wins in 96% of resamples" is a sentence a
judge can check and a p-value here is not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from attribution.adtributor import T_EEP, T_EP, adtributor
from attribution.types import DriverStrength, RobustnessResult

DEFAULT_RESAMPLES = 400
DEFAULT_SEED = 20260822

# A winner that survives four resamples in five is reportable; one that
# survives fewer than half is a coin toss dressed as a finding.
STRONG_FREQUENCY = 0.80
WEAK_FREQUENCY = 0.50


def _block_length(n_days: int, seasonal_period: int) -> int:
    """One seasonal cycle when the window is long enough to hold three."""
    if n_days >= 3 * seasonal_period:
        return seasonal_period
    return max(2, n_days // 3)


def _resample_days(
    rng: np.random.Generator, days: list, block: int
) -> list:
    """Moving-block bootstrap: draw overlapping blocks with replacement."""
    n = len(days)
    if n <= block:
        return list(days)
    out: list = []
    max_start = n - block
    while len(out) < n:
        start = int(rng.integers(0, max_start + 1))
        out.extend(days[start : start + block])
    return out[:n]


def assess(
    forecast: pd.DataFrame,
    actual: pd.DataFrame,
    dims: list[str],
    *,
    date_column: str = "date",
    value_column: str = "value",
    seasonal_period: int = 7,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
    t_ep: float = T_EP,
    t_eep: float = T_EEP,
) -> RobustnessResult:
    """Bootstrap the Adtributor ranking over the event window's days.

    `forecast` and `actual` are per-cell frames carrying the date column, the
    dimension columns and a value column.
    """
    days = sorted(set(actual[date_column]) & set(forecast[date_column]))
    n_days = len(days)

    point = adtributor(forecast, actual, dims, value_column=value_column,
                       t_ep=t_ep, t_eep=t_eep)
    if point.winner is None or not point.winner.candidates:
        return RobustnessResult(
            n_resamples=0,
            window_days=n_days,
            seed=seed,
            strength=DriverStrength.UNSTABLE,
            reason="no dimension qualified, so there is no ranking to stabilise",
        )

    top = max(point.winner.candidates, key=lambda e: abs(e.explanatory_power))
    target_dim = point.winner.dimension
    target_element = top.element

    block = _block_length(n_days, seasonal_period)
    if n_days < 4:
        return RobustnessResult(
            n_resamples=0,
            block_length=block,
            window_days=n_days,
            seed=seed,
            top_element=target_element,
            top_dimension=target_dim,
            strength=DriverStrength.UNSTABLE,
            reason=(
                f"event window is {n_days} day(s); too short to resample "
                "meaningfully"
            ),
            caveat="window shorter than 4 days - treat the ranking as indicative",
        )

    rng = np.random.default_rng(seed)
    f_by_day = {d: g for d, g in forecast.groupby(date_column)}
    a_by_day = {d: g for d, g in actual.groupby(date_column)}

    dim_hits = 0
    element_hits = 0
    eps: list[float] = []
    n_ok = 0

    for _ in range(n_resamples):
        picked = _resample_days(rng, days, block)
        f = pd.concat([f_by_day[d] for d in picked if d in f_by_day],
                      ignore_index=True)
        a = pd.concat([a_by_day[d] for d in picked if d in a_by_day],
                      ignore_index=True)
        if f.empty or a.empty:
            continue
        try:
            r = adtributor(f, a, dims, value_column=value_column,
                           t_ep=t_ep, t_eep=t_eep)
        except (ValueError, ZeroDivisionError):
            continue
        n_ok += 1
        if r.winner is None:
            continue
        if r.winner.dimension == target_dim:
            dim_hits += 1
            match = [
                e for e in r.winner.candidates if e.element == target_element
            ]
            if match:
                element_hits += 1
                eps.append(match[0].explanatory_power)

    if n_ok == 0:
        return RobustnessResult(
            n_resamples=0,
            block_length=block,
            window_days=n_days,
            seed=seed,
            top_element=target_element,
            top_dimension=target_dim,
            strength=DriverStrength.UNSTABLE,
            reason="every resample failed to produce a ranking",
        )

    freq = element_hits / n_ok
    dim_freq = dim_hits / n_ok
    arr = np.asarray(eps) if eps else np.asarray([0.0])
    point_sign = np.sign(top.explanatory_power)
    sign_consistency = (
        float(np.mean(np.sign(arr) == point_sign)) if eps else 0.0
    )

    if freq >= STRONG_FREQUENCY and sign_consistency >= 0.95:
        strength = DriverStrength.STRONG
        reason = (
            f"{target_dim}={target_element} won {freq:.0%} of {n_ok} "
            f"block-bootstrap resamples with a consistent sign; the ranking "
            f"does not depend on which days fell inside the window"
        )
    elif freq >= WEAK_FREQUENCY:
        strength = DriverStrength.WEAK
        reason = (
            f"{target_dim}={target_element} won {freq:.0%} of {n_ok} "
            f"resamples - a majority, but the ranking is sensitive to the "
            f"window boundaries"
        )
    else:
        strength = DriverStrength.UNSTABLE
        reason = (
            f"{target_dim}={target_element} won only {freq:.0%} of {n_ok} "
            f"resamples; the ranking is an artefact of the selected window "
            f"and must not be reported as the driver"
        )

    caveat = None
    if n_days < 3 * seasonal_period:
        caveat = (
            f"window is {n_days} days against a {seasonal_period}-day season, "
            f"so blocks are {block} days and the bootstrap is coarse"
        )

    return RobustnessResult(
        n_resamples=n_ok,
        block_length=block,
        window_days=n_days,
        seed=seed,
        top_element=target_element,
        top_dimension=target_dim,
        selection_frequency=freq,
        dimension_frequency=dim_freq,
        ep_mean=float(arr.mean()),
        ep_p05=float(np.percentile(arr, 5)),
        ep_p95=float(np.percentile(arr, 95)),
        ep_sign_consistency=sign_consistency,
        strength=strength,
        reason=reason,
        caveat=caveat,
    )
