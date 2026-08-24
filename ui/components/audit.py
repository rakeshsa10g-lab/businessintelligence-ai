"""Level 5 — audit, lineage and telemetry.

The distinction Part 17 insists on is the one this panel exists to keep:

* **LLM not required** — the run reached a terminal state that never needed a
  narrative (an abstention, a non-material finding).
* **LLM unavailable** — a narrator was wanted and none was configured, so the
  deterministic template produced the wording.

They look identical if you only count model calls, and conflating them would
let a template-mode run read as though a model had approved it. Every run in
this build is one or the other, and the panel says which.
"""

from __future__ import annotations

import streamlit as st

from graph.types import SILENT_TERMINALS, RunResult, TerminalState
from ui import theme


def narration_mode(result: RunResult) -> tuple[str, str, str]:
    """(label, chip kind, explanation). Never implies a model that did not run."""
    calls = result.telemetry.llm_calls if result.telemetry else 0

    if calls > 0:
        model = next((n.model_id for n in result.telemetry.nodes
                      if n.model_id), "the configured model")
        return ("Model-generated, verified", "support",
                f"{calls} model call(s) to {model}. The wording was generated "
                f"and then passed Gate 2.")

    if result.terminal in SILENT_TERMINALS:
        return ("LLM not required", "quiet",
                "This run ended without producing a narrative, so no model was "
                "needed. Nothing was suppressed.")

    return ("Verified template mode", "caution",
            "No ANTHROPIC_API_KEY is configured, so the wording came from the "
            "deterministic template rather than a model. The analysis, the "
            "numbers and the decision are identical either way — only the "
            "sentence construction differs. No model reviewed this text.")



def render_narration_status(result: RunResult, container=None) -> None:
    """A restrained status indicator for how the wording was produced.

    P2-04. This used to be a static sidebar caption asserting that no
    ANTHROPIC_API_KEY was configured — low-contrast grey, easy to miss, and
    worse, a claim about the environment rather than about the run. If a key
    were configured it would still have said the opposite of the truth.

    It now reads the same `narration_mode()` the Audit tab uses, so the three
    states stay in lockstep and a live model run relabels itself with no
    separate code path. Rendered as a chip in the existing palette: visible,
    but not competing with the decision.
    """
    target = container if container is not None else st
    label, kind, explanation = narration_mode(result)

    target.markdown(
        f'<div style="margin:.2rem 0 .35rem 0;">{theme.chip(label, kind)}</div>',
        unsafe_allow_html=True,
    )
    target.markdown(
        f'<div style="font-size:.75rem;color:{theme.INK_SOFT};'
        f'line-height:1.5;">{explanation}</div>',
        unsafe_allow_html=True,
    )


def render_telemetry(result: RunResult) -> None:
    t = result.telemetry
    if t is None:
        return

    label, kind, explanation = narration_mode(result)

    st.markdown('<div class="bi-sec">Narration mode</div>',
                unsafe_allow_html=True)
    st.markdown(theme.chip(label, kind), unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:.83rem;color:{theme.INK_SOFT};'
        f'margin-top:.4rem;line-height:1.6;">{explanation}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bi-sec">Run cost</div>', unsafe_allow_html=True)

    by_node = {n.node: n.latency_ms for n in t.nodes}
    retrieval_ms = by_node.get("retrieve", 0.0)
    deterministic_ms = t.total_node_latency_ms - retrieval_ms

    c1, c2, c3 = st.columns(3)
    c1.metric("Total runtime", f"{t.wall_ms / 1000:.1f} s")
    c2.metric("Evidence retrieval", f"{retrieval_ms / 1000:.1f} s")
    c3.metric("Orchestration overhead", f"{t.graph_overhead_ms:.0f} ms")

    c4, c5, c6 = st.columns(3)
    c4.metric("Deterministic analysis", f"{deterministic_ms / 1000:.1f} s")
    c5.metric("Model calls", str(t.llm_calls))
    c6.metric("Estimated cost", f"${t.estimated_cost_usd:.4f}"
              if t.estimated_cost_usd else "$0.0000")

    retries = max(0, sum(1 for n in t.nodes if n.node == "retry_narrate"))
    c7, c8, c9 = st.columns(3)
    c7.metric("Input tokens", f"{t.total_input_tokens:,}")
    c8.metric("Output tokens", f"{t.total_output_tokens:,}")
    c9.metric("Narration retries", str(retries))

    st.markdown('<div class="bi-sec">Node timings</div>', unsafe_allow_html=True)
    rows = ["| Node | ms | Result | Branch |", "|---|---|---|---|"]
    for n in t.nodes:
        status = n.gate_result or ("ok" if n.ok else "ERROR")
        rows.append(f"| `{n.node}` | {n.latency_ms:,.1f} | {status} | "
                    f"{n.branch_taken or '—'} |")
    st.markdown("\n".join(rows))

    degraded = [n for n in t.nodes if n.error]
    if degraded:
        st.markdown('<div class="bi-sec">Diagnostics</div>',
                    unsafe_allow_html=True)
        st.caption(
            "Technical detail is exposed here and nowhere else in the product."
        )
        for n in degraded:
            st.code(f"{n.node}: {n.error}", language=None)


