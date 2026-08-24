"""Visual diagnostic for the West-region event (E1), Scenario S1.

One figure, five stacked panels, showing every step the engine took between
the raw series and the decision:

  1. raw KPI with the STL trend+seasonal counterfactual over it
  2. the trend alone
  3. the seasonal component
  4. the residual, with the MAD z threshold and the flagged days
  5. the residual again, with the PELT changepoint, the regime segment and
     the materiality verdict written out

The point is falsifiability. Anyone can look at this and say "your changepoint
is in the wrong place" or "that baseline is obviously bending into the event",
which is the fastest way to find out that it is.

Not Streamlit: a PNG on disk, so it can go in the deck and the appendix.

Run:  python -m eval.diagnostic_west
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from data import spec
from detection import decompose as dec
from detection import engine
from security.entitlements import Principal
from semantic.types import Window

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "diagnostic_west_e1.png"

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
SLICE = {"region": ["West"], "channel": ["Web", "Mobile App"]}

TRUE_START = date(2026, 7, 12)
TRUE_END = date(2026, 7, 26)

INK = "#1a1a1a"
MUTED = "#8a8a8a"
ACCENT = "#c0392b"
BASE = "#2c6fbb"
BAND = "#f2c9c4"


def build() -> Path:
    r = engine.detect("net_revenue", WINDOW, ANALYST, slice_filter=SLICE,
                      scenario_id="S1")
    d = r.decomposition
    dates = [np.datetime64(x) for x in d.dates]
    observed = np.asarray(d.observed)
    trend = np.asarray(d.trend)
    seasonal = np.asarray(d.seasonal)
    residual = np.asarray(d.residual)
    baseline = dec.baseline_from(d)

    z = np.asarray(r.robust_score.z_scores)
    thr = r.robust_score.z_threshold
    sigma = r.changepoint.residual_sigma or 1.0

    i = r.changepoint.selected_index
    j = r.changepoint.segment_end_index or len(observed)
    cp_date = dates[i]
    seg_end = dates[min(j, len(dates)) - 1]

    fig, ax = plt.subplots(5, 1, figsize=(13, 15), sharex=True)
    fig.suptitle(
        "Detection diagnostic - net revenue, West / Web + Mobile App (E1, scenario S1)",
        fontsize=14, fontweight="bold", color=INK, y=0.995,
    )

    def mark_event(a):
        a.axvspan(np.datetime64(TRUE_START), np.datetime64(TRUE_END),
                  color=BAND, alpha=0.45, zorder=0, lw=0)

    # 1 -- raw vs counterfactual
    a = ax[0]
    mark_event(a)
    a.plot(dates, observed, color=INK, lw=1.3, label="observed")
    a.plot(dates, baseline, color=BASE, lw=1.6, ls="--",
           label="STL counterfactual (trend + seasonal)")
    a.fill_between(dates, observed, baseline,
                   where=observed < baseline, color=ACCENT, alpha=0.18,
                   label="shortfall vs counterfactual")
    a.set_title("1. Raw KPI against the 'no event' baseline", loc="left",
                fontsize=11, color=INK)
    a.set_ylabel("INR / day")
    a.legend(loc="lower left", fontsize=8, frameon=False)

    # 2 -- trend
    a = ax[1]
    mark_event(a)
    a.plot(dates, trend, color=BASE, lw=1.8)
    a.set_title(
        f"2. STL trend (smoother = {d.trend_smoother} days, deliberately too "
        "stiff to follow the event)",
        loc="left", fontsize=11, color=INK,
    )
    a.set_ylabel("INR / day")

    # 3 -- seasonal
    a = ax[2]
    mark_event(a)
    a.plot(dates, seasonal, color=MUTED, lw=1.1)
    a.axhline(0, color=MUTED, lw=0.6, ls=":")
    a.set_title(
        f"3. Weekly seasonal component (period {d.seasonal_period}, "
        f"strength {d.seasonal_strength:.2f})",
        loc="left", fontsize=11, color=INK,
    )
    a.set_ylabel("INR / day")

    # 4 -- residual and the robust z threshold
    a = ax[3]
    mark_event(a)
    a.plot(dates, residual, color=INK, lw=1.0)
    a.axhline(0, color=MUTED, lw=0.6, ls=":")
    for s in (1, -1):
        a.axhline(s * thr * sigma, color=ACCENT, lw=0.9, ls="--")
    flagged = np.flatnonzero(np.asarray(r.robust_score.anomaly_flags, dtype=bool))
    if flagged.size:
        a.scatter([dates[k] for k in flagged], residual[flagged],
                  s=22, color=ACCENT, zorder=3,
                  label=f"|z| >= {thr} ({flagged.size} days)")
        a.legend(loc="lower left", fontsize=8, frameon=False)
    a.set_title(
        f"4. Residual with the robust MAD threshold (sigma = {sigma:,.0f}, "
        f"max |z| = {r.robust_score.max_abs_z:.1f})",
        loc="left", fontsize=11, color=INK,
    )
    a.set_ylabel("INR / day")

    # 5 -- changepoint, segment and verdict
    a = ax[4]
    mark_event(a)
    a.plot(dates, residual, color=INK, lw=1.0)
    a.axhline(0, color=MUTED, lw=0.6, ls=":")
    a.axvspan(cp_date, seg_end, color=ACCENT, alpha=0.13, lw=0,
              label="PELT regime segment")
    a.axvline(cp_date, color=ACCENT, lw=2.0,
              label=f"changepoint {r.changepoint.selected_date}")
    a.set_title(
        f"5. PELT changepoint and the materiality decision "
        f"({r.changepoint.shift_type.value}, "
        f"{r.changepoint.n_changepoints} candidates)",
        loc="left", fontsize=11, color=INK,
    )
    a.set_ylabel("INR / day")
    a.legend(loc="lower left", fontsize=8, frameon=False)

    m, sgl = r.materiality, r.statistical_signal
    verdict = (
        f"OUTCOME: {r.outcome.value}\n"
        f"statistical: {sgl.reason}\n"
        f"materiality: {m.reason}\n"
        f"measured {m.rel_effect_pct:+.1f}% over {m.duration_days}d "
        f"({m.abs_effect:+,.0f} {m.unit})   |   "
        f"ground truth -24.98% over {(TRUE_END - TRUE_START).days + 1}d"
    )
    a.text(0.005, -0.52, verdict, transform=a.transAxes, fontsize=9,
           family="monospace", va="top", color=INK,
           bbox=dict(boxstyle="round,pad=0.6", fc="#f6f6f4", ec="#d8d8d4"))

    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#e8e8e6", lw=0.6)
        a.set_axisbelow(True)
    ax[-1].xaxis.set_major_locator(mdates.MonthLocator())
    ax[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    fig.tight_layout(rect=[0, 0.06, 1, 0.985])
    fig.savefig(OUT, dpi=150, facecolor="white")
    plt.close(fig)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path.relative_to(ROOT)}")
