"""Competing explanations, ranked and compared.

The YouTube study's finding is that comparison is easier between a small number
of similar candidates, and that a long flat list produces no decision at all.
So this renders two or three, always ranked, always as a comparison with a
leader — never as an undifferentiated list.

The brief also forbids exposing arbitrary internal scores. `0.7595` is
meaningless to a reader: it is a product of five weighted sub-scores whose
scale has no external referent. What *is* meaningful is the typed status the
backend already assigns, and whether causal language was licensed — because
that second one changes what the reader is allowed to conclude.
"""

from __future__ import annotations

import streamlit as st

from evidence.types import HypothesisStatus
from graph.types import RunResult
from ui import theme

#: Meaningful labels, per Part 7. The enum name is internal vocabulary.
STATUS_LABEL = {
    HypothesisStatus.SUPPORTED: ("Strong evidence", "support"),
    HypothesisStatus.PLAUSIBLE: ("Moderate evidence", "caution"),
    HypothesisStatus.CONFLICTED: ("Conflicted", "contra"),
    HypothesisStatus.INSUFFICIENT: ("Insufficient evidence", "quiet"),
    HypothesisStatus.MULTI_DIMENSIONAL: ("Spans several dimensions", "caution"),
    HypothesisStatus.REJECTED: ("Rejected", "quiet"),
}

MAX_SHOWN = 3


def render(result: RunResult, *, compact: bool = True) -> None:
    bundle = result.bundle
    if bundle is None or not bundle.hypotheses:
        return

    shown = list(bundle.hypotheses)[:MAX_SHOWN]

    for i, h in enumerate(shown, start=1):
        label, kind = STATUS_LABEL.get(
            h.status, (h.status.value.title(), "quiet"))

        causal = (
            theme.chip("Causal language licensed", "support")
            if h.causal_language_allowed
            else theme.chip("Association only", "quiet")
        )

        lead = ("<span style='font-size:.7rem;font-weight:700;"
                f"color:{theme.ACCENT};letter-spacing:.08em;'>LEADING "
                "EXPLANATION</span><br>") if i == 1 else ""

        support_n = len(h.supporting_evidence_ids or ())
        contra_n = len(h.contradicting_evidence_ids or ())
        counts = f"{support_n} supporting"
        if contra_n:
            counts += f" · {contra_n} contradicting"

        st.markdown(
            f"""
            <div class="bi-card">
              {lead}
              <div class="bi-card-head">{i}. {theme.humanise(h.statement)}</div>
              <div style="margin:.4rem 0 .3rem 0;">
                {theme.chip(label, kind)} {causal}
              </div>
              <div class="bi-card-meta">{counts}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not compact and h.status_reason:
            st.caption(h.status_reason)

    if not h.causal_language_allowed and shown:
        st.markdown(
            f'<div style="font-size:.78rem;color:{theme.INK_FAINT};'
            f'margin-top:.2rem;">Where causal language is not licensed, the '
            f'finding stands but the wording stays associative — the '
            f'counterfactual test did not establish cause.</div>',
            unsafe_allow_html=True,
        )
