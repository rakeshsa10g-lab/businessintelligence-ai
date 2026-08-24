"""The sparse-history path (Part 9.4, Scenario 4).

When n < min_history_days: do not run STL, do not run PELT, and say so.

This turns "we don't have enough data" from an error state into designed,
defensible product behaviour — the single most under-rated scenario in the
Round 2 list, because it is the one most teams will fake.

Four rules, all enforced here rather than left to the narrator:
  1. peer-group baseline, comparing like-for-like at the same age
  2. a range from peer dispersion, never a point estimate
  3. a hard LOW confidence ceiling that evidence cannot argue upwards
  4. levers requiring a stable baseline are suppressed entirely
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

CONFIDENCE_CEILING = "LOW"


def peer_cohort_baseline(
    subject: pd.Series,
    peers: dict[str, pd.Series],
    *,
    subject_label: str,
    launch_date: date,
    peer_launch_dates: dict[str, date] | None = None,
) -> dict:
    """Compare a young series to comparable cohorts at the same age.

    `subject` is indexed by date. Each peer series is re-indexed to days since
    its own launch so that day 23 is compared with day 23, not with a mature
    steady state.
    """
    subject_age = [(d - launch_date).days for d in subject.index]
    subject_by_age = pd.Series(subject.to_numpy(dtype=float), index=subject_age)
    max_age = int(max(subject_age)) if subject_age else 0

    peer_curves: dict[str, pd.Series] = {}
    for name, s in peers.items():
        if s.empty:
            continue
        origin = (peer_launch_dates or {}).get(name, s.index.min())
        ages = [(d - origin).days for d in s.index]
        curve = pd.Series(s.to_numpy(dtype=float), index=ages)
        # normalise scale: peers differ in absolute size, so compare shape
        anchor = curve.loc[: max(7, max_age)].mean()
        if anchor and np.isfinite(anchor) and anchor != 0:
            peer_curves[name] = curve / anchor

    if not peer_curves:
        return {
            "method": "peer_cohort_baseline",
            "subject": subject_label,
            "peers_used": [],
            "usable": False,
            "note": "no comparable cohort had enough history to anchor against",
            "confidence_ceiling": CONFIDENCE_CEILING,
        }

    frame = pd.DataFrame(peer_curves)
    common = frame.loc[frame.index.isin(range(0, max_age + 1))].dropna(how="all")

    subject_anchor = subject_by_age.loc[: max(7, max_age)].mean()
    subject_norm = (
        subject_by_age / subject_anchor
        if subject_anchor and np.isfinite(subject_anchor) and subject_anchor != 0
        else subject_by_age
    )

    peer_median = common.median(axis=1)
    peer_lo = common.quantile(0.25, axis=1)
    peer_hi = common.quantile(0.75, axis=1)

    aligned = subject_norm.reindex(peer_median.index).dropna()
    if aligned.empty:
        deviation = None
        within = None
    else:
        idx = aligned.index
        deviation = float(
            (aligned - peer_median.reindex(idx)).mean()
        )
        within = bool(
            (
                (aligned >= peer_lo.reindex(idx))
                & (aligned <= peer_hi.reindex(idx))
            ).mean()
            >= 0.5
        )

    return {
        "method": "peer_cohort_baseline",
        "subject": subject_label,
        "peers_used": sorted(peer_curves),
        "usable": True,
        "subject_age_days": max_age + 1,
        "normalised_deviation_from_peer_median": (
            None if deviation is None else round(deviation, 4)
        ),
        "within_peer_interquartile_range": within,
        # a range, never a point estimate (rule 2)
        "peer_band_p25": round(float(peer_lo.mean()), 4),
        "peer_band_median": round(float(peer_median.mean()), 4),
        "peer_band_p75": round(float(peer_hi.mean()), 4),
        "confidence_ceiling": CONFIDENCE_CEILING,
    }


def caveat_text(observations: int, required: int, period: int) -> str:
    return (
        f"{observations} days of history; {required} required for seasonal "
        f"detection at period {period}. Seasonality is assumed, not measured."
    )


def suppressed_lever_rule() -> dict:
    """Levers tagged requires_stable_baseline are filtered out entirely.

    Stage 9 consumes this; recorded here so the rule lives with the reason.
    """
    return {
        "filter": "requires_stable_baseline == true",
        "action": "suppress",
        "reason": (
            "A pricing or promotional change should not be recommended off "
            "23 days of data."
        ),
    }
