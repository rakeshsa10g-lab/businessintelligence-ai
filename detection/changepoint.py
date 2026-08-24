"""Steps 3 and 4 — robust point anomalies, then regime shifts.

Two different questions, deliberately separated:

  robust z   "was this day unusual?"      -> SPIKE
  PELT       "did the level move and stay moved?" -> LEVEL_SHIFT

Those demand completely different actions, which is why the pipeline answers
both rather than collapsing them (Part 9.3).

MAD rather than standard deviation: a single extreme day inflates sigma and
masks the next real event. The 1.4826 constant makes MAD a consistent
estimator of sigma for normally distributed data.

Architecture reference: Part 9.2 steps 3 and 4.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import ruptures as rpt

from detection.types import ChangepointResult, RobustScoreResult, ShiftType

MAD_TO_SIGMA = 1.4826


def _robust_sigma(x: np.ndarray) -> float:
    """MAD-based sigma, with a std fallback for a degenerate MAD."""
    med = float(np.median(x))
    mad = float(np.median(np.abs(x - med)))
    sigma = mad * MAD_TO_SIGMA
    if sigma <= 0:
        sigma = float(np.std(x))
    return sigma if sigma > 0 else 1.0


# --------------------------------------------------------------------------
# step 3 — robust point anomaly
# --------------------------------------------------------------------------
def robust_z_scores(
    residual: list[float] | np.ndarray,
    z_threshold: float,
) -> RobustScoreResult:
    """MAD-based robust z-score on the STL residual.

    robust_z = (residual - median(residual)) / (1.4826 * MAD(residual))
    """
    r = np.asarray(residual, dtype=float)
    if r.size == 0:
        raise ValueError("cannot score an empty residual series")

    median = float(np.median(r))
    mad = float(np.median(np.abs(r - median)))
    scale = MAD_TO_SIGMA * mad

    # A degenerate scale means the residual is (near) constant. Falling back to
    # std would silently reintroduce the outlier sensitivity MAD exists to
    # avoid, so instead report zero anomalies and flag the condition.
    degenerate = scale <= 0 or not np.isfinite(scale)
    if degenerate:
        z = np.zeros_like(r)
    else:
        z = (r - median) / scale

    flags = np.abs(z) >= z_threshold

    return RobustScoreResult(
        residual_median=round(median, 6),
        mad=round(mad, 6),
        robust_scale=round(scale, 6),
        z_threshold=z_threshold,
        z_scores=[round(float(v), 4) for v in z],
        anomaly_flags=[bool(f) for f in flags],
        n_anomalies=int(flags.sum()),
        max_abs_z=round(float(np.max(np.abs(z))) if z.size else 0.0, 4),
        degenerate_scale=bool(degenerate),
    )


# --------------------------------------------------------------------------
# step 4 — regime shift
# --------------------------------------------------------------------------
def detect_changepoints(
    residual: list[float] | np.ndarray,
    dates: list[date],
    *,
    penalty: float,
    cost_model: str = "l2",
    min_size: int = 3,
    jump: int = 1,
    restrict_to: tuple[date, date] | None = None,
) -> ChangepointResult:
    """PELT on the residual series.

    The penalty is passed in from the KPI contract, never hard-coded here:
    it is the tunable signal-versus-noise control and different KPIs need
    different values (Part 9.1).
    """
    r = np.asarray(residual, dtype=float).reshape(-1, 1)
    n = len(r)

    result = ChangepointResult(
        cost_model=cost_model,
        penalty=penalty,
        min_size=min_size,
        jump=jump,
    )
    if n < 2 * min_size:
        result.selection_rule = "series too short for PELT"
        return result

    # Scale the penalty to the data's own noise level.
    #
    # With the l2 cost, ruptures' segment cost is a sum of squared deviations,
    # so a bare constant is not comparable across KPIs — rupees, percentages
    # and counts differ by orders of magnitude, and a penalty tuned for one
    # silently over-segments the others. The standard remedy (Killick,
    # Fearnhead & Eckley 2012) is a BIC-form penalty, beta * sigma^2 * log(n),
    # which makes `penalty` a dimensionless multiplier: beta = 1 is BIC, and
    # larger values demand correspondingly stronger evidence per changepoint.
    #
    # sigma is estimated with the MAD rather than the standard deviation so
    # that the event we are looking for does not inflate the very threshold
    # meant to detect it.
    sigma = _robust_sigma(r.ravel())
    effective_penalty = float(penalty) * (sigma ** 2) * float(np.log(n))
    result.effective_penalty = effective_penalty
    result.residual_sigma = float(sigma)

    algo = rpt.Pelt(model=cost_model, min_size=min_size, jump=jump).fit(r)
    # ruptures returns breakpoints including the series length as the last
    # element; that sentinel is not a changepoint.
    raw = [int(b) for b in algo.predict(pen=effective_penalty) if 0 < b < n]

    idx_dates = [dates[i] for i in raw]
    if restrict_to is not None:
        lo, hi = restrict_to
        keep = [(i, d) for i, d in zip(raw, idx_dates) if lo <= d <= hi]
        raw = [i for i, _ in keep]
        idx_dates = [d for _, d in keep]

    result.changepoint_indices = raw
    result.changepoint_dates = idx_dates
    result.n_changepoints = len(raw)

    if not raw:
        result.shift_type = ShiftType.NONE
        result.selection_rule = "no changepoint exceeded the penalty"
        return result

    # Select the regime whose cumulative displacement from the counterfactual
    # is largest.
    #
    # An earlier version scored each changepoint by the mean shift across a
    # symmetric +/-28 day window. That is wrong for short events: when an
    # incident lasts under four weeks, both its onset and its recovery sit
    # inside the same window, so the rule could rank the recovery edge above
    # the onset and report the date the problem ended as the date it began.
    #
    # Scoring segments instead removes that confound. The score is the
    # standard signal-to-noise statistic for a level shift,
    #
    #     |mean(segment)| * sqrt(len(segment)) / sigma
    #
    # which is the Gaussian likelihood-ratio statistic for a change in mean.
    # Scoring by the raw sum instead would be pure length bias: a month of
    # barely-displaced days outweighs a genuine eleven-day collapse, and the
    # detector reports the quiet stretch. The sqrt(n) weighting is what makes
    # a large short displacement and a small long one commensurable, and it
    # also pins the onset date, because padding a segment with quiet days
    # ahead of the event lowers the mean faster than it raises sqrt(n).
    #
    # PELT optimises segmentation, not event boundaries, so a gradual dip
    # arrives as several adjacent segments displaced the same way. They are
    # merged while the displacement holds direction with at least half the
    # initial magnitude — the "sustained displacement" idea the materiality
    # gate encodes as min_duration_days, applied to where the regime ends.
    flat = r.ravel()
    bounds = raw + [n]

    def _merged_end(start_i: int) -> int:
        later = [b for b in bounds if b > start_i]
        if not later:
            return n
        first_end = later[0]
        first_mean = float(np.mean(flat[start_i:first_end]))
        direction = np.sign(first_mean)
        end_i = first_end
        if direction != 0:
            for nxt in later[1:]:
                seg_mean = float(np.mean(flat[end_i:nxt]))
                if (
                    np.sign(seg_mean) == direction
                    and abs(seg_mean) >= 0.5 * abs(first_mean)
                ):
                    end_i = nxt
                else:
                    break
        return end_i

    best_i, best_end, best_score = None, None, -np.inf
    for i in raw:
        seg_end = _merged_end(i)
        if seg_end - i < min_size:
            continue
        seg = flat[i:seg_end]
        score = abs(float(np.mean(seg))) * np.sqrt(len(seg)) / sigma
        if score > best_score:
            best_i, best_end, best_score = i, seg_end, score

    if best_i is None:
        best_i = raw[0]
        best_end = _merged_end(best_i)
        result.selection_rule = "first changepoint (no segment had enough support)"
    else:
        result.selection_rule = (
            "regime with the largest absolute cumulative deviation from the "
            "trend+seasonal counterfactual, extended across adjacent "
            "same-direction segments"
        )

    result.selected_index = best_i
    result.selected_date = dates[best_i]
    result.segment_end_index = best_end
    result.segment_end_date = dates[min(best_end, n) - 1]
    result.segments_merged = len([b for b in bounds if best_i < b <= best_end])
    return result


def classify_shift(
    residual: list[float] | np.ndarray,
    changepoint: ChangepointResult,
    robust: RobustScoreResult,
    *,
    sustain_days: int = 5,
) -> ShiftType:
    """SPIKE, LEVEL_SHIFT or DRIFT.

    A changepoint alone is not a level shift: the move has to persist. A
    single bad day that PELT happens to bracket is a spike, and the two call
    for different actions.
    """
    r = np.asarray(residual, dtype=float)

    if changepoint.selected_index is not None:
        i = changepoint.selected_index
        pre = r[max(0, i - 28) : i]
        post = r[i : min(len(r), i + 28)]
        if len(pre) >= 3 and len(post) >= sustain_days:
            # Medians, not means. One catastrophic day inside a 28-day window
            # moves the mean by a twenty-eighth of its size, which is enough to
            # clear the scale and have a spike misreported as a sustained
            # regime change. The median only moves if most of the window moved,
            # which is exactly the question being asked.
            shift = abs(float(np.median(post) - np.median(pre)))
            scale = robust.robust_scale or 1.0
            if shift >= scale and len(post) >= sustain_days:
                return ShiftType.LEVEL_SHIFT

    if robust.n_anomalies > 0:
        return ShiftType.SPIKE

    # No point anomaly and no sustained break: check for a slow trend move.
    if len(r) >= 14:
        x = np.arange(len(r), dtype=float)
        slope = float(np.polyfit(x, r, 1)[0])
        scale = robust.robust_scale or 1.0
        if abs(slope) * len(r) >= 2 * scale:
            return ShiftType.DRIFT

    return ShiftType.NONE
