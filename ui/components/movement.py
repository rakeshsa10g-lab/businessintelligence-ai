"""Level 1 — what changed, and does it matter.

The Amber Alert study's finding is that critical information buried in prose
forces the reader to read and remember, when recognition is faster than
recollection. So this block is one line at the largest type on the page, and
nothing competes with it for that position.

It always renders the materiality verdict alongside the movement. Showing a
movement without saying whether it cleared the gate is the omission the COVID
dashboard study warns about — a number that looks like a finding when the
system has not decided it is one.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult, TerminalState
from ui import theme


def _fact(result: RunResult, needle: str):
    """Find a metric fact by id fragment. Facts are measured, never derived here."""
    bundle = result.bundle
    if bundle is None:
        return None
    for f in bundle.metric_facts:
        if needle in f.fact_id:
            return f
    return None


def headline_numbers(result: RunResult) -> dict:
    """The movement, read off the bundle. The UI computes nothing."""
    bundle = result.bundle
    det = result.detection or (bundle.detection if bundle else None)
    pct = getattr(det, "pct_delta", None)
    abs_delta = getattr(det, "abs_delta", None)
    return {
        "kpi": (bundle.kpi_name if bundle else result.kpi_id),
        "pct": pct,
        "abs": abs_delta,
        "start": getattr(det, "observed_start", None),
        "end": getattr(det, "observed_end", None),
        "material": bool(getattr(det, "is_material", False)),
        "outcome": getattr(det, "outcome", None),
        "baseline": getattr(det, "baseline_value", None),
        "observed": getattr(det, "observed_value", None),
    }


def render(result: RunResult, scenario_label: str) -> None:
    n = headline_numbers(result)
    pct = n["pct"]

    if pct is None:
        arrow, magnitude = "", "No movement measured"
    else:
        arrow = "↓" if pct < 0 else "↑"
        magnitude = f"{arrow} {abs(pct):.1f}%"

    # "Below materiality threshold" is a specific claim: the rule ran and
    # failed. It is only true for NO_MATERIAL_FINDING. Sparse history and a
    # failed data-quality gate stop BEFORE materiality is ever evaluated, and
    # showing that chip there would assert a check that never ran.
    from detection.types import DetectionOutcome

    outcome = n.get("outcome")
    if n["material"]:
        chip = theme.chip("Material movement", "material")
    elif outcome is DetectionOutcome.NO_MATERIAL_FINDING:
        chip = theme.chip("Below materiality threshold", "quiet")
    elif outcome is DetectionOutcome.SPARSE_HISTORY:
        chip = theme.chip("Not enough history to assess", "caution")
    elif outcome is DetectionOutcome.INSUFFICIENT_DATA:
        chip = theme.chip("Data quality gate not passed", "caution")
    else:
        chip = theme.chip("Not assessed", "quiet")

    window = ""
    if n["start"] and n["end"]:
        window = (f"{n['start'].strftime('%d %b')} → "
                  f"{n['end'].strftime('%d %b %Y')}")

    st.markdown(
        f"""
        <div class="bi-kpi">{n['kpi']} · {scenario_label}</div>
        <div style="display:flex;align-items:baseline;gap:1.1rem;
                    flex-wrap:wrap;">
          <div class="bi-move">{magnitude}</div>
          <div style="padding-bottom:.5rem;">{chip}</div>
        </div>
        <div class="bi-window">{window}</div>
        """,
        unsafe_allow_html=True,
    )

    # The rupee figure is a second-order fact: useful, but it must not compete
    # with the percentage for the reader's first glance.
    if n["abs"] is not None and n["baseline"] is not None:
        st.markdown(
            f"""<div style="font-size:.84rem;color:{theme.INK_SOFT};
                 margin-top:.5rem;">
                 {abs(n['abs']):,.0f} INR against a baseline of
                 {n['baseline']:,.0f} INR
                 </div>""",
            unsafe_allow_html=True,
        )


def render_answer_line(result: RunResult) -> None:
    """One sentence answering "why", above the fold.

    The verified narrative headline, labelled as generated. A reader must be
    able to see at a glance that this sentence was written, while the numbers
    above it were measured (Part 5).
    """
    bundle = result.bundle
    if bundle is None or not bundle.hypotheses:
        return
    top = bundle.hypotheses[0]

    # The leading *explanation*, which is what "why" means to a reader — not
    # the narrative headline, which restates the movement and would sit under
    # a HYPOTHESIS label while asserting an observed fact.
    st.markdown(
        theme.claim(
            f"{theme.humanise(top.statement)}."
            + ("" if top.causal_language_allowed else
               " <i>Association only — the counterfactual test did not license"
               " a causal claim.</i>"),
            "hypothesis",
        ),
        unsafe_allow_html=True,
    )
