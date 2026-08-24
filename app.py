"""BusinessIntelligence.ai — the decision workspace.

Run with:  streamlit run app.py

The primary journey is **What changed → Why → Evidence → Confidence → Action**.

That ordering is the whole point of this file. The system's internal sequence
is Detect → Attribute → Retrieve → Verify → Recommend, and that is the order it
was *built* in — it is not a question anybody asks. Mental-model research is
blunt about the cost of making users learn the builder's structure: they must
spend effort on the system instead of on their decision. So the pipeline order
appears exactly once, in the Method tab, where it is the correct frame.

Four tabs, named for questions rather than modules (Part 13).
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="BusinessIntelligence.ai",
    page_icon="◆",
    layout="centered",
    initial_sidebar_state="expanded",
)

from graph.types import SILENT_TERMINALS, TerminalState  # noqa: E402
from ui import safe  # noqa: E402
from ui import state as ui_state  # noqa: E402
from ui import theme  # noqa: E402
from ui.components import abstention as abstention_view  # noqa: E402
from ui.components import audit as audit_view  # noqa: E402
from ui.components import confidence as confidence_view  # noqa: E402
from ui.components import drivers as drivers_view  # noqa: E402
from ui.components import evidence as evidence_view  # noqa: E402
from ui.components import hypotheses as hypotheses_view  # noqa: E402
from ui.components import method as method_view  # noqa: E402
from ui.components import movement as movement_view  # noqa: E402
from ui.components import progress as progress_view  # noqa: E402
from ui.components import recommendation as recommendation_view  # noqa: E402
from ui.components import review as review_view  # noqa: E402


def sidebar() -> tuple:
    """Scenario and persona selection. No analysis happens in here."""
    with st.sidebar:
        st.markdown("**Demo scenario**")
        st.caption(
            "Scenarios come from the evaluation harness — the same definitions "
            "the test suite runs, not a copy."
        )

        scenarios = ui_state.scenarios()
        options = [s.id for s in scenarios]
        labels = {s.id: f"{s.id} — {s.label}" for s in scenarios}

        chosen_id = st.selectbox(
            "Scenario", options, format_func=lambda i: labels[i],
            key="scenario_id", label_visibility="collapsed",
        )
        scenario = ui_state.scenario_by_id(chosen_id)

        st.markdown("---")
        st.markdown("**Read as**")
        st.caption(
            "The analysis is identical for every role. Only entitlement and "
            "the actions you may take differ."
        )
        people = ui_state.personas()
        persona_ids = list(people)
        default_index = persona_ids.index(scenario.persona_id)
        # Key is scoped to the scenario, not fixed. A Streamlit widget with a
        # fixed key ignores `index=` on every rerun after the first — its
        # value lives in session_state once set, and switching the scenario
        # selectbox above does not touch that state. Without the scoped key,
        # switching from S1 (default meera) to S6 silently kept "meera"
        # selected instead of resetting to S6's own default, priya — which
        # defeats S6's whole purpose: it exists to show CRM evidence withheld
        # for an ops_lead reader, and analytics_lead may not have the same
        # restriction. A judge clicking through the scenario dropdown alone,
        # never touching the persona selector, would never see it withhold
        # anything.
        persona_id = st.selectbox(
            "Persona", persona_ids, index=default_index,
            format_func=lambda p: f"{p.title()} · {people[p][0].replace('_',' ').title()}",
            key=f"persona_pick_{scenario.id}", label_visibility="collapsed",
        )

        run = st.button("Run analysis", type="primary", width='stretch')

        st.markdown("---")
        st.markdown("**Narration**")
        # Filled in by `main()` once a run exists, so the indicator states
        # what THIS run did rather than asserting something about the
        # environment (P2-04).
        status_slot = st.empty()
    return scenario, persona_id, run, status_slot


def masthead(scenario, persona_id: str) -> None:
    role = ui_state.personas()[persona_id][0].replace("_", " ").title()
    st.markdown(
        f"""
        <div class="bi-mast">
          <div class="bi-brand">◆ BusinessIntelligence.ai</div>
          <div class="bi-ctx">{persona_id.title()} · {role} &nbsp;|&nbsp;
               {scenario.id}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workspace_tab(result, scenario) -> None:
    """Level 1 and 2: the decision, then why."""
    if result.terminal in SILENT_TERMINALS:
        # An abstention owns the whole screen. Rendering a half-finding above
        # it would be the thing the materiality gate exists to prevent.
        movement_view.render(result, scenario.slice_label)
        st.markdown("")
        abstention_view.render(result)
        return

    with safe.panel("movement"):
        movement_view.render(result, scenario.slice_label)
        movement_view.render_answer_line(result)

    st.markdown('<div class="bi-sec">Why did it move?</div>',
                unsafe_allow_html=True)
    with safe.panel("drivers"):
        drivers_view.render(result)

    st.markdown('<div class="bi-sec">Evidence</div>', unsafe_allow_html=True)
    with safe.panel("evidence summary"):
        evidence_view.render_summary(result)

    st.markdown('<div class="bi-sec">How reliable is this?</div>',
                unsafe_allow_html=True)
    with safe.panel("reliability"):
        confidence_view.render(result)

    if result.terminal is TerminalState.REVIEW_REQUIRED:
        st.markdown('<div class="bi-sec">Human review</div>',
                    unsafe_allow_html=True)
        with safe.panel("human review"):
            review_view.render(result)
        return

    st.markdown('<div class="bi-sec">Recommended action</div>',
                unsafe_allow_html=True)
    with safe.panel("recommendation"):
        recommendation_view.render(result)

    with st.expander("The explanations the system considered"):
        with safe.panel("hypotheses"):
            hypotheses_view.render(result, compact=False)


def main() -> None:
    ui_state.init()
    st.markdown(theme.css(), unsafe_allow_html=True)

    scenario, persona_id, run, status_slot = sidebar()
    masthead(scenario, persona_id)

    result = ui_state.current()
    # `run_id` is fresh per run now (see ui/state.analyse), so staleness is
    # judged by what was actually asked for, not by reconstructing an id.
    stale = (
        result is not None
        and (result.scenario_id != scenario.id
             or result.persona_id != persona_id)
    )

    if run or result is None or stale:
        progress = progress_view.Progress()
        with st.spinner(""):
            result = ui_state.analyse(scenario, persona_id=persona_id,
                                      progress=progress)
        ui_state.store(result)

    # The narration indicator reports on the run that actually happened.
    with safe.panel("narration status"):
        audit_view.render_narration_status(result, status_slot)

    tabs = st.tabs(["Workspace", "Evidence", "Method", "Audit"])

    with tabs[0]:
        with safe.screen("Workspace"):
            workspace_tab(result, scenario)
    with tabs[1]:
        with safe.screen("Evidence"):
            evidence_view.render_panel(result)
    with tabs[2]:
        with safe.screen("Method"):
            method_view.render(result)
    with tabs[3]:
        with safe.screen("Audit"):
            audit_view.render(result)
            audit_view.render_ui_errors(safe.recorded())


if __name__ == "__main__":
    main()
