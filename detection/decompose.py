"""Step 2 — STL decomposition.

Weekly seasonality dominates daily retail revenue. Without removing it first,
every Monday is an anomaly and alert fatigue arrives immediately (Part 9.3).

The seasonal period comes from the KPI contract, never from a constant here:
net_revenue and orders are daily with weekly seasonality (period 7),
refund_rate is weekly with a 4-week cycle. Applying one STL configuration to
every KPI is exactly the mistake this parameterisation prevents.

Architecture reference: Part 9.2 step 2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from detection.types import DecompositionResult
from semantic.contract import KPIContract


def _strength(component: np.ndarray, residual: np.ndarray) -> float:
    """Seasonal / trend strength as defined in Hyndman's FPP.

    max(0, 1 - Var(residual) / Var(component + residual)). Bounded to [0, 1];
    0 means the component carries no information beyond the noise.
    """
    combined = component + residual
    var_combined = float(np.var(combined))
    if var_combined <= 0:
        return 0.0
    return float(max(0.0, min(1.0, 1.0 - np.var(residual) / var_combined)))


def decompose(
    series: pd.Series,
    contract: KPIContract,
    *,
    robust: bool = True,
    seasonal_smoother: int | None = None,
    trend_smoother: int | None = None,
) -> DecompositionResult:
    """Split `series` into trend, seasonal and residual.

    `series` must be gap-free and date-indexed — the engine's preprocess step
    guarantees that, and the coverage gate guarantees it is long enough.
    """
    period = contract.detection.seasonality_period
    if period < 2:
        raise ValueError(
            f"{contract.id}: seasonality_period must be >= 2, got {period}"
        )
    if len(series) < 2 * period:
        raise ValueError(
            f"{contract.id}: STL needs at least two full cycles "
            f"({2 * period} points), got {len(series)}. The coverage gate "
            "should have caught this."
        )

    # The seasonal smoother spans this many cycles of each seasonal sub-series,
    # so it governs how fast the weekly shape is allowed to change. statsmodels'
    # minimum of 7 is loose enough that the seasonal component re-forms around a
    # two-week incident and quietly swallows it: on a clean synthetic series a
    # planted -25% event measures +2.3% at seasonal=7 and exactly -25.0% at 13
    # or more. A retail weekly rhythm is stable, not something that reinvents
    # itself fortnightly, so smooth it over at least two cycles.
    if seasonal_smoother is None:
        seasonal_smoother = max(7, 2 * period + 1)
        if seasonal_smoother % 2 == 0:            # statsmodels requires odd
            seasonal_smoother += 1

    # The trend smoother has to be long enough that the trend cannot follow the
    # very event we are trying to measure. statsmodels defaults to roughly
    # 1.5 * period / (1 - 1.5 / seasonal) — about 23 days at period 7 — which
    # bends to track a two-week incident and absorbs most of it: a true 25%
    # revenue collapse is measured at 6.8% once the trend has moved with it,
    # because the counterfactual baseline quietly follows the event down.
    #
    # Eight cycles is the smallest span that comfortably exceeds any event the
    # materiality gate would call sustained, and it is bounded below by the
    # contract's own min_history_days. The result is a plateau, not a knife
    # edge: 57, 91 and 127 all recover the same effect to within 1.5pp, so the
    # choice is insensitive by construction.
    if trend_smoother is None:
        trend_smoother = max(8 * period + 1, contract.detection.min_history_days + 1)
    if trend_smoother % 2 == 0:              # statsmodels requires odd
        trend_smoother += 1
    if trend_smoother >= len(series):        # fall back rather than fail
        trend_smoother = None

    values = series.to_numpy(dtype=float)
    stl = STL(
        values,
        period=period,
        seasonal=seasonal_smoother,
        trend=trend_smoother,
        robust=robust,  # robust=True downweights outliers, so one bad day
    )                   # does not distort the seasonal shape it estimates
    fitted = stl.fit()

    trend = np.asarray(fitted.trend, dtype=float)
    seasonal = np.asarray(fitted.seasonal, dtype=float)
    residual = np.asarray(fitted.resid, dtype=float)

    return DecompositionResult(
        method="STL",
        seasonal_period=period,
        robust=robust,
        dates=list(series.index),
        observed=values.tolist(),
        trend=trend.tolist(),
        seasonal=seasonal.tolist(),
        residual=residual.tolist(),
        seasonal_strength=round(_strength(seasonal, residual), 4),
        trend_smoother=trend_smoother,
        trend_strength=round(_strength(trend, residual), 4),
    )


def baseline_from(decomposition: DecompositionResult) -> np.ndarray:
    """The counterfactual 'no event' level: trend + seasonal.

    Used to quantify effect size — actual minus this is what the event cost.
    """
    return np.asarray(decomposition.trend) + np.asarray(decomposition.seasonal)
