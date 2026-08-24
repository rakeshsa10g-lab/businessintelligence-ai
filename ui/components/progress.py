"""The loading experience — labour perception, used honestly.

The Growth.Design study on labour perception bias makes a distinction this
product has to respect. Showing work builds trust *when the work is real*; the
same technique becomes manipulation when the wait is padded or the indicator
jitters to manufacture drama (their example is the 2016 NYT election needle).

A run here genuinely takes 4–55 seconds — STL decomposition, PELT changepoint
search, LMDI, a moving-block bootstrap, and BM25 + dense retrieval over the
corpus. That is real work worth showing. So:

* the stages listed are the stages that actually run,
* nothing is slowed down or delayed to look substantial,
* the labels are business language ("Weighing the evidence"), because Part 18
  says implementation vocabulary belongs in Method and Audit,
* if a run finishes fast because it abstained early, the panel ends early too
  rather than animating through stages that never happened.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult
from ui import theme

#: (node name, business-language label). Ordered as the graph runs them.
STAGES: list[tuple[str, str]] = [
    ("load_contract", "Checking the KPI definition"),
    ("enforce_entitlements", "Applying your access permissions"),
    ("detect", "Measuring the movement"),
    ("attribute", "Working out what drove it"),
    ("retrieve", "Searching for supporting evidence"),
    ("rank_hypotheses", "Weighing the explanations"),
    ("gate_2", "Verifying every stated number"),
    ("defer", "Deciding what should happen next"),
]


class Progress:
    """A live checklist bound to a Streamlit placeholder."""

    def __init__(self, placeholder=None):
        self._slot = placeholder or st.empty()
        self._done: set[str] = set()

    def start(self) -> None:
        self._render(active=STAGES[0][0])

    def finish(self, result: RunResult) -> None:
        """Tick only the stages the run actually reached."""
        ran = {n.node for n in result.telemetry.nodes} if result.telemetry else set()
        self._done = ran
        self._slot.empty()

    def _render(self, active: str | None = None) -> None:
        lines = []
        for node, label in STAGES:
            if node in self._done:
                mark = f'<span class="done">✓</span>'
            elif node == active:
                mark = "…"
            else:
                mark = "&nbsp;"
            lines.append(
                f'<div class="bi-step">{mark}&nbsp;&nbsp;{label}</div>'
            )
        self._slot.markdown(
            f"""<div style="padding:1.6rem 0;">
                 <div style="font-size:.72rem;font-weight:700;
                      letter-spacing:.08em;color:{theme.INK_FAINT};
                      margin-bottom:.7rem;">RUNNING THE ANALYSIS</div>
                 {''.join(lines)}
                 </div>""",
            unsafe_allow_html=True,
        )


def stage_labels() -> list[str]:
    return [label for _node, label in STAGES]
