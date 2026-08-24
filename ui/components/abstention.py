"""Abstention states — designed, not defaulted.

The Amber Alert study's sharpest finding for this product is *habituation
through irrelevance*: alerts perceived as non-actionable train people to ignore
all alerts, including the ones that matter. A system with a materiality gate
protects against exactly that, and a UI that renders a non-event with the same
weight as a real one throws the protection away.

So these screens are deliberately **quieter** than a finding: no driver chart,
no reliability chip, no action block. Showing less when the system knows less
is the product working, and it should look like it.

Each state answers three questions rather than one: what is known, what is
missing, and what would change the answer. The Amber Alert actionability gap
applies to a decline as much as to a finding — "we don't know" without "and
here is what would settle it" leaves the reader stuck.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult, TerminalState
from ui import theme
from ui.components import hypotheses as hyp_view


def _shell(title: str, body: str, *, chip_text: str = "",
           chip_kind: str = "quiet") -> None:
    chip = theme.chip(chip_text, chip_kind) if chip_text else ""
    st.markdown(
        f"""
        <div class="bi-abstain">
          {f'<div style="margin-bottom:.6rem;">{chip}</div>' if chip else ''}
          <div class="bi-abstain-title">{title}</div>
          <div class="bi-abstain-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _next_step(text: str) -> None:
    st.markdown(
        f"""<div style="border-left:3px solid {theme.ACCENT};
             padding:.55rem .85rem;margin-top:.9rem;
             background:{theme.ACCENT_SOFT};border-radius:0 4px 4px 0;">
             <span style="font-size:.68rem;font-weight:700;letter-spacing:.09em;
             color:{theme.ACCENT};">WHAT WOULD CHANGE THIS</span><br>
             <span style="font-size:.87rem;color:{theme.INK};">{text}</span>
             </div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
def sparse_history(result: RunResult) -> None:
    det = result.detection or (result.bundle.detection if result.bundle else None)

    have = required = None
    coverage = getattr(det, "coverage", None) if det else None
    if coverage is not None:
        have = getattr(coverage, "observations_available", None)
        required = getattr(coverage, "observations_required", None)

    counts = ""
    if have is not None and required is not None:
        counts = (
            f"<br><br><b>{have} days</b> of history are available. "
            f"A seasonal baseline needs <b>{required}</b>."
        )

    _shell(
        "Not enough history to judge this yet",
        "This slice is too new for the system to know what normal looks like. "
        "A weekly pattern cannot be separated from a real change until there "
        "is enough history to establish one." + counts +
        "<br><br>Extrapolating from a short series would produce a confident "
        "number with nothing behind it, so the system declines instead.",
        chip_text="Sparse history", chip_kind="caution",
    )
    if have is not None and required is not None and required > have:
        _next_step(
            f"About {required - have} more days of observations. The system "
            f"will start explaining this slice on its own once the baseline "
            f"exists — no action is needed now."
        )
    else:
        _next_step("More observations for this slice.")


def insufficient_evidence(result: RunResult) -> None:
    bundle = result.bundle
    _shell(
        "A real movement, but nothing explains it",
        "The movement itself is established — it cleared detection and the "
        "materiality gate. What is missing is corroboration: no source the "
        "system can read supports any particular explanation.",
        chip_text="Insufficient evidence", chip_kind="caution",
    )

    if bundle is not None and bundle.hypotheses:
        st.markdown('<div class="bi-sec">Leading candidates, unconfirmed</div>',
                    unsafe_allow_html=True)
        hyp_view.render(result)

    _next_step(
        "A source that covers this period and slice — a deployment log, a "
        "support queue, or a supplier note. Naming the missing source is "
        "usually enough to close the gap."
    )


def conflicting_evidence(result: RunResult) -> None:
    _shell(
        "Two explanations fit equally well",
        "The evidence supports more than one cause, and they imply different "
        "owners. Choosing between them arbitrarily would send the wrong team "
        "to investigate, so the system escalates rather than picking.",
        chip_text="Conflicting evidence", chip_kind="contra",
    )
    st.markdown('<div class="bi-sec">Competing explanations</div>',
                unsafe_allow_html=True)
    hyp_view.render(result)
    _next_step(
        "A person who can distinguish the two — the analyst review below "
        "carries the specific question."
    )


def no_material_event(result: RunResult) -> None:
    det = result.detection or (result.bundle.detection if result.bundle else None)
    materiality = getattr(det, "materiality", None) if det else None

    detail = ""
    if materiality is not None:
        # The rule can fail on either leg (absolute or relative effect size),
        # so the message names whichever leg the movement actually missed
        # rather than a generic "below threshold".
        if not materiality.abs_effect_passed:
            detail = (
                f"<br><br>The movement was <b>{materiality.abs_effect:,.0f} "
                f"{materiality.unit}</b>, below the "
                f"<b>{materiality.min_abs_effect:,.0f} {materiality.unit}</b> "
                f"minimum."
            )
        elif not materiality.rel_effect_passed:
            detail = (
                f"<br><br>The movement was <b>{materiality.rel_effect_pct:.1f}%</b>, "
                f"below the <b>{materiality.min_rel_effect_pct:.1f}%</b> minimum."
            )
        elif not materiality.duration_passed:
            detail = (
                f"<br><br>It lasted <b>{materiality.duration_days} day(s)</b>, "
                f"below the <b>{materiality.min_duration_days}</b> required."
            )

    _shell(
        "Nothing here needs your attention",
        "The system looked and found no movement large or sustained enough to "
        "act on." + detail +
        "<br><br>This is a result, not a failure. Reporting every small "
        "fluctuation is how a system trains people to ignore it.",
        chip_text="No material event", chip_kind="quiet",
    )
    # P2-03: the raw detector string used to be surfaced here in an expander.
    # It reads `net_revenue [channel=Marketplace]: statistical_signal=True,
    # business_materiality=False -> NO_MATERIAL_FINDING...` — gate names and
    # internal enum values, which Part 19 confines to Method and Audit. The
    # numbers a business reader needs are already stated above, in the
    # `detail` block, phrased as the threshold that was actually missed.


def access_denied(result: RunResult) -> None:
    _shell(
        "This analysis is not available for your role",
        "Your role does not have access to the data this question needs. "
        "A colleague with the required entitlement can run it.",
        chip_text="Restricted", chip_kind="caution",
    )
    _next_step("Ask a permitted reader to run this, or request access.")


def clarify(result: RunResult) -> None:
    _shell(
        "That KPI is not one this system knows",
        result.terminal_reason or "Choose one of the available KPIs.",
        chip_text="Needs clarification", chip_kind="quiet",
    )


def data_quality(result: RunResult) -> None:
    # `terminal_reason` here can be a raw exception string — on a locked
    # warehouse it is literally `detect: IOException: Cannot open file ...`.
    # Same rule as P2-03: the business view says what happened, Audit says
    # what the exception was.
    _shell(
        "The underlying data did not pass its quality gate",
        "The system stopped before analysing, because the inputs would not "
        "support a trustworthy answer.",
        chip_text="Data quality", chip_kind="caution",
    )
    _next_step("A refreshed or corrected load of the source data.")


def unexpected(result: RunResult) -> None:
    """Never a traceback in the business view (Part 19)."""
    _shell(
        "This analysis could not be completed",
        "Something went wrong while running it. The technical detail is "
        "recorded in the Audit view; nothing partial has been reported as a "
        "finding.",
        chip_text="Run incomplete", chip_kind="contra",
    )


#: Terminal → renderer. A lookup rather than a chain of ifs, so a terminal
#: added without a screen fails visibly instead of falling into a generic one.
RENDERERS = {
    TerminalState.ABSTAIN_SPARSE_HISTORY: sparse_history,
    TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE: insufficient_evidence,
    TerminalState.ABSTAIN_CONFLICTING_EVIDENCE: conflicting_evidence,
    TerminalState.NO_MATERIAL_EVENT: no_material_event,
    TerminalState.ACCESS_DENIED: access_denied,
    TerminalState.CLARIFY_REQUESTED: clarify,
    TerminalState.ABSTAIN_DATA_QUALITY: data_quality,
    TerminalState.CONTRACT_ERROR: unexpected,
}


def render(result: RunResult) -> bool:
    """Render the abstention screen for this terminal, if it is one."""
    renderer = RENDERERS.get(result.terminal)
    if renderer is None:
        return False
    renderer(result)
    return True
