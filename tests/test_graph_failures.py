"""Stage 10 — failure injection (brief Part 11) and end-to-end scenarios.

Every entry in the brief's failure list gets a test that *causes* the failure
rather than asserting the handler exists. The distinction matters: a handler
with no path to it is untested code that reads as coverage.

The end-to-end runs share one session-scoped graph and index, because a single
real scenario costs seconds of detection, embedding and retrieval work that
does not change between assertions.
"""

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from confidence.types import ConfidenceBand
from deferral.types import AutomationScope, DeferralOutcome
from graph.build import compile_graph, make_checkpointer
from graph.routing import MAX_NARRATION_ATTEMPTS
from graph.run import InsightRequest, pending_review, resume_review, run_insight
from graph.types import TerminalState
from llm.client import LLMResponse
from semantic.types import Window

WINDOW = Window(start=date(2026, 1, 1), end=date(2026, 8, 17))
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}


# ==========================================================================
# shared fixtures — one real run is expensive, so it is built once
# ==========================================================================
@pytest.fixture(scope="module")
def index():
    from retrieval.embeddings import load_index
    return load_index()


@pytest.fixture(scope="module")
def graph():
    return compile_graph(in_memory=True)


@pytest.fixture(scope="module")
def s1_result(graph, index):
    """S1: material, high confidence, automates."""
    return run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue", window=WINDOW,
            slice_filter=WEST, cause_date=date(2026, 7, 12),
            scenario_id="S1", run_id="F-S1",
        ),
        graph=graph, index=index, history_days=229,
    )


# ==========================================================================
# fake clients
# ==========================================================================
class _Client:
    """A narrator client that returns whatever it was told to."""

    def __init__(self, payload, *, model="claude-opus-5"):
        self.payload = payload
        self.model = model
        self.calls = 0

    def complete(self, *, system, user, route="narrate", prompt_version="",
                 max_tokens=None):
        self.calls += 1
        text = (self.payload if isinstance(self.payload, str)
                else json.dumps(self.payload))
        return LLMResponse(
            ok=True, text=text, parsed=None, model=self.model,
            model_route=route, prompt_version=prompt_version,
            input_tokens=1200, output_tokens=300, cached_input_tokens=800,
            latency_ms=42.0,
        )


class _ExplodingClient:
    def complete(self, **kw):
        raise RuntimeError("the model API is unreachable")


# ==========================================================================
# 1. missing / unknown contract
# ==========================================================================
def test_unknown_kpi_asks_which_one_rather_than_erroring(graph, index):
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="revenue_per_llama",
                       window=WINDOW, run_id="F-UNKNOWN"),
        graph=graph, index=index,
    )
    assert result.terminal is TerminalState.CLARIFY_REQUESTED
    assert "revenue_per_llama" in result.terminal_reason
    # the remedy is in the message: the real KPI ids
    assert "net_revenue" in result.terminal_reason


def test_a_broken_contract_stays_loud_and_does_not_become_an_abstention(
    graph, index, monkeypatch
):
    """A config fault must not be dressed up as a polite decline."""
    from semantic import registry

    monkeypatch.setattr(registry, "all_ids", lambda: ["net_revenue"])

    def boom(kpi_id):
        raise ValueError("contract yaml is malformed")

    monkeypatch.setattr(registry, "get", boom)
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, run_id="F-BROKEN"),
        graph=graph, index=index,
    )
    assert result.terminal is TerminalState.CONTRACT_ERROR
    assert "malformed" in result.terminal_reason


# ==========================================================================
# 2. authorization denial
# ==========================================================================
def test_authorization_denial_stops_before_any_data_is_read(
    graph, index, monkeypatch
):
    from security import entitlements

    real = entitlements.decide

    def denied(principal, contract):
        d = real(principal, contract)
        return d.model_copy(update={
            "allowed": False,
            "reason": "role has no permitted rows for this KPI",
        })

    monkeypatch.setattr(entitlements, "decide", denied)
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST, run_id="F-DENIED"),
        graph=graph, index=index,
    )
    assert result.terminal is TerminalState.ACCESS_DENIED
    assert "permitted" in result.terminal_reason
    # nothing downstream ran
    nodes = [n.node for n in result.telemetry.nodes]
    assert "detect" not in nodes
    assert result.bundle is None


