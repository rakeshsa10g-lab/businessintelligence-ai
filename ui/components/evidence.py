"""Level 3 — the sources, with hierarchy rather than a document dump.

Two constraints shape this panel.

The social-proof principle: an excerpt without provenance is a hollow claim. So
every item carries its source type and date, and contradicting evidence is
never quietly dropped — a system that shows only what agrees with it is not
presenting evidence, it is presenting a case.

The entitlement rule (Part 11): withheld material is *counted*, never shown and
never named beyond what policy permits. The count itself is the trust signal —
"2 items withheld" tells an honest story that a silently shorter list does not.
Nothing restricted reaches this module, because retrieval filtered before
ranking; this only reports the count the bundle already carries.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult
from ui import theme


def counts(result: RunResult) -> tuple[int, int, int]:
    bundle = result.bundle
    if bundle is None:
        return 0, 0, 0
    return (
        len(bundle.supporting_evidence or ()),
        len(bundle.contradicting_evidence or ()),
        bundle.security_context.withheld_item_count if bundle.security_context else 0,
    )


def render_summary(result: RunResult) -> None:
    """The one-line evidence posture, for the default screen."""
    support, contra, withheld = counts(result)
    if support == 0 and contra == 0:
        st.markdown(
            f'<div style="font-size:.86rem;color:{theme.INK_FAINT};">'
            f"No corroborating documents were found for this window.</div>",
            unsafe_allow_html=True,
        )
        return

    bits = [f'<span style="color:{theme.SUPPORT};font-weight:650;">'
            f'{support} supporting</span>']
    if contra:
        bits.append(f'<span style="color:{theme.CONTRA};font-weight:650;">'
                    f'{contra} contradicting</span>')
    st.markdown(
        f'<div style="font-size:1rem;">{" · ".join(bits)}</div>',
        unsafe_allow_html=True,
    )
    if withheld:
        render_withheld_notice(result)


def render_withheld_notice(result: RunResult) -> None:
    """Part 11. Safe wording; no restricted content, ever."""
    bundle = result.bundle
    if bundle is None or bundle.security_context is None:
        return
    n = bundle.security_context.withheld_item_count
    if not n:
        return
    st.markdown(
        f"""<div style="border:1px solid #e8dcb8;background:{theme.CAUTION_SOFT};
             border-radius:4px;padding:.55rem .8rem;margin-top:.55rem;
             font-size:.82rem;color:{theme.CAUTION};">
             Some evidence is unavailable for your role. This explanation uses
             only the sources you are authorised to access
             ({n} item{'s' if n != 1 else ''} withheld).
             </div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# P2-02 — a cohort card must carry information, or not exist
# --------------------------------------------------------------------------
def cohort_is_renderable(cohort) -> bool:
    """True when the cohort has something a reader can actually use.

    The first version of this panel read `document_count`, `count`,
    `change_vs_baseline` and `summary` off the cohort via `getattr` defaults.
    None of those are fields on `CohortEvidence` — the real names are
    `incident_count`, `baseline_count`, `ratio` and `label` — so every lookup
    returned the fallback and every card rendered as an empty box with an
    empty meta line and an empty body.

    An empty container is worse than no container: it reads as data that
    failed to load rather than as a cohort that has nothing to say.
    """
    if cohort is None:
        return False
    has_label = bool(getattr(cohort, "label", "") or
                     getattr(cohort, "cohort_id", ""))
    has_count = bool(getattr(cohort, "incident_count", 0))
    return has_label and has_count


