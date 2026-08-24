"""Graph nodes — thin wrappers over the already-tested modules.

Every node here does the same three things: read typed objects off the state,
call one module function, put the typed result back. No node computes a
statistic, ranks anything, decides a threshold or writes a sentence. If a node
in this file starts to contain business logic, the logic is in the wrong place
and the module it belongs to is the one to change.

That constraint is the whole point of Stage 10. LangGraph is the workflow
runtime (CLAUDE.md rule 3); the analytical truth stays in `detection/`,
`attribution/`, `retrieval/`, `evidence/`, `verification/`, `recommendation/`,
`confidence/` and `deferral/`, all of which were tested before this file
existed.
"""

from __future__ import annotations

from datetime import datetime

from attribution import engine as att
from confidence import engine as conf_engine
from deferral import engine as defer_engine
from deferral.types import AbstentionReason, DeferralOutcome
from detection import engine as det
from detection.types import DetectionOutcome
from evidence.bundle import freeze_evidence_bundle, load_persona, principal_for
from graph.routing import MAX_NARRATION_ATTEMPTS, abstention_terminal
from graph.telemetry import instrument, safe_lineage
from graph.types import InsightState, LineageRecord, TerminalState
from llm import client as llm_client
from llm import narrator
from recommendation import engine as rec_engine
from retrieval import engine as ret
from retrieval.types import (
    FilterConditions,
    RetrievalConfig,
    RetrievalQuery,
    RetrievalResult,
)
from security import entitlements
from semantic import registry
from verification import engine as verify_engine


def _runtime(config) -> dict:
    """Runtime handles, which live in `config` and never in graph state.

    The LLM client and the embedding index are connections, not findings. They
    were briefly carried on the state and the checkpoint serialiser rejected
    them, which was the right complaint: a checkpoint is an audit record of
    what a run concluded, and a socket has no place in one. `configurable` is
    passed per invocation and is not persisted, which is exactly the lifetime
    these have.
    """
    return ((config or {}).get("configurable") or {})


def _lineage(stage: str, question: str, answer: str) -> list[LineageRecord]:
    return [LineageRecord(stage=stage, question=question, answer=answer)]


# ==========================================================================
# 1-4  request, contract, entitlement, validation
# ==========================================================================
@instrument("resolve_intent")
def resolve_intent(state: InsightState, config=None) -> dict:
    """Resolve the persona and the request into typed objects.

    Architecture Part 12.3 puts an LLM here to parse free text into a KPI id
    and window. This build resolves an *already structured* request, so no
    model is called: the scenario harness supplies `kpi_id`, `window` and
    `slice_filter` directly. Calling a model to re-derive values it was handed
    would be decoration, and it would put a model upstream of every routing
    decision in the graph.
    """
    persona = load_persona(state["persona_id"])
    principal = principal_for(persona)
    return {
        "persona": persona,
        "principal": principal,
        "_branch": "structured_request",
        "_lineage_fn": lambda: _lineage(
            "intent", "which persona and request?",
            f"persona={persona.persona_id} role={persona.role} "
            f"kpi={state['kpi_id']} window={state['window'].start}"
            f"..{state['window'].end} slice={state.get('slice_filter') or 'ALL'}",
        ),
    }


@instrument("load_contract")
def load_contract(state: InsightState, config=None) -> dict:
    """Load the KPI contract. A missing contract is a config bug, kept loud."""
    kpi_id = state["kpi_id"]
    if kpi_id not in set(registry.all_ids()):
        # An unresolvable request, not a broken system. The two deserve
        # different terminals: one is answered by asking again, the other by
        # fixing a config file.
        return {
            "error": f"unknown_kpi:{kpi_id}",
            "_branch": "unknown_kpi",
            "_gate_result": "unknown_kpi",
        }
    contract = registry.get(kpi_id)
    return {
        "contract": contract,
        "_lineage_fn": lambda: _lineage(
            "contract", "which KPI contract?",
            f"{contract.id} v{contract.version} ({contract.name})",
        ),
    }


