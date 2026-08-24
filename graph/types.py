"""Graph state, terminal states and per-node telemetry (Architecture Part 12.1).

`InsightState` is a `TypedDict` rather than a Pydantic model, following Part
12.1. The reason is not stylistic: LangGraph merges partial dicts returned by
each node into the accumulated state, and a frozen Pydantic model would have to
be reconstructed on every node return. The *values* remain the project's
existing typed objects — `DetectionResult`, `AttributionResult`,
`EvidenceBundle` and the rest are carried as-is, never re-shaped into graph
specific copies. The graph transports analysis; it does not restate it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, TypedDict

from attribution.types import AttributionResult
from confidence.types import Confidence
from deferral.types import AnalystPacket, DeferralDecision
from detection.types import DetectionResult
from evidence.types import EvidenceBundle, PersonaProfile
from recommendation.types import RecommendationSet
from retrieval.types import RetrievalResult
from security.entitlements import AccessDecision, Principal
from verification.types import Narrative, VerificationReport


class TerminalState(str, Enum):
    """How a run ended. Every run ends in exactly one of these.

    Kept separate from `DeferralOutcome` on purpose: deferral answers "who
    should decide this", the terminal state answers "what did the run do".
    A run can defer to a human *and* end in REVIEW_REQUIRED, but it can also
    stop long before any recommendation exists.
    """

    NO_MATERIAL_EVENT = "NO_MATERIAL_EVENT"
    ACCESS_DENIED = "ACCESS_DENIED"
    ABSTAIN_SPARSE_HISTORY = "ABSTAIN_SPARSE_HISTORY"
    ABSTAIN_INSUFFICIENT_EVIDENCE = "ABSTAIN_INSUFFICIENT_EVIDENCE"
    ABSTAIN_CONFLICTING_EVIDENCE = "ABSTAIN_CONFLICTING_EVIDENCE"
    ABSTAIN_DATA_QUALITY = "ABSTAIN_DATA_QUALITY"
    CLARIFY_REQUESTED = "CLARIFY_REQUESTED"
    VERIFIED_LLM = "VERIFIED_LLM"
    VERIFIED_TEMPLATE = "VERIFIED_TEMPLATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONTRACT_ERROR = "CONTRACT_ERROR"


#: Terminal states in which no narrative was produced.
SILENT_TERMINALS: frozenset[TerminalState] = frozenset({
    TerminalState.NO_MATERIAL_EVENT,
    TerminalState.ACCESS_DENIED,
    TerminalState.ABSTAIN_SPARSE_HISTORY,
    TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE,
    TerminalState.ABSTAIN_CONFLICTING_EVIDENCE,
    TerminalState.ABSTAIN_DATA_QUALITY,
    TerminalState.CLARIFY_REQUESTED,
    TerminalState.CONTRACT_ERROR,
})


@dataclass
class NodeTelemetry:
    """One node execution, recorded while it runs.

    Written by the instrumentation wrapper in `graph/telemetry.py` at the
    moment the node returns, never reconstructed from the final state. A field
    that was not observed stays at its zero value rather than being inferred.
    """

    node: str
    started_at: str
    ended_at: str = ""
    latency_ms: float = 0.0
    ok: bool = True
    error: str = ""

    # model accounting; zero for the deterministic majority of nodes
    model_calls: int = 0
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # what the node concluded
    gate_result: str = ""
    branch_taken: str = ""

    @property
    def cache_hit_rate(self) -> float:
        if not self.input_tokens:
            return 0.0
        return self.cached_input_tokens / self.input_tokens

    def as_dict(self) -> dict[str, Any]:
        return {
            "node": self.node, "started_at": self.started_at,
            "ended_at": self.ended_at, "latency_ms": round(self.latency_ms, 3),
            "ok": self.ok, "error": self.error,
            "model_calls": self.model_calls, "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "gate_result": self.gate_result, "branch_taken": self.branch_taken,
        }


@dataclass
class LineageRecord:
    """One answerable lineage question, recorded by the node that answers it.

    Part 8 of the brief: lineage is accumulated during the run. Rebuilding it
    at the end would mean asserting what the run *would* have done, which is
    a different claim from what it did.
    """

    stage: str
    question: str
    answer: str
    at: str = field(default_factory=lambda: datetime.now().isoformat())

    def as_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "question": self.question,
                "answer": self.answer, "at": self.at}


def _append(left: list | None, right: list | None) -> list:
    """Reducer: nodes append to telemetry and lineage, never overwrite.

    Without this LangGraph would replace the list with whatever the last node
    returned, and the run would end holding one node's telemetry.
    """
    return list(left or []) + list(right or [])


class InsightState(TypedDict, total=False):
    """The complete run. Part 12.1, with the Stage 9 additions."""

    # --- request ---------------------------------------------------------
    run_id: str
    query_text: str
    persona_id: str
    principal: Principal
    persona: PersonaProfile
    scenario_id: str | None

    # --- resolved intent -------------------------------------------------
    kpi_id: str
    window: Any                       # semantic.types.Window
    slice_filter: dict[str, list[str]]
    cause_date: Any                   # date | None
    contract: Any                     # semantic.contract.KPIContract
    access: AccessDecision

    # --- analysis --------------------------------------------------------
    detection: DetectionResult
    attribution: AttributionResult
    counterfactual: Any               # attribution.types.CounterfactualResult
    retrieval: RetrievalResult
    hypotheses: tuple
    bundle: EvidenceBundle

    # --- gates and generation -------------------------------------------
    gate_1: dict
    narrative: Narrative | None
    verification: VerificationReport | None
    narration_attempts: int
    prior_violations: tuple
    model_available: bool

    # --- decision --------------------------------------------------------
    confidence: Confidence
    recommendations: RecommendationSet
    deferral: DeferralDecision
    analyst_packet: AnalystPacket | None
    review_response: dict | None
    feedback: Any

    # --- cross-cutting ---------------------------------------------------
    telemetry: Annotated[list[NodeTelemetry], _append]
    lineage: Annotated[list[LineageRecord], _append]
    terminal: TerminalState | None
    terminal_reason: str
    error: str


def new_state(
    *,
    run_id: str,
    persona_id: str,
    kpi_id: str,
    window: Any,
    query_text: str = "",
    slice_filter: dict[str, list[str]] | None = None,
    cause_date: Any = None,
    scenario_id: str | None = None,
) -> InsightState:
    """A run's starting state. Everything else is filled in by nodes."""
    return {
        "run_id": run_id,
        "query_text": query_text,
        "persona_id": persona_id,
        "kpi_id": kpi_id,
        "window": window,
        "slice_filter": slice_filter or {},
        "cause_date": cause_date,
        "scenario_id": scenario_id,
        "narration_attempts": 0,
        "prior_violations": (),
        "telemetry": [],
        "lineage": [],
        "terminal": None,
        "terminal_reason": "",
        "error": "",
    }