# ==========================================================================
# 3-4. no material event, sparse history
# ==========================================================================
def test_no_material_event_terminates_with_the_numbers(graph, index):
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter={"channel": ["Marketplace"]},
                       cause_date=date(2026, 6, 14), scenario_id="S7",
                       run_id="F-S7"),
        graph=graph, index=index, history_days=229,
    )
    assert result.terminal is TerminalState.NO_MATERIAL_EVENT
    assert result.terminal_reason
    assert "attribute" not in [n.node for n in result.telemetry.nodes]


def test_sparse_history_is_a_path_not_an_error(graph, index):
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW,
                       slice_filter={"product_category": ["NewLaunch"]},
                       scenario_id="S4", run_id="F-S4"),
        graph=graph, index=index, history_days=23,
        has_stable_baseline=False,
    )
    assert result.terminal is TerminalState.ABSTAIN_SPARSE_HISTORY
    assert all(n.ok for n in result.telemetry.nodes), \
        "sparse history must not be recorded as a node failure"


# ==========================================================================
# 5. retrieval failure
# ==========================================================================
def test_retrieval_failure_does_not_take_down_the_run_silently(
    graph, index, monkeypatch
):
    from retrieval import engine as ret

    def boom(*a, **kw):
        raise ConnectionError("embedding index unavailable")

    monkeypatch.setattr(ret, "retrieve_evidence", boom)
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-RETRIEVAL"),
        graph=graph, index=index, history_days=229,
    )
    # it ends in a typed terminal, and the failure is on the record
    assert result.terminal is not None
    failed = [n for n in result.telemetry.nodes if not n.ok]
    assert failed and failed[0].node == "retrieve"
    assert "ConnectionError" in failed[0].error


# ==========================================================================
# 6-7. insufficient and conflicting evidence
# ==========================================================================
def test_insufficient_evidence_routes_to_its_own_terminal():
    from graph import nodes

    out = nodes.abstain_insufficient_evidence({})
    assert out["terminal"] is TerminalState.ABSTAIN_INSUFFICIENT_EVIDENCE
    assert "corroborates" in out["terminal_reason"]


def test_conflicting_evidence_reaches_review_with_a_packet_not_a_shrug(
    graph, index
):
    """ADR-029's actual purpose, asserted end to end.

    The old Gate 1b abstained here. What the analyst gets instead is a packet
    containing the question.
    """
    result = run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue", window=WINDOW,
            slice_filter={"region": ["South"], "product_category": ["Apparel"]},
            cause_date=date(2026, 6, 2), scenario_id="S2", run_id="F-S2",
        ),
        graph=graph, index=index, history_days=229,
    )
    assert result.terminal is TerminalState.REVIEW_REQUIRED
    assert result.interrupted is True
    assert result.deferral.outcome is DeferralOutcome.REVIEW
    question = pending_review("F-S2", graph=graph)["question"]
    assert "equally supported" in question


# ==========================================================================
# 8-9. malformed and missing LLM
# ==========================================================================
def test_malformed_llm_output_falls_back_without_a_third_call(graph, index):
    client = _Client("this is not json at all")
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-MALFORMED"),
        graph=graph, index=index, client=client, history_days=229,
    )
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE
    assert client.calls <= MAX_NARRATION_ATTEMPTS, \
        f"{client.calls} model calls; the cap is {MAX_NARRATION_ATTEMPTS}"


def test_a_missing_llm_is_a_supported_path_not_a_failure(s1_result):
    """No API key configured. The template is a first-class delivery mode."""
    assert s1_result.terminal is TerminalState.VERIFIED_TEMPLATE
    assert s1_result.telemetry.llm_calls == 0
    assert s1_result.narrative is not None
    assert s1_result.narrative.generated_deterministically is True
    assert s1_result.verification.hard_violation_count == 0


def test_an_api_error_ends_in_the_template_rather_than_an_exception(
    graph, index
):
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-APIERR"),
        graph=graph, index=index, client=_ExplodingClient(),
        history_days=229,
    )
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE
    assert result.narrative is not None