@instrument("enforce_entitlements")
def enforce_entitlements(state: InsightState, config=None) -> dict:
    """Resolve row/column/source access before any data is read."""
    access = entitlements.decide(state["principal"], state["contract"])
    return {
        "access": access,
        "_gate_result": access.decision_label,
        "_branch": "allowed" if access.allowed else "denied",
        "_lineage_fn": lambda: _lineage(
            "entitlement", "which entitlement policy?",
            f"policy v{access.policy_version} -> {access.decision_label} "
            f"for role {access.role}; denied_sources="
            f"{access.denied_sources or 'none'}",
        ),
    }


@instrument("access_denied")
def access_denied(state: InsightState, config=None) -> dict:
    """Terminal. Says what was restricted and who can answer instead."""
    access = state.get("access")
    reason = access.reason if access else "no permitted rows"
    return {
        "terminal": TerminalState.ACCESS_DENIED,
        "terminal_reason": (
            f"{reason}. A reader with the required entitlement can run this."
        ),
        "_branch": "terminal",
    }


@instrument("contract_error")
def contract_error(state: InsightState, config=None) -> dict:
    """Terminal. Configuration faults do not degrade into an abstention."""
    return {
        "terminal": TerminalState.CONTRACT_ERROR,
        "terminal_reason": state.get("error") or "contract could not be loaded",
        "_branch": "terminal",
    }


# ==========================================================================
# 5-6  detection and materiality
# ==========================================================================
@instrument("detect")
def detect(state: InsightState, config=None) -> dict:
    """Coverage gate -> STL -> robust z -> PELT -> materiality (Stage 3)."""
    result = det.detect(
        state["kpi_id"], state["window"], state["principal"],
        slice_filter=state.get("slice_filter") or None,
        scenario_id=state.get("scenario_id"),
    )
    return {
        "detection": result,
        "_gate_result": result.outcome.value,
        "_lineage_fn": lambda: _lineage(
            "detection", "which detection method?",
            f"{result.method}; outcome={result.outcome.value}; "
            f"material={result.is_material}",
        ) + _lineage(
            "source", "which source data?",
            (f"{result.lineage.source_table if result.lineage else 'n/a'}; "
             f"columns_masked="
             f"{result.lineage.columns_masked if result.lineage else []}"),
        ),
    }


@instrument("no_material_event")
def no_material_event(state: InsightState, config=None) -> dict:
    det_result = state.get("detection")
    return {
        "terminal": TerminalState.NO_MATERIAL_EVENT,
        "terminal_reason": det_result.explain() if det_result else
                           "no movement cleared the materiality gate",
        "_branch": "terminal",
    }


@instrument("abstain_sparse_history")
def abstain_sparse_history(state: InsightState, config=None) -> dict:
    det_result = state.get("detection")
    return {
        "terminal": TerminalState.ABSTAIN_SPARSE_HISTORY,
        "terminal_reason": det_result.explain() if det_result else
                           "insufficient history for a seasonal baseline",
        "_branch": "terminal",
    }


@instrument("abstain_data_quality")
def abstain_data_quality(state: InsightState, config=None) -> dict:
    det_result = state.get("detection")
    return {
        "terminal": TerminalState.ABSTAIN_DATA_QUALITY,
        "terminal_reason": (
            det_result.coverage.reason if det_result and det_result.coverage
            else state.get("error") or "data quality gate failed"
        ),
        "_branch": "terminal",
    }


