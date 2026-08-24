"""Error boundaries (brief Part 19).

A traceback appeared in the business view during the first walkthrough — a
tuple iterated as a dict. The field name was a one-line fix; relying on having
found every such bug is not a fix at all, which is what this module is for.

Two boundaries, deliberately different:

* `panel()` wraps one section. If a driver chart cannot render, the reader
  still gets the movement, the evidence and the recommendation. Losing a panel
  should not lose the decision.
* `screen()` wraps a whole tab, so a failure inside Method cannot take down
  Workspace.

Both record the technical detail for the Audit view and show the reader a
sentence instead. Streamlit's own `client.showErrorDetails` is *not* what does
this: that setting is global and would also hide errors from the Audit panel,
where they belong.
"""

from __future__ import annotations

import traceback
from contextlib import contextmanager

import streamlit as st

from ui import theme

_ERRORS_KEY = "_ui_errors"


def record(where: str, exc: Exception) -> None:
    errors = st.session_state.setdefault(_ERRORS_KEY, [])
    errors.append({
        "where": where,
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    })


def recorded() -> list[dict]:
    return list(st.session_state.get(_ERRORS_KEY, []))


def clear() -> None:
    st.session_state[_ERRORS_KEY] = []


@contextmanager
def panel(name: str, *, note: str = ""):
    """Guard one section of a screen."""
    try:
        yield
    except Exception as exc:                              # noqa: BLE001
        record(name, exc)
        st.markdown(
            f"""<div style="border:1px solid {theme.RULE};
                 background:{theme.CANVAS_SOFT};border-radius:4px;
                 padding:.7rem .9rem;font-size:.84rem;color:{theme.INK_SOFT};">
                 This section could not be displayed.
                 {note or 'The rest of the analysis is unaffected.'}
                 The technical detail is in the Audit view.
                 </div>""",
            unsafe_allow_html=True,
        )


@contextmanager
def screen(name: str):
    """Guard a whole tab."""
    try:
        yield
    except Exception as exc:                              # noqa: BLE001
        record(name, exc)
        st.markdown(
            f"""<div class="bi-abstain">
                 <div class="bi-abstain-title">This view could not be
                 displayed</div>
                 <div class="bi-abstain-body">
                   Something went wrong while rendering it. No partial result
                   has been presented as a finding, and the other views are
                   unaffected. The technical detail is recorded in the Audit
                   view.
                 </div>
                 </div>""",
            unsafe_allow_html=True,
        )
