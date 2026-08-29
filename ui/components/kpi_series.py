"""Level 1 supporting exhibit — the KPI itself, over time.

The judge audit found the workspace answered "what changed" numerically but
never *showed* the series, which is the one exhibit a BI audience expects
before it will accept a decomposition of that series.

Nothing here is computed. Every value is read off `DetectionResult`:

- `decomposition.dates` / `.observed`   the series
- `decomposition.trend`                 the baseline STL already fitted
- `changepoint.changepoint_dates`       where PELT broke the residual
- `observed_start` / `observed_end`     the investigation window

The chart is deliberately quiet when detection found nothing material. S7 is a
schema-rename artefact that *looks* like +5.9% growth: if it rendered with a
changepoint marker and a shaded window it would assert an event the system
explicitly declined to call, which is the habituation failure the materiality
gate exists to prevent. So the annotations are gated on the outcome, not on
whether the underlying fields happen to be populated.
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from detection.types import DetectionOutcome
from graph.types import RunResult
from ui import theme

# Below this many points a line chart is noise, not a trend.
MIN_POINTS = 8


def _series(result: RunResult) -> tuple[list[date], list[float], list[float]]:
    """Dates, observed, trend — or three empty lists if unavailable."""
    detection = getattr(result, "detection", None)
    decomposition = getattr(detection, "decomposition", None) if detection else None
    if decomposition is None:
        return [], [], []

    dates = list(getattr(decomposition, "dates", []) or [])
    observed = list(getattr(decomposition, "observed", []) or [])
    trend = list(getattr(decomposition, "trend", []) or [])

    if len(dates) != len(observed) or len(dates) < MIN_POINTS:
        return [], [], []
    if len(trend) != len(dates):
        trend = []
    return dates, observed, trend


def _figure(
    dates: list[date],
    observed: list[float],
    trend: list[float],
    *,
    window: tuple[date | None, date | None],
    changepoints: list[date],
    material: bool,
    unit: str,
) -> go.Figure:
    fig = go.Figure()

    # The observed series is the subject; it is drawn last so it sits on top,
    # but added first so the legend order reads observed-then-baseline.
    fig.add_trace(
        go.Scatter(
            x=dates, y=observed, mode="lines", name="Observed",
            line=dict(color=theme.ACCENT, width=2),
            hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} " + unit + "<extra></extra>",
        )
    )

    if trend:
        fig.add_trace(
            go.Scatter(
                x=dates, y=trend, mode="lines", name="Trend (STL)",
                line=dict(color=theme.INK_FAINT, width=1.5, dash="dot"),
                hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} " + unit
                              + " trend<extra></extra>",
            )
        )

    start, end = window
    if material and start and end:
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=theme.CONTRA, opacity=0.07,
            line_width=0, layer="below",
            annotation_text="investigation window",
            annotation_position="top left",
            annotation=dict(font=dict(size=10, color=theme.INK_FAINT)),
        )

    if material:
        for cp in changepoints:
            fig.add_vline(
                x=cp, line=dict(color=theme.CONTRA, width=1.5, dash="dash"),
            )

    fig.update_layout(
        height=230,
        margin=dict(l=0, r=10, t=8, b=24),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=12, color=theme.INK),
        xaxis=dict(
            showgrid=False, showline=True, linecolor=theme.RULE,
            tickfont=dict(size=10, color=theme.INK_FAINT),
        ),
        yaxis=dict(
            title=dict(text=unit, font=dict(size=11, color=theme.INK_FAINT)),
            gridcolor="#f0f2f5", showline=False, zeroline=False,
            tickfont=dict(size=10, color=theme.INK_FAINT),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1.0,
            font=dict(size=10, color=theme.INK_FAINT),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
    )
    return fig


def render(result: RunResult, *, unit: str = "INR") -> None:
    dates, observed, trend = _series(result)
    if not dates:
        return

    detection = result.detection
    material = detection.outcome == DetectionOutcome.MATERIAL_EVENT

    changepoints: list[date] = []
    if detection.changepoint is not None:
        changepoints = [
            d for d in (getattr(detection.changepoint, "changepoint_dates", []) or [])
            if dates[0] <= d <= dates[-1]
        ]

    window = (detection.observed_start, detection.observed_end)

    st.plotly_chart(
        _figure(
            dates, observed, trend,
            window=window, changepoints=changepoints,
            material=material, unit=unit,
        )
    )

    if material and changepoints:
        marks = ", ".join(d.strftime("%d %b %Y") for d in changepoints[:3])
        caption = (
            f"Dashed line: changepoint detected by PELT ({marks}). "
            f"Shaded band: the window compared against baseline."
        )
    elif material:
        caption = "Shaded band: the window compared against baseline."
    else:
        # Explicitly says why the chart is bare, so a quiet screen reads as a
        # decision rather than as missing data.
        caption = (
            "No changepoint is marked: detection did not find a material event, "
            "so nothing here is annotated as one."
        )

    st.markdown(
        f'<div style="font-size:.78rem;color:{theme.INK_FAINT};'
        f'margin-top:-.35rem;">{caption}</div>',
        unsafe_allow_html=True,
    )