def _cohort_card(cohort) -> str:
    """One cohort, rendered from its real fields."""
    label = getattr(cohort, "label", "") or getattr(cohort, "cohort_id", "")
    n = getattr(cohort, "incident_count", 0) or 0
    baseline = getattr(cohort, "baseline_count", None)
    ratio = getattr(cohort, "ratio", None)
    distinct = getattr(cohort, "distinct_accounts", None)
    novel = bool(getattr(cohort, "novel", False))
    weeks = getattr(cohort, "baseline_weeks", None)

    meta = [f"{n} document{'s' if n != 1 else ''} in the event window"]
    if ratio:
        meta.append(f"{ratio:.1f}x the baseline rate")
    if baseline is not None and weeks:
        # `baseline_count` is a per-week average, so it is a float; rendering
        # it raw gives "baseline 0.0", which reads as a broken count rather
        # than as "nothing comparable in the baseline period".
        if baseline == 0:
            meta.append(f"none in the {weeks}-week baseline")
        else:
            meta.append(f"baseline {baseline:,.1f}/week over {weeks} week(s)")
    if distinct:
        meta.append(f"{distinct} distinct account(s)")

    flag = ('<span class="bi-chip bi-chip-caution">New in this window</span>'
            if novel else "")

    return f"""
    <div class="bi-card">
      <div class="bi-card-head">{(label + " " + flag).strip()}</div>
      <div class="bi-card-meta">{' &middot; '.join(meta)}</div>
    </div>
    """


def _item_card(item, stance: str) -> str:
    accent = theme.CONTRA if stance == "contradicting" else theme.SUPPORT
    label = "CONTRADICTS" if stance == "contradicting" else "SUPPORTS"

    when = ""
    if getattr(item, "timestamp", None):
        try:
            when = item.timestamp.strftime("%d %b %Y")
        except Exception:                                 # noqa: BLE001
            when = str(item.timestamp)[:10]

    st = getattr(item, "source_type", "")
    source = (st.value if hasattr(st, "value") else str(st)).replace("_", " ")
    method = getattr(item, "retrieval_method", "") or ""
    dupes = getattr(item, "duplicate_count", 0) or 0

    meta = " · ".join(x for x in [source, when, f"via {method}" if method else ""] if x)
    dupe_note = (f' <span style="color:{theme.INK_FAINT};">'
                 f"(+{dupes} near-identical)</span>" if dupes > 1 else "")

    freshness = getattr(item, "freshness_lag_hours", None)
    fresh_note = ""
    if freshness is not None:
        fresh_note = (f'<div class="bi-card-meta" style="margin-top:.3rem;">'
                      f"Source lag at read time: {freshness:.0f}h</div>")

    return f"""
    <div class="bi-card" style="border-left:3px solid {accent};">
      <div style="font-size:.62rem;font-weight:700;letter-spacing:.1em;
                  color:{accent};margin-bottom:.25rem;">{label}</div>
      <div class="bi-card-head">{getattr(item, 'title', '') or 'Evidence'}{dupe_note}</div>
      <div class="bi-card-meta">{meta}</div>
      <div class="bi-card-body">{getattr(item, 'excerpt', '')}</div>
      {fresh_note}
    </div>
    """


def render_panel(result: RunResult) -> None:
    """The full Evidence tab."""
    bundle = result.bundle
    if bundle is None:
        st.info("No evidence was retrieved: this run stopped before retrieval.")
        return

    support, contra, withheld = counts(result)
    st.markdown('<div class="bi-sec">Evidence posture</div>',
                unsafe_allow_html=True)
    render_summary(result)

    if contra:
        # Contradicting first, deliberately. Evidence against the leading
        # explanation is the thing a reader is most likely to skip and most
        # needs to see.
        st.markdown('<div class="bi-sec">Evidence against</div>',
                    unsafe_allow_html=True)
        for item in bundle.contradicting_evidence:
            st.markdown(_item_card(item, "contradicting"),
                        unsafe_allow_html=True)

    if support:
        st.markdown('<div class="bi-sec">Evidence for</div>',
                    unsafe_allow_html=True)
        for item in bundle.supporting_evidence:
            st.markdown(_item_card(item, "supporting"), unsafe_allow_html=True)

    if not support and not contra:
        st.markdown(
            f'<div style="font-size:.88rem;color:{theme.INK_SOFT};">'
            f"Retrieval ran and returned nothing for this window and slice. "
            f"An empty result is informative: it is why the explanation is "
            f"not corroborated.</div>",
            unsafe_allow_html=True,
        )

    cohorts = [c for c in (bundle.cohorts or ()) if cohort_is_renderable(c)]
    if cohorts:
        st.markdown('<div class="bi-sec">Cohorts</div>', unsafe_allow_html=True)
        for cohort in cohorts:
            st.markdown(_cohort_card(cohort), unsafe_allow_html=True)