# ==========================================================================
# 7-9  attribution, identity, counterfactual
# ==========================================================================
@instrument("attribute")
def attribute(state: InsightState, config=None) -> dict:
    """LMDI identity + Adtributor + robustness + DiD, in one module call.

    Part 12.3 splits this across nodes 7-9. They are one node here because
    `attribution.attribute()` runs them as one unit and returns one typed
    result; splitting it in the graph would mean calling private helpers and
    re-assembling a result the module already assembles. The lineage below
    records all three methods separately, which is what the split was for.
    """
    result = att.attribute(
        state["detection"], state["principal"],
        cause_date=state.get("cause_date"),
        n_resamples=30,
    )
    cf = result.counterfactual
    return {
        "attribution": result,
        "counterfactual": cf,
        "_gate_result": f"causal={'yes' if result.causal_language_licensed else 'no'}",
        "_lineage_fn": lambda: _lineage(
            "attribution", "which attribution method?",
            f"{result.method or 'LMDI identity + Adtributor + bootstrap'}; "
            f"top slice={result.top_slice.element if result.top_slice else 'none'}",
        ) + _lineage(
            "counterfactual", "which counterfactual?",
            (f"difference-in-differences: "
             f"{'PASSED' if cf and cf.passed else 'FAILED'}"
             f"{' - ' + cf.reason if cf else ''}"),
        ),
    }


# ==========================================================================
# 10-11  retrieval and hypotheses
# ==========================================================================
@instrument("retrieve")
def retrieve(state: InsightState, config=None) -> dict:
    """Hybrid BM25 + dense, RRF-fused, entitlement filtered BEFORE ranking."""
    index = _runtime(config).get("__index")
    result = ret.retrieve_evidence(
        state["attribution"], state["principal"], index=index,
    )
    return {
        "retrieval": result,
        "_gate_result": f"{len(result.items)} items",
        "_lineage_fn": lambda: _lineage(
            "retrieval", "which retrieved documents?",
            (f"{len(result.items)} permitted, "
             f"{len(result.withheld)} withheld by entitlement; "
             f"ids={[i.evidence_id for i in result.items][:8]}"),
        ),
    }


@instrument("rank_hypotheses")
def rank_hypotheses(state: InsightState, config=None) -> dict:
    """Rank and freeze. The bundle is immutable from this point on."""
    bundle = freeze_evidence_bundle(
        bundle_id=f"G-{state['run_id']}",
        persona_id=state["persona_id"],
        detection=state["detection"],
        attribution=state["attribution"],
        retrieval=state["retrieval"],
        history_days=_runtime(config).get("__history_days"),
        has_stable_baseline=_runtime(config).get(
            "__has_stable_baseline", True),
    )
    return {
        "bundle": bundle,
        "hypotheses": bundle.hypotheses,
        "_gate_result": f"{len(bundle.hypotheses)} hypotheses",
        "_lineage_fn": lambda: _lineage(
            "bundle", "which EvidenceBundle hash?",
            f"{bundle.bundle_hash} (frozen at {bundle.created_at})",
        ),
    }


@instrument("gate_1")
def gate_1(state: InsightState, config=None) -> dict:
    """Gate 1b — sufficiency, recorded before the routing edge reads it."""
    from graph.routing import route_sufficiency

    from graph.routing import is_ambiguous

    verdict = route_sufficiency(state)
    bundle = state.get("bundle")
    top = bundle.hypotheses[0] if bundle and bundle.hypotheses else None
    return {
        "gate_1": {
            "verdict": verdict,
            "hypothesis_count": len(bundle.hypotheses) if bundle else 0,
            "top_score": round(top.score, 4) if top else 0.0,
            "top_status": top.status.value if top else "none",
            # Recorded, not routed on (ADR-029). The deferral engine decides
            # what an ambiguous pair means; this is the audit record that the
            # graph saw it too.
            "ambiguous": is_ambiguous(bundle),
        },
        "_gate_result": verdict,
        "_branch": verdict,
    }


@instrument("abstain_insufficient_evidence")
def abstain_insufficient_evidence(state: InsightState, config=None) -> dict:
    return {
        "terminal": TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE,
        "terminal_reason": (
            "a movement is real but nothing corroborates an explanation; "
            "naming the missing source would close the gap"
        ),
        "_branch": "terminal",
    }


