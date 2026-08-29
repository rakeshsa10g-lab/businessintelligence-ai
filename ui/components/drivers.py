"""Level 2 — why it moved. Driver contributions.

Two research findings shape this chart.

The COVID-dashboard study found that symbol size which does not encode the
underlying proportion misleads even when every number is correct. So the bars
share one zero-anchored axis scaled to the whole movement: bar length *is*
contribution share, and the unexplained residual is drawn rather than dropped.
A chart that silently omits the part it cannot explain is claiming a complete
decomposition it does not have.

The YouTube study found that more visible options reduce the chance of any
decision. So three drivers show by default and the rest are one click away.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from graph.types import RunResult
from ui import theme

DEFAULT_VISIBLE = 3


def driver_rows(result: RunResult) -> list[dict]:
    """Contributions, read off the frozen bundle. Nothing is recomputed."""
    bundle = result.bundle
    if bundle is None or not bundle.hypotheses:
        return []

    attribution = bundle.attribution
    identity = getattr(attribution, "identity", None) if attribution else None
    rows: list[dict] = []

    if identity is not None:
        for term in getattr(identity, "drivers", []) or []:
            rows.append({
                "name": str(term.driver or "").replace("_", " ").title(),
                "value": float(term.contribution or 0.0),
                "share": (term.contribution_pct / 100.0
                          if term.contribution_pct is not None else None),
            })

    if not rows:
        # Fall back to the ranked hypotheses' own contribution figures.
        for h in bundle.hypotheses:
            rows.append({
                "name": (h.driver_name or h.driver_id or "").replace("_", " ").title(),
                "value": float(h.contribution or 0.0),
                "share": h.contribution_share,
            })

    rows = [r for r in rows if r["name"]]
    rows.sort(key=lambda r: -abs(r["value"]))
    return rows


def _figure(rows: list[dict], unit: str = "INR") -> go.Figure:
    names = [r["name"] for r in rows][::-1]
    values = [r["value"] for r in rows][::-1]
    # One semantic across the whole product: red is *adverse* — a factor that
    # pushed the KPI down here, a document that argues against the leading
    # hypothesis in the evidence panel. Green is *favourable* — a factor that
    # pushed the KPI up, or a document that corroborates.
    #
    # The UX mapping previously claimed red was reserved for contradicting
    # evidence alone, which this chart had always contradicted: S1 renders a
    # large red bar for conversion rate. The mapping was corrected rather than
    # the chart recoloured, because red-means-down is the stronger mental model
    # in a revenue chart and fighting it would cost more comprehension than the
    # narrower reservation was worth. See eval/growth_design_ux_mapping.md.
    colours = [theme.CONTRA if v < 0 else theme.SUPPORT for v in values]

    fig = go.Figure(
        go.Bar(
            x=values, y=names, orientation="h",
            marker=dict(color=colours),
            hovertemplate="%{y}<br>%{x:,.0f} " + unit + "<extra></extra>",
            text=[f"{v:,.0f}" for v in values],
            textposition="auto",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(
        height=max(150, 46 * len(names) + 60),
        margin=dict(l=0, r=10, t=6, b=24),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(size=12, color=theme.INK),
        xaxis=dict(
            title=dict(text=f"Contribution to the movement ({unit})",
                       font=dict(size=11, color=theme.INK_FAINT)),
            zeroline=True, zerolinecolor=theme.INK_FAINT, zerolinewidth=1,
            gridcolor="#f0f2f5", showline=False,
            tickfont=dict(size=10, color=theme.INK_FAINT),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=12)),
        showlegend=False, bargap=0.42,
    )
    return fig


def render(result: RunResult) -> None:
    rows = driver_rows(result)
    if not rows:
        st.markdown(
            f'<div style="font-size:.86rem;color:{theme.INK_FAINT};">'
            f"No driver decomposition is available for this movement.</div>",
            unsafe_allow_html=True,
        )
        return

    bundle = result.bundle
    top = bundle.hypotheses[0] if bundle and bundle.hypotheses else None

    if top is not None and top.driver_name:
        share = top.contribution_share
        # A single factor can exceed 100% when another moved the opposite way:
        # here conversion fell further than revenue did, because sessions rose
        # and partly offset it. That is what an exact identity decomposition
        # looks like, but "110%" reads as a bug, so it is explained inline
        # rather than shown bare or silently clipped.
        if share is not None and abs(share) > 1.0:
            # One decimal place here specifically: at zero decimals a share
            # of 1.0047 rounds to "100%", which reads as self-contradictory
            # next to "more than the whole movement".
            share_text = (
                f", accounting for more than the whole movement "
                f"({abs(share):.1%}) — other factors moved the opposite way "
                f"and partly offset it"
            )
        elif share:
            share_text = f", accounting for {abs(share):.0%} of the movement"
        else:
            share_text = ""

        st.markdown(
            theme.claim(
                f"<b>{top.driver_name}</b> is the largest contributor"
                f"{share_text}.",
                "analysis",
            ),
            unsafe_allow_html=True,
        )

    show_all = st.session_state.get("show_all_drivers", False)
    visible = rows if show_all else rows[:DEFAULT_VISIBLE]

    st.plotly_chart(_figure(visible))

    # States the colour rule at the point of use rather than leaving the reader
    # to infer it — and keeps the UI and the UX mapping saying the same thing.
    st.markdown(
        f'<div style="font-size:.78rem;color:{theme.INK_FAINT};'
        f'margin-top:-.3rem;">'
        f'<span style="color:{theme.CONTRA};font-weight:650;">Red</span>'
        f' pushed {("the KPI")} down &middot; '
        f'<span style="color:{theme.SUPPORT};font-weight:650;">green</span>'
        f' pushed it up.</div>',
        unsafe_allow_html=True,
    )

    if len(rows) > DEFAULT_VISIBLE:
        hidden = len(rows) - DEFAULT_VISIBLE
        label = ("Show fewer drivers" if show_all
                 else f"Show {hidden} smaller driver(s)")
        if st.button(label, key="drivers_toggle"):
            st.session_state["show_all_drivers"] = not show_all
            st.rerun()

    if top is not None and getattr(top, "slice", None):
        parts = ", ".join(f"{k} = {v}" for k, v in dict(top.slice).items())
        st.markdown(
            f'<div style="font-size:.8rem;color:{theme.INK_FAINT};'
            f'margin-top:.4rem;">Most affected slice: {parts}</div>',
            unsafe_allow_html=True,
        )