@dataclass
class RunTelemetry:
    """Whole-run aggregates, summed from what the nodes recorded."""

    run_id: str
    nodes: list[NodeTelemetry] = field(default_factory=list)
    wall_ms: float = 0.0

    @property
    def total_node_latency_ms(self) -> float:
        return sum(n.latency_ms for n in self.nodes)

    @property
    def graph_overhead_ms(self) -> float:
        """What the runtime cost beyond the work the nodes did."""
        return max(0.0, self.wall_ms - self.total_node_latency_ms)

    @property
    def llm_calls(self) -> int:
        return sum(n.model_calls for n in self.nodes)

    @property
    def total_input_tokens(self) -> int:
        return sum(n.input_tokens for n in self.nodes)

    @property
    def total_output_tokens(self) -> int:
        return sum(n.output_tokens for n in self.nodes)

    @property
    def estimated_cost_usd(self) -> float:
        return sum(n.estimated_cost_usd for n in self.nodes)

    @property
    def errors(self) -> list[NodeTelemetry]:
        return [n for n in self.nodes if not n.ok]

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "wall_ms": round(self.wall_ms, 3),
            "total_node_latency_ms": round(self.total_node_latency_ms, 3),
            "graph_overhead_ms": round(self.graph_overhead_ms, 3),
            "node_count": len(self.nodes),
            "llm_calls": self.llm_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "error_count": len(self.errors),
            "nodes": [n.as_dict() for n in self.nodes],
        }


@dataclass
class RunResult:
    """One serialisable run, for a UI that does not exist yet.

    Deliberately the only thing `run_insight` returns. A future Streamlit page
    renders this; it does not reach back into the graph, the modules or the
    warehouse (CLAUDE.md rule 6).
    """

    run_id: str
    terminal: TerminalState
    terminal_reason: str
    persona_id: str
    kpi_id: str
    scenario_id: str | None = None

    # Carried even when no bundle exists. A run that abstains at detection
    # still measured something, and the abstention screen has to be able to
    # say *what* — "52 of 56 days" is the difference between a decline the
    # reader can act on and one they can only accept.
    detection: DetectionResult | None = None

    narrative: Narrative | None = None
    verification: VerificationReport | None = None
    confidence: Confidence | None = None
    recommendations: RecommendationSet | None = None
    deferral: DeferralDecision | None = None
    analyst_packet: AnalystPacket | None = None
    bundle: EvidenceBundle | None = None

    telemetry: RunTelemetry | None = None
    lineage: list[LineageRecord] = field(default_factory=list)
    interrupted: bool = False
    thread_id: str = ""

    @property
    def bundle_hash(self) -> str:
        return self.bundle.bundle_hash if self.bundle else ""

    def as_dict(self) -> dict[str, Any]:
        """Serialisable form. Pydantic objects go through `model_dump`."""
        def dump(obj):
            if obj is None:
                return None
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            return obj

        return {
            "run_id": self.run_id,
            "terminal": self.terminal.value,
            "terminal_reason": self.terminal_reason,
            "persona_id": self.persona_id,
            "kpi_id": self.kpi_id,
            "bundle_hash": self.bundle_hash,
            "interrupted": self.interrupted,
            "thread_id": self.thread_id,
            "detection": dump(self.detection),
            "narrative": dump(self.narrative),
            "verification": dump(self.verification),
            "confidence": dump(self.confidence),
            "recommendations": dump(self.recommendations),
            "deferral": dump(self.deferral),
            "analyst_packet": dump(self.analyst_packet),
            "telemetry": self.telemetry.as_dict() if self.telemetry else None,
            "lineage": [l.as_dict() for l in self.lineage],
        }


def now_ms() -> float:
    return time.perf_counter() * 1000.0
