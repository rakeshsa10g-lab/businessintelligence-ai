"""Reliability, expressed as a track record rather than a number.

The brief forbids a naked `Confidence: 0.82`, and the reason is the one the
COVID-dashboard study identifies: a number printed without a qualifier reads as
precise. `0.82` invites the question "82% of what?" and supplies no answer.

The social-proof principle sharpens it further. A counter that a reader cannot
interpret creates a *credibility gap* — worse than no counter, because it looks
like evidence. "12 of 12" is exactly such a counter unless it says, in the same
breath, that the twelve are synthetic and that twelve is a small number.

So three things are always rendered together and never separated:

1. the band,
2. the observed track record for that band, or an explicit statement that there
   is not one,
3. the provenance of those cases.

`confidence.render()` already composes (1) and (2) in the backend. This module
does not recompute a score — it presents what Stage 9 produced.
"""

from __future__ import annotations

import streamlit as st

from confidence.types import ConfidenceBand
from graph.types import RunResult
from ui import theme

#: Plain-language band names. The enum values are internal vocabulary.
BAND_LABEL = {
    ConfidenceBand.HIGH: "High reliability",
    ConfidenceBand.MEDIUM: "Moderate reliability",
    ConfidenceBand.LOW: "Low reliability",
    ConfidenceBand.UNCALIBRATED: "Uncalibrated",
    ConfidenceBand.INSUFFICIENT: "Insufficient",
}

BAND_ACCENT = {
    ConfidenceBand.HIGH: theme.SUPPORT,
    ConfidenceBand.MEDIUM: theme.ACCENT,
    ConfidenceBand.LOW: theme.CAUTION,
    ConfidenceBand.UNCALIBRATED: theme.CAUTION,
    ConfidenceBand.INSUFFICIENT: theme.INK_FAINT,
}


def basis_sentence(result: RunResult) -> str:
    """What the band is grounded in — or the honest absence of a ground."""
    conf = result.confidence
    if conf is None:
        return "No reliability estimate was produced for this run."

    entry = getattr(conf, "calibration", None)
    if entry is None or not getattr(entry, "total", 0):
        return (
            "There are not enough comparable past cases to state how often "
            "this kind of call has been right."
        )

    if conf.band is ConfidenceBand.UNCALIBRATED:
        return (
            f"Only {entry.total} comparable case(s) have been recorded — "
            f"below the minimum needed to quote a hit rate. The signal is "
            f"strong, but its track record is not established."
        )

    return f"Correct in {entry.correct} of {entry.total} similar past cases."


def provenance_sentence(result: RunResult) -> str | None:
    """Never let the counter travel without saying what the cases are."""
    conf = result.confidence
    if conf is None:
        return None
    entry = getattr(conf, "calibration", None)
    if entry is None or not getattr(entry, "total", 0):
        return None
    if getattr(conf, "calibration_is_synthetic", False):
        return ("These cases come from a synthetic evaluation set, not from "
                "production history.")
    return f"Source: {getattr(conf, 'calibration_source', 'recorded outcomes')}."


def render(result: RunResult) -> None:
    conf = result.confidence
    if conf is None:
        return

    band = conf.band
    accent = BAND_ACCENT.get(band, theme.INK_FAINT)
    label = BAND_LABEL.get(band, band.value.title())
    caveat = provenance_sentence(result)

    st.markdown(
        f"""
        <div class="bi-rel" style="border-left-color:{accent};">
          <div class="bi-rel-band" style="color:{accent};">{label}</div>
          <div class="bi-rel-basis">{basis_sentence(result)}</div>
          {f'<div class="bi-rel-caveat">{caveat}</div>' if caveat else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_detail(result: RunResult) -> None:
    """The weighted components. Method view only — not the default screen."""
    conf = result.confidence
    if conf is None:
        return

    components = getattr(conf, "components", None) or ()
    if not components:
        return

    st.markdown('<div class="bi-sec">Reliability components</div>',
                unsafe_allow_html=True)
    rows = [
        f"| {c.name.replace('_', ' ').title()} | {c.raw:.2f} | "
        f"{c.weight:.2f} | {c.weighted:.3f} |"
        for c in components
    ]
    st.markdown(
        "| Component | Score | Weight | Contribution |\n|---|---|---|---|\n"
        + "\n".join(rows)
    )
    st.caption(
        f"Weighted total {conf.score:.3f}. The weights are configuration "
        f"(`config/confidence.yaml` v{conf.config_version}), not learned."
    )
    multiplier = getattr(conf, "contradiction_multiplier", None)
    if multiplier is not None and multiplier != 1.0:
        st.caption(
            f"Contradicting evidence scaled the result by ×{multiplier:.2f}."
        )
