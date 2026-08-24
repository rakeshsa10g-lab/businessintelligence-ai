"""What should happen next — and precisely how far the system may go.

The Amber Alert study calls an alert without a next step an *actionability
gap*: information that leaves the recipient helpless. Every terminal state in
this product therefore ends in a named next step, including the abstentions.

The framing-effect constraint governs the money. Expected impact is a *range*
derived from a configured recovery fraction applied to the movement detection
measured. Rendering its midpoint as a single figure would claim a precision
that does not exist; rendering only its top would be selling the action. It is
always a range, always with its basis named.

The scope distinction from ADR-026 is the other thing this must not blur.
`automate` for `L_GATEWAY_ESCALATE` means the *request* is raised
automatically. It does not mean a rollback is performed, and the UI says so in
words rather than leaving the reader to assume.
"""

from __future__ import annotations

import streamlit as st

from deferral.types import AutomationScope, DeferralOutcome
from graph.types import RunResult
from ui import theme

SCOPE_SENTENCE = {
    AutomationScope.RAISE_REQUEST: (
        "The system can raise this request automatically. It will not perform "
        "the technical fix — that stays with the owning team."
    ),
    AutomationScope.EXECUTE: (
        "You hold approval rights on this action, so it can be taken directly."
    ),
    AutomationScope.NONE: (
        "Nothing is automated here; the decision stays with a person."
    ),
}



# --------------------------------------------------------------------------
# P2-01 — business language on the Workspace, notation in Method/Audit
# --------------------------------------------------------------------------
def _why_heading(decision) -> str:
    if decision.outcome is DeferralOutcome.AUTOMATE:
        return "Why the system is acting on this rather than asking you"
    if decision.outcome is DeferralOutcome.REVIEW:
        return "Why this is coming to you rather than being actioned"
    return "Why the system is not offering an action"


def business_rationale(decision) -> str:
    """The deferral decision in plain business terms.

    `decision.rationale` is written for an audit trail and reads
    `E[loss|model] 53,571 < E[loss|human]+review 128,250 INR`. That notation
    is exact and it belongs in Method/Audit; on the decision screen it asks a
    business reader to parse conditional-expectation syntax before they can
    tell whether the system is acting or asking.

    Nothing is recomputed here — the same figures the arithmetic produced are
    restated as money and consequence rather than as an inequality.
    """
    model = decision.expected_model_loss
    human = decision.expected_human_loss
    review = decision.review_cost

    if decision.override_applied:
        # A guardrail fired, so the arithmetic was not what decided it.
        return (
            f"This was decided by policy rather than by cost: "
            f"{decision.override_applied}"
        )

    if decision.outcome is DeferralOutcome.AUTOMATE:
        saved = human - model
        para_one = (
            f"**Acting now carries less risk than waiting.** Sending this for "
            f"manual review would cost about **{review:,.0f} INR** in analyst "
            f"time and delay — more than the review would be expected to save "
            f"by catching a wrong call."
        )
        para_two = (
            f"Weighing the chance of being wrong against what being wrong "
            f"would cost: acting now is worth about **{model:,.0f} INR** of "
            f"expected risk, against **{human:,.0f} INR** if this waited for a "
            f"person — a difference of roughly **{saved:,.0f} INR** in favour "
            f"of acting."
        )
        return para_one + "\n\n" + para_two

    if decision.outcome is DeferralOutcome.REVIEW:
        return (
            f"**A person should decide this one.** The expected cost of "
            f"getting it wrong unaided (**{model:,.0f} INR**) outweighs the "
            f"**{review:,.0f} INR** that review costs in time and delay, so "
            f"the review pays for itself here."
        )

    return (
        "The system does not have enough to offer an action, so it is not "
        "guessing at one."
    )


def render(result: RunResult) -> None:
    recs = result.recommendations
    decision = result.deferral
    primary = recs.primary if recs else None

    if primary is None:
        st.markdown(
            f'<div style="font-size:.88rem;color:{theme.INK_SOFT};">'
            f"No action is recommended for this finding.</div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        theme.claim(f"<b>{primary.lever_name}</b>", "recommendation"),
        unsafe_allow_html=True,
    )

    owner = (primary.owner_role or "").replace("_", " ").title()
    right = (primary.persona_right.value if primary.persona_right else "none")

    st.markdown(
        f"""
        <div style="font-size:.85rem;color:{theme.INK_SOFT};line-height:1.75;
                    margin:.5rem 0 .2rem 0;">
          <b>Owner</b> · {owner}<br>
          <b>Your authority</b> · you may {right} this action<br>
          <b>Monitor</b> · {primary.monitoring.render() if primary.monitoring else '—'}
        </div>
        """,
        unsafe_allow_html=True,
    )

    impact = primary.expected_impact
    if impact is not None and getattr(impact, "low", None) is not None:
        st.markdown(
            f"""
            <div style="border:1px solid {theme.RULE};border-radius:5px;
                        padding:.7rem .9rem;margin:.6rem 0;
                        background:{theme.CANVAS_SOFT};">
              <div style="font-size:.72rem;color:{theme.INK_FAINT};
                          letter-spacing:.06em;font-weight:700;">
                EXPECTED RECOVERY IF ACTED ON
              </div>
              <div style="font-size:1.15rem;font-weight:650;margin-top:.15rem;">
                {impact.low:,.0f} – {impact.high:,.0f} INR
              </div>
              <div style="font-size:.75rem;color:{theme.INK_FAINT};
                          margin-top:.25rem;">
                A range, not a point estimate: it applies a configured recovery
                fraction to the movement detection measured. The system does not
                estimate this figure — it reads it.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if decision is None:
        return

    scope_note = SCOPE_SENTENCE.get(decision.automation_scope, "")

    if decision.outcome is DeferralOutcome.AUTOMATE:
        st.markdown(
            f'<div style="font-size:.82rem;color:{theme.INK_SOFT};'
            f'margin:.4rem 0 .6rem 0;">{scope_note}</div>',
            unsafe_allow_html=True,
        )
        verb = ("Raise the request"
                if decision.automation_scope is AutomationScope.RAISE_REQUEST
                else "Take this action")
        clicked = st.button(verb, type="primary", key="primary_action")
        if clicked:
            st.success(
                f"{verb} — recorded against bundle "
                f"{result.bundle_hash[:12]}. In this prototype no external "
                f"system is contacted; the action and its authority are logged."
            )

    with st.expander(_why_heading(decision)):
        st.markdown(business_rationale(decision))
        st.caption(
            "The full expected-loss calculation, including the notation and "
            "the policy version behind it, is in the Method tab."
        )
