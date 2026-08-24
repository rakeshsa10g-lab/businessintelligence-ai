"""Conditional routing (Architecture Part 12.4, brief Part 3).

Every predicate here is a pure function of deterministic state. None of them
reads a narrative, a model response, or anything a model produced. That is the
architecture's central claim stated as code rather than as prose: the model
writes, the system decides.

The one place a model's *output* is consulted at all is `route_verification`,
and it consults the deterministic verifier's verdict on that output — a count
of typed violations produced by `verification/`, not the text itself.
"""

from __future__ import annotations

from deferral.types import AbstentionReason, DeferralOutcome
from detection.types import DetectionOutcome
from evidence.types import HypothesisStatus
from graph.types import InsightState, TerminalState

#: Hard cap on model calls per run. Two attempts = one retry (brief Part 5).
MAX_NARRATION_ATTEMPTS = 2


def route_access(state: InsightState) -> str:
    """Entitlement is a boundary: denied runs stop before any analysis."""
    if state.get("error"):
        return "error"
    access = state.get("access")
    if access is not None and not access.allowed:
        return "denied"
    return "allowed"


def route_contract(state: InsightState) -> str:
    """Three answers, because two different faults hide under "no contract".

    An unknown KPI id is a question the user can answer, so it routes to
    `clarify` with the list of real ones. A contract that exists but will not
    load is a configuration bug and must stay loud (Part 12.3) — degrading it
    into a polite clarification would hide a broken deployment behind a
    conversational message.
    """
    error = str(state.get("error") or "")
    if error.startswith("unknown_kpi:"):
        return "clarify"
    if error or state.get("contract") is None:
        return "error"
    return "ok"


def route_materiality(state: InsightState) -> str:
    """Detection's own verdict decides this; the graph does not re-judge it.

    Three of detection's four outcomes are terminal here. Re-deriving
    materiality from `pct_delta` would be a second implementation of a rule
    that `detection/` already owns, and the two would drift.
    """
    if state.get("error"):
        return "error"
    det = state.get("detection")
    if det is None:
        return "error"
    if det.outcome is DetectionOutcome.SPARSE_HISTORY:
        return "sparse"
    if det.outcome is DetectionOutcome.INSUFFICIENT_DATA:
        return "insufficient_data"
    if det.outcome is DetectionOutcome.NO_MATERIAL_FINDING or not det.is_material:
        return "not_material"
    return "material"


#: Ambiguity margin. Retained for the record on `gate_1`, no longer a terminal.
AMBIGUITY_MARGIN = 0.08


def is_ambiguous(bundle) -> bool:
    """Two top hypotheses close enough to matter, with different owners."""
    if bundle is None or len(bundle.hypotheses) < 2:
        return False
    top, second = bundle.hypotheses[0], bundle.hypotheses[1]
    return (abs(top.score - second.score) < AMBIGUITY_MARGIN
            and top.cause_bucket != second.cause_bucket)


def route_sufficiency(state: InsightState) -> str:
    """Gate 1b. Is there enough here to write about at all? (ADR-029)

    Only two answers. Architecture Part 12.4 had a third, `clarify`, taken
    when the top two hypotheses were within 0.08 with different cause buckets.
    That branch is gone, and the reason is a measured one: on S2 it fired
    (margin 0.0768) and ended the run with a bare abstention, while the
    deferral engine — reached only if the run continues — classifies the very
    same state as `conflicting_evidence`, routes it to review, and builds an
    analyst packet whose question is *"Two explanations are equally supported
    and imply different owners. Which is it?"*.

    Two mechanisms were making one judgement and the cruder one fired first,
    discarding the packet that asked the question the abstention wanted asked.

    So the split is by kind: **can anything be written** is a generation
    question and belongs here; **who resolves a tie** is a decision question
    and belongs to `deferral/`, which already owns it and does it better.
    Ambiguity is still recorded on `gate_1` for the audit trail.
    """
    if state.get("error"):
        return "error"
    bundle = state.get("bundle")
    if bundle is None or not bundle.hypotheses:
        return "insufficient"

    if bundle.hypotheses[0].status is HypothesisStatus.INSUFFICIENT:
        return "insufficient"

    return "narrate"


def route_verification(state: InsightState) -> str:
    """Gate 2. Pass, retry once, then the template — never a third attempt.

    The cap is read from state rather than from a counter held by the node, so
    a resumed run cannot get a fresh budget by restarting mid-cycle.
    """
    if state.get("model_available") is False:
        # No narrator configured at all. The template is not a fallback here,
        # it is the only path, and pretending to retry would be theatre.
        return "template"

    report = state.get("verification")
    if report is None:
        # Nothing to verify: generation failed, or returned something that
        # would not parse. Architecture Part 12.3 gives this the same single
        # retry as a violation — an unparseable response is the commonest
        # transient model failure, and spending the retry the run is already
        # budgeted for is what the budget is for. The cap below still applies,
        # so this cannot loop.
        if state.get("narration_attempts", 0) < MAX_NARRATION_ATTEMPTS:
            return "retry"
        return "template"

    if report.hard_violation_count == 0:
        return "pass"

    if state.get("narration_attempts", 0) < MAX_NARRATION_ATTEMPTS:
        return "retry"

    return "template"


def route_deferral(state: InsightState) -> str:
    """Who takes this decision. The arithmetic already ran; this reads it."""
    if state.get("error"):
        return "error"
    decision = state.get("deferral")
    if decision is None:
        return "error"
    if decision.outcome is DeferralOutcome.ABSTAIN:
        return "abstain"
    if decision.outcome is DeferralOutcome.REVIEW:
        return "review"
    return "deliver"


def abstention_terminal(reason: AbstentionReason) -> TerminalState:
    """Map a typed abstention onto a typed terminal state.

    A dict rather than a chain of ifs, so an abstention reason that gains no
    terminal mapping fails visibly at the lookup instead of quietly landing in
    a generic bucket.
    """
    return {
        AbstentionReason.NO_MATERIAL_EVENT: TerminalState.NO_MATERIAL_EVENT,
        AbstentionReason.SPARSE_HISTORY: TerminalState.ABSTAIN_SPARSE_HISTORY,
        AbstentionReason.EVIDENCE_INSUFFICIENCY:
            TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE,
        AbstentionReason.CONFLICTING_EVIDENCE:
            TerminalState.ABSTAIN_CONFLICTING_EVIDENCE,
        AbstentionReason.UNAUTHORIZED_INFORMATION: TerminalState.ACCESS_DENIED,
        AbstentionReason.UNSUPPORTED_CAUSAL_CLAIM:
            TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE,
        AbstentionReason.MULTI_DIMENSIONAL:
            TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE,
    }.get(reason, TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE)


#: Every predicate, for the introspection test that asserts each branch is
#: reachable and that none of them touches a narrative.
PREDICATES = {
    "route_access": route_access,
    "route_contract": route_contract,
    "route_materiality": route_materiality,
    "route_sufficiency": route_sufficiency,
    "route_verification": route_verification,
    "route_deferral": route_deferral,
}