# ==========================================================================
# 10-12. Gate 2 violations, by type
# ==========================================================================
@pytest.mark.parametrize("kind", ["numeric", "driver", "causal"])
def test_gate_2_catches_each_violation_class_and_never_delivers_it(
    graph, index, kind
):
    """A corrupt narrative of each kind must not reach the user.

    The assertion is on the *terminal*: whatever the model said, the run ends
    on the verified template, so the corrupt text is never what is delivered.
    """
    corrupt = {
        "numeric": {
            "headline": "Net revenue fell by 99.9% in the West region.",
            "claims": [{"text": "Revenue fell 99.9%, a loss of 40,000,000 INR.",
                        "claim_type": "OBSERVATION", "evidence_ids": []}],
            "caveats": [],
        },
        "driver": {
            "headline": "Net revenue fell in the West region.",
            "claims": [{"text": "The decline was driven by shipping delays.",
                        "claim_type": "OBSERVATION", "evidence_ids": []}],
            "caveats": [],
        },
        "causal": {
            "headline": "Net revenue fell in the West region.",
            "claims": [{"text": "The gateway outage caused the entire decline.",
                        "claim_type": "CAUSAL", "evidence_ids": []}],
            "caveats": [],
        },
    }[kind]

    client = _Client(corrupt)
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id=f"F-G2-{kind}"),
        graph=graph, index=index, client=client, history_days=229,
    )
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE
    assert result.verification.hard_violation_count == 0, \
        "what is finally delivered must itself be clean"
    assert result.narrative.generated_deterministically is True


# ==========================================================================
# 13-14. retry cap and template fallback
# ==========================================================================
def test_a_persistently_bad_model_is_called_exactly_twice(graph, index):
    """One attempt, one retry, then the template. Never three."""
    client = _Client({
        "headline": "Revenue fell by 12345.6% due to a fabricated cause.",
        "claims": [{"text": "A 99999 INR effect caused by nothing on record.",
                    "claim_type": "CAUSAL", "evidence_ids": []}],
        "caveats": [],
    })
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-RETRYCAP"),
        graph=graph, index=index, client=client, history_days=229,
    )
    assert client.calls == MAX_NARRATION_ATTEMPTS == 2
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE

    path = [n.node for n in result.telemetry.nodes]
    assert path.count("narrate") == 1
    assert path.count("retry_narrate") == 1
    assert path.count("deterministic_template") == 1
    assert path.count("gate_2") == 2


def test_a_narrator_that_raises_every_time_still_terminates(graph, index):
    """Regression: the verify/retry cycle was unbounded when narration raised.

    An exception inside the narrate node escaped to the telemetry wrapper, so
    `narration_attempts` was never incremented; `route_verification` saw
    attempts=0 on every pass and the cycle ran until the process died with an
    access violation. A retry cap enforced on a counter that failures do not
    advance is not a cap.
    """
    client = _ExplodingClient()
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-ALWAYSRAISE"),
        graph=graph, index=index, client=client, history_days=229,
    )
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE
    path = [n.node for n in result.telemetry.nodes]
    assert path.count("gate_2") == 2, f"cycle ran {path.count('gate_2')} times"
    assert path.count("retry_narrate") == 1


def test_the_graph_has_a_recursion_limit_independent_of_the_counter():
    """Defence in depth: a structural bound that no bookkeeping bug can lift."""
    from graph.run import RECURSION_LIMIT, _thread

    assert RECURSION_LIMIT <= 60, "too loose to catch a runaway cycle"
    assert _thread("X")["recursion_limit"] == RECURSION_LIMIT


def test_runtime_handles_never_reach_the_checkpoint(graph, index):
    """A client is a connection, not a finding; audit records hold findings."""
    from graph.run import _thread

    conf = _thread("X", client=object(), index=object())["configurable"]
    non_thread = [k for k in conf if k != "thread_id"]
    assert non_thread, "no runtime keys present to check"
    for key in non_thread:
        assert key.startswith("__"), (
            f"{key} is not excluded from checkpoint metadata; LangGraph only "
            f"skips keys prefixed '__'"
        )


