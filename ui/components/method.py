"""Level 4 — how it was calculated.

This is where the technical work becomes visible without taxing the default
screen. Every value here is read from run metadata rather than hard-coded, so
a method card cannot claim a technique the run did not use — which is the
failure mode that makes a methods panel worse than none.
"""

from __future__ import annotations

import streamlit as st

from graph.types import RunResult
from ui import theme
from ui.components import confidence as conf_view


def _card(title: str, lines: list[str], verdict: str = "",
          verdict_kind: str = "quiet") -> str:
    body = "<br>".join(l for l in lines if l)
    chip = theme.chip(verdict, verdict_kind) if verdict else ""
    return f"""
    <div class="bi-card">
      <div style="display:flex;justify-content:space-between;
                  align-items:flex-start;gap:1rem;">
        <div class="bi-card-head">{title}</div>
        <div>{chip}</div>
      </div>
      <div class="bi-card-body">{body}</div>
    </div>
    """


def render(result: RunResult) -> None:
    bundle = result.bundle
    if bundle is None:
        st.info("This run stopped before the analytical stages.")
        if result.terminal_reason:
            st.caption(result.terminal_reason)
        return

    det = bundle.detection
    att = bundle.attribution

    # ---- detection -----------------------------------------------------
    materiality = getattr(det, "materiality", None)
    passed = bool(getattr(det, "is_material", False))
    st.markdown(
        _card(
            "Detection",
            [
                getattr(det, "method", "") or "—",
                f"Outcome: {det.outcome.value}",
                (f"Coverage: {det.coverage.observations_available} of "
                 f"{det.coverage.observations_required} required observations"
                 if getattr(det, "coverage", None) else ""),
            ],
            "Materiality: pass" if passed else "Materiality: fail",
            "support" if passed else "quiet",
        ),
        unsafe_allow_html=True,
    )

    # ---- attribution ---------------------------------------------------
    if att is not None:
        cf = getattr(att, "counterfactual", None)
        cf_ok = bool(getattr(cf, "passed", False)) if cf else False
        identity = getattr(att, "identity", None)
        closure = getattr(identity, "closure_gap_pct", None) if identity else None
        st.markdown(
            _card(
                "Attribution",
                [
                    getattr(att, "method", "") or "LMDI + Adtributor",
                    (f"Identity closes to {abs(closure):.6f}%"
                     if closure is not None else ""),
                    (f"Causal language: "
                     f"{'licensed' if att.causal_language_licensed else 'not licensed'}"
                     f" — {att.causal_language_reason}"
                     if getattr(att, "causal_language_reason", "") else ""),
                ],
                "Counterfactual: pass" if cf_ok else "Counterfactual: fail",
                "support" if cf_ok else "caution",
            ),
            unsafe_allow_html=True,
        )

    # ---- retrieval -----------------------------------------------------
    support = len(bundle.supporting_evidence or ())
    contra = len(bundle.contradicting_evidence or ())
    methods = {getattr(i, "retrieval_method", "") for i in
               (bundle.supporting_evidence or ())}
    methods.discard("")
    st.markdown(
        _card(
            "Evidence retrieval",
            [
                "BM25 + dense embeddings, fused by reciprocal rank fusion",
                (f"Methods used on returned items: {', '.join(sorted(methods))}"
                 if methods else ""),
                f"{support} supporting, {contra} contradicting",
                "Entitlement filtering runs BEFORE ranking, so restricted "
                "documents never influence the result order.",
            ],
        ),
        unsafe_allow_html=True,
    )

    # ---- verification --------------------------------------------------
    report = result.verification
    if report is not None:
        clean = report.hard_violation_count == 0
        # `checks_run` is the tuple of individual CheckResult objects, not a
        # count — printing it directly dumped raw Python reprs onto the
        # screen, exactly the implementation leak Part 15 warns against even
        # for the technical Method view. What belongs here is the count and,
        # on request, the named checks that actually failed.
        failed = [c.name for c in report.checks_run if not c.passed]
        st.markdown(
            _card(
                "Verification (Gate 2)",
                [
                    f"Ruleset v{report.verification_version}",
                    f"{len(report.checks_run)} deterministic checks run",
                    (f"{report.soft_violation_count} advisory note(s)"
                     if report.soft_violation_count else ""),
                    (f"Failed: {', '.join(failed)}" if failed else ""),
                ],
                (f"{report.hard_violation_count} hard violations"
                 if not clean else "0 hard violations"),
                "support" if clean else "contra",
            ),
            unsafe_allow_html=True,
        )

    # ---- deferral: the exact notation, kept out of the Workspace --------
    decision = result.deferral
    if decision is not None:
        st.markdown(
            _card(
                "Decision rule (cost-sensitive deferral)",
                [
                    f"Policy v{decision.policy_version}",
                    f"<code>{decision.rationale}</code>",
                    (f"p(model correct) = {decision.p_model:.3f} · "
                     f"p(human correct) = {decision.p_human:.3f}"),
                    (f"cost of error {decision.cost_of_error:,.0f} INR · "
                     f"review {decision.review_cost:,.0f} INR"),
                    (f"Guardrail: {decision.override_applied}"
                     if decision.override_applied else ""),
                ],
                decision.outcome.value,
                "support" if decision.outcome.value == "automate" else "quiet",
            ),
            unsafe_allow_html=True,
        )

    if bundle.methods_used:
        st.markdown('<div class="bi-sec">Methods recorded on the bundle</div>',
                    unsafe_allow_html=True)
        st.markdown("\n".join(f"- {m}" for m in bundle.methods_used))

    conf_view.render_detail(result)