@instrument("clarify")
def clarify(state: InsightState, config=None) -> dict:
    """The request could not be resolved. Ask, listing what is available.

    Reached when the KPI id is unknown — a question the user can answer.
    A *malformed* contract goes to `contract_error` instead, because that one
    is answered by fixing a file, not by asking again.
    """
    known = ", ".join(sorted(registry.all_ids()))
    asked = str(state.get("error", "")).replace("unknown_kpi:", "")
    return {
        "terminal": TerminalState.CLARIFY_REQUESTED,
        "terminal_reason": (
            f"'{asked}' is not a KPI this system knows. Available: {known}."
        ),
        "_branch": "terminal",
    }


# ==========================================================================
# 13-15  narrate, verify, retry, template
# ==========================================================================
def _narrate(state: InsightState, config, *, retry: bool) -> dict:
    """Shared body for the first attempt and the single retry.

    The retry receives the prior narrative and the typed violations, and the
    *same frozen bundle*. `llm/narrator.py` owns the prompt assembly; this node
    only decides that a retry is happening and counts it.
    """
    bundle = state["bundle"]
    attempts = state.get("narration_attempts", 0)

    if attempts >= MAX_NARRATION_ATTEMPTS:
        # Defence in depth: the router already caps this. If the cap were ever
        # wrong, failing here is better than making a third paid call.
        raise RuntimeError(
            f"narration attempted {attempts} times; the cap is "
            f"{MAX_NARRATION_ATTEMPTS} and a third attempt is not permitted"
        )

    client = _runtime(config).get("__client")
    if client is None:
        # No model configured. Not an error: the deterministic template is a
        # supported delivery path, and pretending otherwise would invent a
        # failure the system does not have.
        return {
            "narrative": None,
            "narration_attempts": attempts + 1,
            # Not a transient failure: there is no model, and a second attempt
            # would call the same absent model. Retrying here would burn a
            # cycle and log a `retry_narrate` that did nothing, which makes the
            # telemetry claim an attempt the system never made.
            "model_available": False,
            "_branch": "no_client",
            "_gate_result": "no_model",
        }

    try:
        narrative, response, _prompt = narrator.generate_narrative(
            bundle, client,
        )
    except Exception as exc:                              # noqa: BLE001
        # A failed generation is an expected condition, not a node fault, and
        # it MUST still spend the attempt.
        #
        # This is the bug that made the cycle unbounded: when the exception
        # escaped to the telemetry wrapper, `narration_attempts` was never
        # incremented, so `route_verification` saw attempts=0 forever and
        # `gate_2 -> retry_narrate -> gate_2` spun until the process died. A
        # retry cap enforced on a counter that failures do not advance is not
        # a cap at all.
        return {
            "narrative": None,
            "narration_attempts": attempts + 1,
            "error": "",
            "_branch": "generation_failed",
            "_gate_result": f"failed:{type(exc).__name__}",
        }
    # LLMResponse carries token counts; the price list lives in
    # config/models.yaml, so cost is arithmetic over configuration rather
    # than a number invented here.
    try:
        cost = llm_client.estimate_cost_usd(
            response.model, response.input_tokens, response.output_tokens,
            response.cached_input_tokens,
        )
    except Exception:                                     # noqa: BLE001
        cost = 0.0
    model_stats = {
        "calls": 1,
        "model_id": response.model or "",
        "input_tokens": response.input_tokens or 0,
        "output_tokens": response.output_tokens or 0,
        "cached_input_tokens": response.cached_input_tokens or 0,
        "estimated_cost_usd": cost,
    }
    return {
        "narrative": narrative,
        "narration_attempts": attempts + 1,
        "_model": model_stats,
        "_branch": "retry" if retry else "first_pass",
        "_gate_result": "generated" if narrative else "unparseable",
        "_lineage_fn": lambda: _lineage(
            "model", "which model?",
            f"{model_stats['model_id']} attempt {attempts + 1}",
        ),
    }