def test_the_template_is_itself_verified_before_delivery(s1_result):
    """A fallback that could not pass its own verifier would be worthless."""
    assert s1_result.verification is not None
    assert s1_result.verification.passed is True
    assert s1_result.verification.hard_violation_count == 0


# ==========================================================================
# 15-16. human interrupt and resume
# ==========================================================================
@pytest.fixture(scope="module")
def paused(tmp_path_factory, index):
    """A genuinely paused run on a real SQLite checkpoint."""
    ckpt = tmp_path_factory.mktemp("ckpt") / "graph.sqlite"
    g = compile_graph(checkpointer=make_checkpointer(ckpt))
    result = run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue", window=WINDOW,
            slice_filter={"region": ["South"], "product_category": ["Apparel"]},
            cause_date=date(2026, 6, 2), scenario_id="S2", run_id="F-PAUSE",
        ),
        graph=g, index=index, history_days=229,
    )
    return g, result


def test_review_pauses_the_run_on_a_real_checkpoint(paused):
    _g, result = paused
    assert result.interrupted is True
    assert result.terminal is TerminalState.REVIEW_REQUIRED
    assert result.bundle is not None, "the paused run kept its evidence"


def test_the_paused_run_exposes_the_analyst_packet(paused):
    g, _result = paused
    payload = pending_review("F-PAUSE", graph=g)
    assert payload["kind"] == "analyst_review"
    assert payload["bundle_hash"]
    assert set(payload["options"]) == {
        "accept", "reject", "correct", "request_clarification"}


@pytest.mark.parametrize("outcome", ["accept", "reject", "correct",
                                     "request_clarification"])
def test_every_analyst_outcome_resumes_the_same_run(tmp_path, index, outcome):
    ckpt = tmp_path / f"g-{outcome}.sqlite"
    g = compile_graph(checkpointer=make_checkpointer(ckpt))
    run_id = f"F-RESUME-{outcome}"
    first = run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue", window=WINDOW,
            slice_filter={"region": ["South"], "product_category": ["Apparel"]},
            cause_date=date(2026, 6, 2), run_id=run_id,
        ),
        graph=g, index=index, history_days=229,
    )
    assert first.interrupted is True

    resumed = resume_review(run_id, {"outcome": outcome}, graph=g)
    assert resumed.interrupted is False
    assert resumed.run_id == first.run_id, "resume must continue the same run"
    assert resumed.bundle_hash == first.bundle_hash, \
        "the frozen bundle must survive the pause unchanged"
    assert resumed.analyst_packet is not None
    assert len(resumed.telemetry.nodes) > len(first.telemetry.nodes)


def test_state_survives_the_checkpoint_round_trip_as_typed_objects(paused):
    """Not `is not None` — the actual class.

    An earlier version of this test asserted only that each key was non-None.
    An unregistered type deserialises to a plain `dict`, which is non-None, so
    the weak assertion passed while `deferral.outcome` was already broken. The
    check has to name the type.
    """
    from attribution.types import AttributionResult
    from confidence.types import Confidence
    from deferral.types import DeferralDecision
    from detection.types import DetectionResult
    from evidence.bundle import verify_hash
    from evidence.types import EvidenceBundle
    from recommendation.types import RecommendationSet
    from retrieval.types import RetrievalResult
    from semantic.contract import KPIContract

    g, _r = paused
    values = g.get_state({"configurable": {"thread_id": "F-PAUSE"}}).values

    expected = {
        "detection": DetectionResult, "attribution": AttributionResult,
        "retrieval": RetrievalResult, "bundle": EvidenceBundle,
        "confidence": Confidence, "recommendations": RecommendationSet,
        "deferral": DeferralDecision, "contract": KPIContract,
    }
    for key, cls in expected.items():
        got = values.get(key)
        assert got is not None, f"{key} lost across the checkpoint"
        assert isinstance(got, cls), (
            f"{key} came back as {type(got).__name__}, not {cls.__name__}; "
            f"its type is not registered with the checkpoint serialiser"
        )

    assert verify_hash(values["bundle"]), "the bundle hash did not survive"


