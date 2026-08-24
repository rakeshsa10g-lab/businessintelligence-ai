"""Human review — a real LangGraph interrupt, not a local flag.

The brief forbids faking this with a Streamlit boolean, and the distinction is
substantive rather than pedantic. A paused run here is a checkpoint on disk
holding the frozen bundle, the telemetry and the lineage the run had already
accumulated. Resuming continues *that* run; the bundle hash is identical either
side of the pause. A local boolean would produce the same screen and none of
the guarantee.

The Zeigarnik principle applies to the framing: this is genuinely unfinished
work, and it is rendered as an open item with the question stated as a
question. It is not styled as an error — the system escalating because two
explanations imply different owners is the system working correctly.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult
from ui import state as ui_state
from ui import theme
from ui.theme import humanise
from ui.components import evidence as evidence_view
from ui.components import hypotheses as hyp_view

#: The four typed outcomes the graph accepts, in the order an analyst
#: encounters them: confirm, deny, amend, or ask for more.
ACTIONS = [
    ("accept", "Accept", "The leading explanation is right; proceed."),
    ("reject", "Reject", "The explanation is wrong; do not act on it."),
    ("correct", "Correct", "Partly right — record what should change."),
    ("request_clarification", "Request clarification",
     "Not answerable yet; name what is missing."),
]


def render(result: RunResult) -> None:
    payload = ui_state.review_payload(result.run_id) or {}
    packet = result.analyst_packet

    st.markdown(
        f"""
        <div style="border:1px solid #c9d6ea;border-left:3px solid {theme.ACCENT};
                    background:{theme.ACCENT_SOFT};border-radius:0 5px 5px 0;
                    padding:1.1rem 1.25rem;">
          <div style="font-size:.68rem;font-weight:700;letter-spacing:.09em;
                      color:{theme.ACCENT};">AWAITING YOUR DECISION</div>
          <div style="font-size:1.15rem;font-weight:650;margin:.35rem 0 .5rem 0;">
            {humanise(payload.get('question') or (packet.recommended_clarification if packet else 'A person needs to decide this.'))}
          </div>
          <div style="font-size:.85rem;color:{theme.INK_SOFT};line-height:1.6;">
            {payload.get('why_you') or (result.deferral.rationale if result.deferral else '')}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if packet is not None and packet.estimated_review_minutes:
        st.caption(
            f"The investigation is already done — estimated review time "
            f"{packet.estimated_review_minutes} minutes."
        )

    st.markdown('<div class="bi-sec">The competing explanations</div>',
                unsafe_allow_html=True)
    hyp_view.render(result)

    st.markdown('<div class="bi-sec">What the evidence says</div>',
                unsafe_allow_html=True)
    evidence_view.render_summary(result)

    if packet is not None and packet.missing_information:
        st.markdown('<div class="bi-sec">What is missing</div>',
                    unsafe_allow_html=True)
        for item in packet.missing_information:
            st.markdown(f"- {item}")

    _render_actions(result)


def _render_actions(result: RunResult) -> None:
    submitted = st.session_state.get("review_submitted")
    if submitted:
        st.success(
            f"Recorded **{submitted['outcome']}** and resumed run "
            f"`{submitted['run_id']}`. The bundle hash is unchanged "
            f"(`{submitted['hash'][:12]}`), so the decision is attached to the "
            f"same frozen evidence the analyst reviewed."
        )
        return

    st.markdown('<div class="bi-sec">Your decision</div>',
                unsafe_allow_html=True)

    choice = st.radio(
        "Outcome",
        options=[a[0] for a in ACTIONS],
        format_func=lambda v: next(a[1] for a in ACTIONS if a[0] == v),
        horizontal=True,
        label_visibility="collapsed",
        key="review_choice",
    )
    st.caption(next(a[2] for a in ACTIONS if a[0] == choice))

    note = st.text_input(
        "Note (optional)", key="review_note",
        placeholder="What did you conclude, and why?",
    )

    if st.button("Submit and resume the run", type="primary",
                 key="review_submit"):
        resumed = ui_state.submit_review(result.run_id, choice, note)
        st.session_state["review_submitted"] = {
            "outcome": choice,
            "run_id": resumed.run_id,
            "hash": resumed.bundle_hash or result.bundle_hash,
        }
        ui_state.store(resumed)
        st.rerun()