@instrument("narrate")
def narrate(state: InsightState, config=None) -> dict:
    return _narrate(state, config, retry=False)


@instrument("retry_narrate")
def retry_narrate(state: InsightState, config=None) -> dict:
    """The one retry. Carries violations forward; introduces no new evidence."""
    report = state.get("verification")
    violations = tuple(report.violations) if report else ()
    out = _narrate(state, config, retry=True)
    out["prior_violations"] = violations
    return out


@instrument("gate_2")
def gate_2(state: InsightState, config=None) -> dict:
    """Deterministic post-generation verification (Stage 7).

    A run with no narrative fails closed: `verify_narrative` is not asked to
    verify nothing, and the router sends it to the template.
    """
    narrative = state.get("narrative")
    if narrative is None:
        return {
            "verification": None,
            "_gate_result": "no_narrative",
            "_branch": "template",
        }

    report = verify_engine.verify_narrative(
        state["bundle"], narrative, run_id=state["run_id"],
    )
    return {
        "verification": report,
        "_gate_result": (
            f"{'PASS' if report.hard_violation_count == 0 else 'FAIL'} "
            f"({report.hard_violation_count} hard)"
        ),
        "_lineage_fn": lambda: _lineage(
            "verification", "which verification rules?",
            f"Gate 2 v{report.verification_version}: "
            f"{len(report.checks_run)} checks, "
            f"{report.hard_violation_count} hard violations",
        ),
    }


@instrument("deterministic_template")
def deterministic_template(state: InsightState, config=None) -> dict:
    """The guaranteed-faithful fallback. Cannot fail by construction.

    It is still put through Gate 2. A template that could not pass its own
    verifier would be a bug worth failing on, and asserting that it passes is
    cheaper than assuming it.
    """
    bundle = state["bundle"]
    narrative = verify_engine.build_deterministic_narrative(bundle)
    report = verify_engine.verify_narrative(
        bundle, narrative, run_id=state["run_id"],
    )
    return {
        "narrative": narrative,
        "verification": report,
        "_gate_result": (
            f"template {'PASS' if report.hard_violation_count == 0 else 'FAIL'}"
        ),
        "_branch": "template",
        "_lineage_fn": lambda: _lineage(
            "narrative", "which narrator?",
            "deterministic template (no model call)",
        ) + _lineage(
            # The template path skips the narrative branch of `gate_2`, so
            # without this the run would end verified but unable to say by
            # which rules — on the very path that is meant to be the most
            # trustworthy one.
            "verification", "which verification rules?",
            f"Gate 2 v{report.verification_version}: "
            f"{len(report.checks_run)} checks, "
            f"{report.hard_violation_count} hard violations",
        ),
    }


# ==========================================================================
# 16-18  recommend, calibrate, defer
# ==========================================================================
@instrument("calibrate")
def calibrate(state: InsightState, config=None) -> dict:
    """Banded confidence with historical calibration (Stage 9)."""
    confidence = conf_engine.compute(state["bundle"])
    return {
        "confidence": confidence,
        "_gate_result": f"{confidence.band.value} {confidence.score:.2f}",
        "_lineage_fn": lambda: _lineage(
            "confidence", "which calibration?",
            f"band={confidence.band.value} score={confidence.score:.3f}; "
            f"{confidence.calibration.render() if confidence.calibration else 'uncalibrated'}",
        ),
    }


@instrument("recommend")
def recommend(state: InsightState, config=None) -> dict:
    """Levers from the catalogue. The model may never author one."""
    recs = rec_engine.recommend(state["bundle"], state["confidence"])
    primary = recs.primary
    return {
        "recommendations": recs,
        "_gate_result": primary.lever_id if primary else "none",
        "_lineage_fn": lambda: _lineage(
            "recommendation", "which recommendation rule?",
            (f"lever catalogue v{recs.catalogue_version}; "
             f"primary={primary.lever_id if primary else 'none'}; "
             f"impact read from measured movement, not estimated"),
        ),
    }