def test_an_unregistered_type_would_be_caught_rather_than_degraded():
    """The allowlist is derived, so it cannot fall behind the type modules."""
    from graph.build import ALLOWED_CHECKPOINT_MODULES, CHECKPOINTED_MODULES

    registered = {(c.__module__, c.__name__) for c in ALLOWED_CHECKPOINT_MODULES}
    assert len(registered) > 50, "the allowlist looks empty or truncated"
    for module in CHECKPOINTED_MODULES:
        assert any(m == module for m, _ in registered),             f"{module} contributed no types"


# ==========================================================================
# 17. telemetry failure must not corrupt the business result
# ==========================================================================
def test_re_invoking_the_same_scenario_does_not_return_a_stale_run(
    tmp_path, index
):
    """Regression: a deterministic run_id silently returned cached results.

    `ui/state.py` used to build `run_id` from scenario+persona alone. The
    checkpointer is durable, and `invoke()` on a thread id that already
    reached a terminal state returns that terminal state rather than
    executing anything — so a second "Run analysis" click, or simply
    re-running after fixing a bug, produced the FIRST run's answer with no
    indication anything was stale. It was found by hand: a fix to a lineage
    string kept failing to show up in a live walkthrough.

    The fix is that `run_id` is fresh per invocation unless the caller
    supplies one explicitly (which tests and eval scripts still do, for
    reproducible fixtures) — so this test drives two runs the way the UI
    does, with no `run_id` set, and asserts they are independent executions.
    """
    from datetime import date

    from graph.build import compile_graph, make_checkpointer
    from graph.run import InsightRequest, run_insight
    from semantic.types import Window

    ckpt = tmp_path / "regression.sqlite"
    g = compile_graph(checkpointer=make_checkpointer(ckpt))
    req = lambda: InsightRequest(                        # noqa: E731
        persona_id="meera", kpi_id="net_revenue",
        window=Window(start=date(2026, 1, 1), end=date(2026, 8, 17)),
        slice_filter={"region": ["West"], "channel": ["Web", "Mobile App"]},
        cause_date=date(2026, 7, 12), scenario_id="S1",
        # deliberately no run_id — this is what the UI does
    )

    first = run_insight(req(), graph=g, index=index, history_days=229)
    second = run_insight(req(), graph=g, index=index, history_days=229)

    assert first.run_id != second.run_id, (
        "two separate analysis requests were assigned the same run id, so "
        "the second one would silently resume the first one's checkpoint"
    )
    assert len(second.telemetry.nodes) > 0,         "the second run executed no nodes at all"
    # Both did real, independent work on identical input. `bundle_hash`
    # deliberately differs — `bundle_id` embeds the run id by design, so a
    # bundle carries which run produced it — but the analysis itself must
    # agree, because nothing about the input changed between the two calls.
    assert first.terminal == second.terminal
    assert first.confidence.score == second.confidence.score
    assert (first.recommendations.primary.lever_id
            == second.recommendations.primary.lever_id)
    assert first.bundle_hash != second.bundle_hash, (
        "identical hashes would mean the second run reused the first "
        "run's bundle rather than freezing its own"
    )


def test_a_lineage_failure_degrades_telemetry_and_keeps_the_analysis(
    graph, index, monkeypatch
):
    """The failure mode this codebase actually hit on first run.

    A renamed field inside a lineage f-string raised, the node was recorded as
    failed, and a perfectly good detection was discarded into an abstention.
    """
    from graph import nodes

    real = nodes._lineage

    def boom(stage, question, answer):
        if stage == "detection":
            raise AttributeError("no attribute 'source_tables'")
        return real(stage, question, answer)

    monkeypatch.setattr(nodes, "_lineage", boom)
    result = run_insight(
        InsightRequest(persona_id="meera", kpi_id="net_revenue",
                       window=WINDOW, slice_filter=WEST,
                       cause_date=date(2026, 7, 12), scenario_id="S1",
                       run_id="F-TELEM"),
        graph=graph, index=index, history_days=229,
    )
    # the analysis completed
    assert result.terminal is TerminalState.VERIFIED_TEMPLATE
    assert result.bundle is not None
    # and the degradation is on the record rather than hidden
    detect_node = [n for n in result.telemetry.nodes if n.node == "detect"][0]
    assert detect_node.ok is True
    assert "lineage degraded" in detect_node.error