def render(result: RunResult) -> None:
    bundle = result.bundle

    st.markdown('<div class="bi-sec">Run</div>', unsafe_allow_html=True)
    rows = [
        theme.kv("Run ID", result.run_id),
        theme.kv("Terminal state", result.terminal.value),
        # The raw detector/gate string. It lives here and not on the
        # Workspace (P2-03): it names internal gates and enum values, which
        # Part 19 confines to the technical views.
        theme.kv("Terminal reason (raw)", result.terminal_reason or "-"),
        theme.kv("Persona", result.persona_id),
        theme.kv("KPI", result.kpi_id),
    ]
    if bundle is not None:
        sec = bundle.security_context
        rows += [
            theme.kv("EvidenceBundle hash", result.bundle_hash or "—"),
            theme.kv("Bundle frozen at", str(bundle.created_at)),
            theme.kv("Scoring version", bundle.scoring_version or "—"),
        ]
        if sec is not None:
            rows += [
                theme.kv("Entitlement policy", f"v{sec.policy_version}"),
                theme.kv("Role", sec.role),
                theme.kv("Permitted sources", ", ".join(sec.permitted_sources) or "—"),
                theme.kv("Withheld by entitlement",
                         f"{sec.withheld_item_count} item(s)"),
            ]
        for name, version in (bundle.config_versions or ()):
            rows.append(theme.kv(f"Config · {name}", str(version)))

    st.markdown("".join(rows), unsafe_allow_html=True)

    st.markdown('<div class="bi-sec">Graph path</div>', unsafe_allow_html=True)
    path = " → ".join(n.node for n in result.telemetry.nodes) if result.telemetry else "—"
    st.markdown(
        f'<div style="font-family:ui-monospace,Menlo,Consolas,monospace;'
        f'font-size:.74rem;color:{theme.INK_SOFT};line-height:1.9;'
        f'word-break:break-word;">{path}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bi-sec">Lineage</div>', unsafe_allow_html=True)
    if result.lineage:
        st.caption(
            "Accumulated during the run by the node that answered each "
            "question — not reconstructed afterwards."
        )
        for record in result.lineage:
            st.markdown(
                theme.kv(f"{record.stage} · {record.question}", record.answer),
                unsafe_allow_html=True,
            )
    else:
        st.caption("No lineage was recorded for this run.")

    render_telemetry(result)


def render_ui_errors(errors: list[dict]) -> None:
    """Rendering faults, shown here and nowhere else (Part 19)."""
    if not errors:
        return
    st.markdown('<div class="bi-sec">Interface diagnostics</div>',
                unsafe_allow_html=True)
    st.caption(
        f"{len(errors)} panel(s) failed to render this session. The business "
        f"views showed a message instead of a traceback."
    )
    for err in errors:
        with st.expander(f"{err['where']} — {err['type']}"):
            st.code(err["traceback"], language=None)