@instrument("defer")
def defer(state: InsightState, config=None) -> dict:
    """Cost-sensitive deferral. Automate, review, or abstain."""
    decision = defer_engine.decide(
        state["bundle"], state["confidence"], state["recommendations"],
    )
    return {
        "deferral": decision,
        "_gate_result": decision.outcome.value,
        "_branch": decision.outcome.value,
        "_lineage_fn": lambda: _lineage(
            "deferral", "who decided?",
            (f"policy v{decision.policy_version}: {decision.outcome.value}; "
             f"scope={decision.automation_scope.value}; "
             f"E[model]={decision.expected_model_loss:,.0f} vs "
             f"E[human]={decision.expected_human_loss:,.0f} INR"),
        ),
    }


# ==========================================================================
# 19-22  human review, delivery, feedback, logging
# ==========================================================================
@instrument("human_review")
def human_review(state: InsightState, config=None) -> dict:
    """Pause the run and hand a packet to an analyst.

    Uses a real LangGraph `interrupt()`, so the run stops here, the checkpoint
    persists, and resuming continues *this* run rather than starting another.
    The packet is built before the interrupt because it is the payload the
    analyst is shown.
    """
    from langgraph.types import interrupt

    packet = defer_engine.build_analyst_packet(
        state["bundle"], state["confidence"], state["deferral"],
        state["recommendations"],
    )

    response = interrupt({
        "kind": "analyst_review",
        "run_id": state["run_id"],
        "packet_id": packet.packet_id,
        "bundle_hash": packet.bundle_hash,
        "persona_role": packet.persona_role,
        "question": packet.recommended_clarification,
        "confidence": packet.confidence_render,
        "why_you": packet.deferral_rationale,
        "estimated_review_minutes": packet.estimated_review_minutes,
        "options": ["accept", "reject", "correct", "request_clarification"],
    })

    return {
        "analyst_packet": packet,
        "review_response": response,
        "terminal": TerminalState.REVIEW_REQUIRED,
        "terminal_reason": state["deferral"].rationale,
        "_branch": "resumed",
        "_lineage_fn": lambda: _lineage(
            "review", "who reviewed it?",
            f"analyst packet {packet.packet_id}; response="
            f"{(response or {}).get('outcome', 'pending') if isinstance(response, dict) else response}",
        ),
    }


@instrument("deliver")
def deliver(state: InsightState, config=None) -> dict:
    """Terminal for an automated run. Which terminal depends on the narrator."""
    narrative = state.get("narrative")
    # `generated_deterministically` is set by the template builder itself,
    # so this reads the narrative's own claim about its origin rather than
    # inferring it from which node happened to run.
    from_template = bool(
        narrative is None or narrative.generated_deterministically
    )
    terminal = (TerminalState.VERIFIED_TEMPLATE if from_template
                else TerminalState.VERIFIED_LLM)
    decision = state.get("deferral")
    return {
        "terminal": terminal,
        "terminal_reason": decision.rationale if decision else "delivered",
        "_branch": terminal.value,
    }


@instrument("abstain_terminal")
def abstain_terminal(state: InsightState, config=None) -> dict:
    """Deferral said there is nothing for a human to review either."""
    decision = state["deferral"]
    return {
        "terminal": abstention_terminal(decision.abstention_reason),
        "terminal_reason": decision.rationale,
        "_branch": "terminal",
    }


@instrument("log_run")
def log_run(state: InsightState, config=None) -> dict:
    """Close the run. Never blocks delivery (Part 12.3, node 22).

    Everything here is already on the state; this node exists so that the run
    has one exit through which telemetry is finalised, not to compute anything.
    """
    terminal = state.get("terminal")
    return {
        "_gate_result": terminal.value if terminal else "unknown",
        "_lineage_fn": lambda: _lineage(
            "run", "how did it end?",
            f"{terminal.value if terminal else 'unknown'} at "
            f"{datetime.now().isoformat()}",
        ),
    }
