"""Steps 5 and 6 — quantify the effect, then apply the business gate.

The single most important idea in this layer: a statistically real change is
not automatically a business problem. Fraud ops learned the expensive version
of this lesson — industry false-positive rates of 90-95% and 70% of analyst
time spent on alerts that were fine (Round 1 evidence D6).

So `statistical_signal` and `business_materiality` are computed separately,
reported separately, and only then combined:

    is_material = statistical_signal AND business_materiality

Collapsing them into one score would make "why did you alert me?"
unanswerable, which is the failure the semantic layer exists to prevent.

Architecture reference: Part 9.2 steps 5 and 6.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from detection.types import MaterialityResult, StatisticalSignal
from semantic.contract import KPIContract


def quantify(
    observed: np.ndarray,
    baseline: np.ndarray,
    start_index: int,
    end_index: int | None = None,
) -> tuple[float, float, int]:
    """Effect of the event relative to the counterfactual 'no event' path.

    abs_effect = sum(actual - baseline) over the event window
    rel_effect = abs_effect / sum(baseline)

    `end_index` bounds the window to the regime segment PELT identified. It
    matters more than it looks: measuring to the end of the series instead
    averages a short incident over every subsequent recovered day, so the same
    event appears less material the longer ago it happened.
    """
    stop = len(observed) if end_index is None else int(end_index)
    actual_post = observed[start_index:stop]
    baseline_post = baseline[start_index:stop]
    if actual_post.size == 0:
        return 0.0, 0.0, 0

    abs_effect = float(np.sum(actual_post - baseline_post))
    denom = float(np.sum(baseline_post))
    rel_effect_pct = (abs_effect / denom * 100.0) if denom else 0.0
    return abs_effect, rel_effect_pct, int(actual_post.size)


def welch_test(
    residual: np.ndarray,
    start_index: int,
    end_index: int | None = None,
    baseline_days: int = 28,
) -> tuple[float | None, float | None]:
    """Welch t-test of pre-window residuals against post-window residuals.

    Welch rather than Student because the two windows routinely have different
    variance — an event usually changes dispersion as well as level.

    Both windows are bounded: the post window to the regime segment, the pre
    window to `baseline_days` immediately before it. Comparing against the
    whole of history instead would dilute the contrast with months of
    unrelated regimes.

    Returns (p_value, Cohen's d).
    """
    stop = len(residual) if end_index is None else int(end_index)
    pre = residual[max(0, start_index - baseline_days) : start_index]
    post = residual[start_index:stop]
    if len(pre) < 3 or len(post) < 3:
        return None, None

    result = stats.ttest_ind(post, pre, equal_var=False)
    p_value = float(result.pvalue)

    n1, n2 = len(post), len(pre)
    s1, s2 = float(np.var(post, ddof=1)), float(np.var(pre, ddof=1))
    pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / max(1, n1 + n2 - 2))
    d = float((np.mean(post) - np.mean(pre)) / pooled) if pooled > 0 else 0.0
    return p_value, d


def assess_statistical_signal(
    *,
    max_abs_z: float,
    z_threshold: float,
    changepoint_found: bool,
    p_value: float | None,
    effect_size: float | None,
    p_threshold: float = 0.05,
) -> StatisticalSignal:
    """Is the movement statistically real?

    Requires a point anomaly OR a changepoint, and — when there is enough data
    to run it — a significant Welch test. The disjunction on the first pair is
    deliberate: a sustained level shift may contain no single day extreme
    enough to trip the z threshold, and a sharp one-day spike may be too short
    for PELT.
    """
    z_passed = max_abs_z >= z_threshold
    p_passed = None if p_value is None else bool(p_value < p_threshold)

    structural = z_passed or changepoint_found
    significant = structural and (p_passed is not False)

    if not structural:
        reason = (
            f"no point anomaly (max |z| {max_abs_z:.2f} < {z_threshold}) "
            "and no changepoint"
        )
    elif p_passed is False:
        reason = (
            f"structure present but the pre/post difference is not significant "
            f"(Welch p={p_value:.3f} >= {p_threshold})"
        )
    else:
        parts = []
        if z_passed:
            parts.append(f"max |z| {max_abs_z:.2f} >= {z_threshold}")
        if changepoint_found:
            parts.append("changepoint detected")
        if p_value is not None:
            parts.append(f"Welch p={p_value:.4f}")
        reason = "; ".join(parts)

    return StatisticalSignal(
        significant=bool(significant),
        max_abs_z=round(max_abs_z, 4),
        z_threshold=z_threshold,
        z_passed=bool(z_passed),
        changepoint_found=bool(changepoint_found),
        p_value=None if p_value is None else round(p_value, 6),
        p_threshold=p_threshold,
        p_passed=p_passed,
        effect_size_cohens_d=None if effect_size is None else round(effect_size, 4),
        reason=reason,
    )


def assess_materiality(
    contract: KPIContract,
    *,
    abs_effect: float,
    rel_effect_pct: float,
    duration_days: int,
) -> MaterialityResult:
    """The business gate, read straight from the contract.

    (abs_effect >= min_abs_effect OR rel_effect >= min_rel_effect_pct)
    AND duration >= min_duration_days

    Magnitude is compared on absolute value: a drop is as material as a rise.
    """
    rule = contract.materiality
    abs_passed = abs(abs_effect) >= rule.min_abs_effect
    rel_passed = abs(rel_effect_pct) >= rule.min_rel_effect_pct
    duration_passed = duration_days >= rule.min_duration_days
    material = (abs_passed or rel_passed) and duration_passed

    if material:
        hit = []
        if abs_passed:
            hit.append(
                f"|effect| {abs(abs_effect):,.0f} >= {rule.min_abs_effect:,.0f} "
                f"{rule.min_abs_effect_unit}"
            )
        if rel_passed:
            hit.append(
                f"|relative| {abs(rel_effect_pct):.2f}% >= {rule.min_rel_effect_pct}%"
            )
        reason = (
            f"material: {' and '.join(hit)}, sustained {duration_days}d "
            f">= {rule.min_duration_days}d"
        )
    elif not duration_passed:
        reason = (
            f"not material: lasted {duration_days}d, below the "
            f"{rule.min_duration_days}d minimum duration"
        )
    else:
        reason = (
            f"not material: |effect| {abs(abs_effect):,.0f} below "
            f"{rule.min_abs_effect:,.0f} {rule.min_abs_effect_unit} and "
            f"|relative| {abs(rel_effect_pct):.2f}% below "
            f"{rule.min_rel_effect_pct}%"
        )

    return MaterialityResult(
        abs_effect=round(abs_effect, 4),
        rel_effect_pct=round(rel_effect_pct, 4),
        duration_days=duration_days,
        min_abs_effect=rule.min_abs_effect,
        min_rel_effect_pct=rule.min_rel_effect_pct,
        min_duration_days=rule.min_duration_days,
        unit=rule.min_abs_effect_unit,
        abs_effect_passed=bool(abs_passed),
        rel_effect_passed=bool(rel_passed),
        duration_passed=bool(duration_passed),
        business_materiality=bool(material),
        rule=rule.rule,
        reason=reason,
    )