def test_telemetry_is_captured_during_the_run_not_reconstructed(s1_result):
    nodes = s1_result.telemetry.nodes
    assert nodes, "no telemetry captured"
    for n in nodes:
        assert n.started_at and n.ended_at
        assert n.latency_ms >= 0.0
    # timestamps are monotonic in execution order
    assert [n.started_at for n in nodes] == sorted(n.started_at for n in nodes)


def test_run_totals_are_sums_of_what_the_nodes_recorded(s1_result):
    t = s1_result.telemetry
    assert t.total_node_latency_ms == pytest.approx(
        sum(n.latency_ms for n in t.nodes), rel=1e-9)
    assert t.wall_ms >= t.total_node_latency_ms
    assert t.graph_overhead_ms >= 0.0


def test_orchestration_is_a_small_fraction_of_runtime(s1_result):
    """LangGraph must not dominate; the claim is measured, not asserted."""
    t = s1_result.telemetry
    assert t.graph_overhead_ms / t.wall_ms < 0.10, (
        f"graph overhead {t.graph_overhead_ms:.0f}ms of {t.wall_ms:.0f}ms"
    )


# ==========================================================================
# lineage
# ==========================================================================
def _find_pandas_timestamps(obj, path="", depth=0, seen=None, hits=None):
    """Walk an object graph collecting paths to any `pandas.Timestamp`."""
    import pandas as pd

    if seen is None:
        seen, hits = set(), []
    if depth > 9 or id(obj) in seen:
        return hits
    seen.add(id(obj))
    if isinstance(obj, pd.Timestamp):
        hits.append(path)
        return hits
    # `type(obj).model_fields`, not `obj.model_fields` — Pydantic 2.11
    # deprecated instance access and emits a warning per field visited, which
    # on a full state walk is several hundred warnings.
    if hasattr(type(obj), "model_fields"):
        for f in type(obj).model_fields:
            _find_pandas_timestamps(getattr(obj, f, None), f"{path}.{f}",
                                    depth + 1, seen, hits)
    elif hasattr(obj, "__dataclass_fields__"):
        for f in obj.__dataclass_fields__:
            _find_pandas_timestamps(getattr(obj, f, None), f"{path}.{f}",
                                    depth + 1, seen, hits)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _find_pandas_timestamps(v, f"{path}[{k!r}]", depth + 1, seen, hits)
    elif isinstance(obj, (list, tuple, set)):
        for i, x in enumerate(list(obj)[:30]):
            _find_pandas_timestamps(x, f"{path}[{i}]", depth + 1, seen, hits)
    return hits


def test_no_pandas_timestamp_can_enter_checkpoint_state(tmp_path, index):
    """P1-01. `pandas.Timestamp` subclasses `datetime`, so Pydantic accepts it.

    The LangGraph checkpointer then refuses to deserialise it —
    `Blocked deserialization of method call pandas.Timestamp.fromisoformat` —
    and silently falls back. Nothing crashes, so it went unnoticed through
    two stages; but the value is rebuilt through an unintended path on every
    restore, and the allowlist blocking it is a security control.

    This scans the WHOLE checkpointed state rather than the fields known to
    have been affected, so a future model that starts carrying a pandas value
    fails here instead of reintroducing the warning.
    """
    from datetime import date

    from graph.build import compile_graph, make_checkpointer
    from graph.run import InsightRequest, run_insight
    from semantic.types import Window

    g = compile_graph(checkpointer=make_checkpointer(tmp_path / "ts.sqlite"))
    run_id = "TS-GUARD"
    run_insight(
        InsightRequest(
            persona_id="meera", kpi_id="net_revenue",
            window=Window(start=date(2026, 1, 1), end=date(2026, 8, 17)),
            slice_filter={"region": ["South"], "product_category": ["Apparel"]},
            cause_date=date(2026, 6, 2), scenario_id="S2", run_id=run_id,
        ),
        graph=g, index=index, history_days=229,
    )

    values = g.get_state({"configurable": {"thread_id": run_id}}).values
    hits = []
    for key, value in values.items():
        hits += _find_pandas_timestamps(value, key)

    assert hits == [], (
        "pandas.Timestamp reached checkpoint state at: "
        + ", ".join(hits[:8])
        + " — annotate the field with semantic.types.PlainDateTime"
    )


def test_the_plain_datetime_normaliser_preserves_the_instant_and_tz():
    """The fix must not quietly change a value while fixing its type."""
    from datetime import datetime, timedelta, timezone

    import pandas as pd

    from semantic.types import _to_plain_datetime

    naive = pd.Timestamp("2026-06-02 14:30:15.123456")
    out = _to_plain_datetime(naive)
    assert type(out) is datetime
    assert out == datetime(2026, 6, 2, 14, 30, 15, 123456)

    tz = timezone(timedelta(hours=5, minutes=30))
    aware = pd.Timestamp("2026-06-02 14:30:15", tz=tz)
    out_aware = _to_plain_datetime(aware)
    assert type(out_aware) is datetime
    assert out_aware.utcoffset() == timedelta(hours=5, minutes=30)
    assert out_aware.timestamp() == aware.timestamp()

    # a plain datetime passes through untouched
    plain = datetime(2026, 1, 1, 12, 0)
    assert _to_plain_datetime(plain) is plain
    # NaT is a Timestamp subclass but is not a usable datetime
    assert _to_plain_datetime(pd.NaT) is None


def test_evidence_timestamps_are_plain_datetimes_not_pandas(s1_result):
    """The specific field P1-01 was found on, asserted on a real run."""
    from datetime import datetime

    import pandas as pd

    items = list(s1_result.bundle.supporting_evidence or ()) +         list(s1_result.bundle.contradicting_evidence or ())
    assert items, "S1 should retrieve evidence"
    for item in items:
        assert not isinstance(item.timestamp, pd.Timestamp), item.evidence_id
        assert type(item.timestamp) is datetime, item.evidence_id


def test_lineage_never_carries_a_raw_python_repr(s1_result):
    """Regression: `checks_run` is `tuple[CheckResult, ...]`, not a count.

    Two lineage sites in `graph/nodes.py` interpolated it directly into an
    f-string, which is valid Python and produces `(CheckResult(name=...),
    CheckResult(name=...), ...)` — a repr of ten dataclass instances sitting
    inside what is supposed to be a one-line audit answer. Nothing caught it
    because every existing test asserted a lineage entry *existed* for
    "verification", never what it said.
    """
    for record in s1_result.lineage:
        assert "CheckResult(" not in record.answer, (
            f"{record.stage}: raw repr leaked into the lineage answer: "
            f"{record.answer[:120]}"
        )
        assert not re.search(r"[A-Z]\w*\(name=", record.answer), (
            f"{record.stage}: looks like a dataclass repr: {record.answer[:120]}"
        )


def test_lineage_answers_every_question_the_brief_lists(s1_result):
    stages = {r.stage for r in s1_result.lineage}
    for required in ("contract", "source", "entitlement", "detection",
                     "attribution", "counterfactual", "retrieval", "bundle",
                     "verification", "recommendation", "confidence"):
        assert required in stages, f"lineage cannot answer '{required}'"


def test_lineage_is_accumulated_not_rebuilt_at_the_end(s1_result):
    """Records carry the timestamp of the node that wrote them."""
    times = [r.at for r in s1_result.lineage]
    assert len(set(times)) > 1, \
        "identical timestamps mean lineage was rebuilt in one pass"


def test_the_bundle_hash_appears_in_lineage(s1_result):
    bundle_line = [r for r in s1_result.lineage if r.stage == "bundle"][0]
    assert s1_result.bundle_hash in bundle_line.answer


# ==========================================================================
# the serialisable result the future UI consumes
# ==========================================================================
def test_the_run_result_serialises_without_reaching_back_into_the_graph(
    s1_result
):
    payload = s1_result.as_dict()
    text = json.dumps(payload)          # must not raise
    assert payload["terminal"] == "VERIFIED_TEMPLATE"
    assert payload["bundle_hash"]
    assert payload["telemetry"]["node_count"] > 0
    assert len(payload["lineage"]) > 0
    assert len(text) > 500
