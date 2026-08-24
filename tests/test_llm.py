"""Stage 8 tests — the constrained narrator.

Every test here runs against a `ScriptedClient`. That is deliberate and not a
compromise: the behaviour under test is the *loop* — generate, verify, retry
once, fall back — and a scripted client lets a test assert what happens when a
model returns a lie, times out, or emits malformed JSON. Those are exactly the
cases a live model will not produce on demand.

The invariants asserted from the recorded requests are the load-bearing ones:
the narrator is never given tools, the retry is never given new evidence, and a
structurally abstaining bundle never reaches the model at all.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from evidence.types import HypothesisStatus
from llm import payload as payload_mod
from llm.client import (
    AnthropicClient,
    FailureReason,
    LLMResponse,
    ScriptedClient,
    estimate_cost_usd,
    extract_json,
    failing,
    load_config,
    model_for,
    scripted_json,
)
from llm.narrator import (
    DeliveryMode,
    NarrationError,
    deliver_insight,
    is_structural_abstention,
    load_prompt,
    parse_narrative,
)
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window
from verification.types import ViolationCode

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}
SOUTH = {"region": ["South"], "product_category": ["Apparel"]}
EAST = {"region": ["East"], "segment": ["SMB"]}

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
OPS_LEAD = Principal(
    user_id="priya", display_name="Priya Nair", role="ops_lead",
    user_region="West",
)


@pytest.fixture(scope="module")
def index():
    return load_index()


def _bundle(slice_filter, principal, persona, cause_date, index, scenario, **kw):
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=20)
    r = ret.retrieve_evidence(a, principal, index=index)
    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario}", persona_id=persona,
        detection=d, attribution=a, retrieval=r, **kw
    )


@pytest.fixture(scope="module")
def s1(index):
    return _bundle(WEST, ANALYST, "meera", date(2026, 7, 12), index, "S1")


@pytest.fixture(scope="module")
def s2(index):
    return _bundle(SOUTH, ANALYST, "meera", date(2026, 6, 2), index, "S2")


@pytest.fixture(scope="module")
def s3(index):
    return _bundle(EAST, ANALYST, "meera", date(2026, 8, 5), index, "S3")


@pytest.fixture(scope="module")
def s6(index):
    return _bundle(WEST, OPS_LEAD, "priya", date(2026, 7, 12), index, "S1")


@pytest.fixture(scope="module")
def s4(index):
    from retrieval.types import (
        FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
    )

    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"product_category": ["NewLaunch"]}, scenario_id="S4",
    )
    a = att.attribute(d, ANALYST, n_resamples=10)
    empty = RetrievalResult(
        query=RetrievalQuery(text=""), filters=FilterConditions(),
        config=RetrievalConfig(
            embedding_model="none", embedding_dim=1, corpus_hash="none"
        ),
    )
    return freeze_evidence_bundle(
        bundle_id="R-S4", persona_id="meera", detection=d, attribution=a,
        retrieval=empty, history_days=23, has_stable_baseline=False,
    )


# --------------------------------------------------------------------------
# helpers: build a model output that should pass, from the bundle
# --------------------------------------------------------------------------
def faithful_payload(bundle) -> dict:
    """A plausible model output that cites correctly.

    Built from the bundle so it stays valid as fixtures change, but written the
    way a model would write it - free text plus references - not by calling the
    deterministic builder.
    """
    top = bundle.hypotheses[0]
    movement = bundle.fact("F-movement-pct")
    licensed = top.causal_language_allowed

    claims = [
        {
            "claim_id": "C01",
            "text": (
                f"{bundle.kpi_name} moved by "
                f"{abs(movement.value):.2f}% over the window."
            ),
            "claim_type": "observation",
            "evidence_ids": [],
            "metric_refs": ["F-movement-pct"],
            "direction": "down" if movement.value < 0 else "up",
        },
        {
            "claim_id": "C02",
            "text": (
                (f"{top.statement} caused the movement."
                 if licensed
                 else f"{top.statement} is consistent with the movement, but "
                      f"the evidence does not establish causality.")
            ),
            "claim_type": "causal" if licensed else "attribution",
            "evidence_ids": list(top.supporting_evidence_ids[:2]),
            "metric_refs": ["F-movement-pct"],
            "direction": "down" if movement.value < 0 else "up",
            "hypothesis_id": top.hypothesis_id,
        },
    ]
    return {
        "headline": f"{bundle.kpi_name} moved in the affected slice",
        "claims": claims,
        "caveats": ["Evidence is drawn from the frozen bundle only."],
        "recommendation_ids": [],
    }


# ==========================================================================
# configuration and routing
# ==========================================================================
def test_model_routing_comes_from_configuration():
    cfg = load_config()
    assert model_for("narrate", cfg) == "claude-opus-5"
    assert model_for("intent", cfg) == "claude-haiku-4-5"
    assert model_for("fallback", cfg) == "claude-sonnet-5"


def test_no_model_name_is_hard_coded_in_the_llm_package():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for path in (root / "llm").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        body = "\n".join(
            line for line in text.splitlines()
            if not line.strip().startswith("#")
        )
        for name in ("claude-opus", "claude-sonnet", "claude-haiku"):
            assert name not in body, (
                f"{path.name} hard-codes '{name}'; model choice belongs in "
                f"config/models.yaml"
            )


def test_cost_is_arithmetic_over_the_config():
    cfg = load_config()
    cost = estimate_cost_usd("claude-opus-5", 1_000_000, 0, 0, cfg)
    assert cost == pytest.approx(5.00)
    cost = estimate_cost_usd("claude-opus-5", 0, 1_000_000, 0, cfg)
    assert cost == pytest.approx(25.00)


def test_cached_input_is_billed_at_the_configured_multiplier():
    cfg = load_config()
    full = estimate_cost_usd("claude-opus-5", 1_000_000, 0, 0, cfg)
    cached = estimate_cost_usd("claude-opus-5", 1_000_000, 0, 1_000_000, cfg)
    assert cached == pytest.approx(full * 0.10)


def test_prompts_are_versioned_on_disk():
    version, text = load_prompt()
    assert version.startswith("narration_v")
    assert len(text) > 500
    for instruction in ("causal", "evidence", "lever", "persona"):
        assert instruction in text.lower()


@pytest.mark.parametrize(
    "name",
    ["narration_v1_concise", "narration_v2_evidence_forward",
     "narration_v3_constrained"],
)
def test_all_three_prompt_variants_exist(name):
    version, text = load_prompt(name)
    assert version == name and text


def test_an_unknown_prompt_is_refused():
    with pytest.raises(NarrationError, match="no prompt"):
        load_prompt("narration_v99_imaginary")


# ==========================================================================
# the payload: what the model sees
# ==========================================================================
def test_the_payload_carries_what_a_narrator_needs(s1):
    payload = payload_mod.build_payload(s1)
    assert payload["metric_facts"] and payload["hypotheses"]
    assert payload["persona"]["role"] == "analytics_lead"
    assert payload["allowed_levers"]
    assert payload["causal_permissions"]


def test_the_payload_withholds_sql_and_raw_analytics(s1):
    """A narrator has no use for compiled SQL, and it carries entitlement
    predicates."""
    text = json.dumps(payload_mod.build_payload(s1))
    assert "compiled_sql" not in text
    assert "SELECT" not in text.upper()
    assert "residual" not in text.lower()


def test_the_payload_withholds_hypothesis_scores(s1):
    """A score is a ranking artefact; quoting it would fail the numeric check."""
    payload = payload_mod.build_payload(s1)
    for h in payload["hypotheses"]:
        assert "score" not in h


def test_the_payload_is_small_enough_to_be_cheap(s1):
    text = json.dumps(payload_mod.build_payload(s1))
    assert len(text) // 4 < 8000, "payload is larger than the architecture budgets"


# ==========================================================================
# parsing
# ==========================================================================
def test_valid_structured_output_parses(s1):
    narrative = parse_narrative(faithful_payload(s1))
    assert narrative.headline
    assert len(narrative.claims) >= 2
    assert not narrative.generated_deterministically


def test_a_confidence_field_is_dropped_not_accepted(s1):
    """There is no slot for it, so a model that emits one is ignored."""
    payload = faithful_payload(s1)
    payload["confidence"] = 0.97
    payload["claims"][0]["confidence"] = 0.99
    narrative = parse_narrative(payload)
    assert not hasattr(narrative, "confidence")
    assert not hasattr(narrative.claims[0], "confidence")


def test_output_with_no_claims_is_refused():
    with pytest.raises(NarrationError, match="no claims"):
        parse_narrative({"headline": "x", "claims": []})


def test_an_unknown_claim_type_is_refused():
    with pytest.raises(NarrationError, match="claim_type"):
        parse_narrative({
            "headline": "x",
            "claims": [{"claim_id": "C1", "text": "y",
                        "claim_type": "speculation"}],
        })


def test_json_is_extracted_from_a_fenced_response():
    text = 'Here is the narrative:\n```json\n{"headline": "x"}\n```\nDone.'
    assert extract_json(text) == {"headline": "x"}


def test_json_extraction_survives_nested_objects():
    text = '{"a": {"b": {"c": 1}}, "d": 2}'
    assert extract_json(text) == {"a": {"b": {"c": 1}}, "d": 2}


def test_json_extraction_returns_none_rather_than_raising():
    assert extract_json("no json at all") is None
    assert extract_json("{broken") is None
    assert extract_json("") is None


# ==========================================================================
# the no-tools invariant
# ==========================================================================
def test_the_client_never_offers_tools(s1):
    """The strongest guarantee in the system, asserted against the request."""
    captured = {}

    class FakeSDK:
        class messages:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                raise RuntimeError("stop here; the request is what matters")

    client = AnthropicClient(api_key="test-key", client=FakeSDK())
    client.complete(system="s", user="u", route="narrate")

    assert "tools" not in captured, "the narrator was offered tools"
    assert "tool_choice" not in captured
    assert set(captured["messages"][0]) == {"role", "content"}


def test_telemetry_records_that_no_call_had_tools(s1):
    client = ScriptedClient([scripted_json(faithful_payload(s1))])
    result = deliver_insight(s1, client)
    assert not result.telemetry.any_call_had_tools


# ==========================================================================
# the loop
# ==========================================================================
def test_a_faithful_narrative_is_delivered_first_pass(s1):
    client = ScriptedClient([scripted_json(faithful_payload(s1))])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.LLM_FIRST_PASS
    assert result.delivered
    assert result.attempts == 1
    assert result.telemetry.retry_count == 0


def test_a_bad_narrative_triggers_exactly_one_retry(s1):
    bad = {
        "headline": "Revenue rose 41.7% in the West",
        "claims": [{
            "claim_id": "C01",
            "text": "Net Revenue rose by 41.70% over the window.",
            "claim_type": "observation",
            "metric_refs": ["F-movement-pct"],
            "direction": "up",
        }],
        "caveats": [], "recommendation_ids": [],
    }
    client = ScriptedClient([
        scripted_json(bad), scripted_json(faithful_payload(s1)),
    ])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.LLM_AFTER_RETRY
    assert result.delivered
    assert result.attempts == 2
    assert len(client.calls) == 2


def test_two_failures_fall_back_to_the_template(s1):
    bad = {
        "headline": "Revenue rose 41.7%",
        "claims": [{
            "claim_id": "C01", "text": "Revenue rose by 41.70%.",
            "claim_type": "observation", "metric_refs": ["F-movement-pct"],
            "direction": "up",
        }],
        "caveats": [], "recommendation_ids": [],
    }
    client = ScriptedClient([scripted_json(bad), scripted_json(bad)])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE
    assert result.delivered, "the template must itself pass Gate 2"
    assert result.attempts == 2
    assert result.fallback_reason


def test_the_fallback_is_labelled_never_silent(s1):
    client = ScriptedClient([failing(FailureReason.TIMEOUT, "timed out")])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE
    assert "timed out" in result.fallback_reason
    assert result.narrative.generated_deterministically


def test_the_retry_receives_the_violations_and_no_new_evidence(s1):
    bad = {
        "headline": "x",
        "claims": [{
            "claim_id": "C01", "text": "Revenue rose by 41.70%.",
            "claim_type": "observation", "metric_refs": ["F-movement-pct"],
            "direction": "up",
        }],
        "caveats": [], "recommendation_ids": [],
    }
    client = ScriptedClient([
        scripted_json(bad), scripted_json(faithful_payload(s1)),
    ])
    deliver_insight(s1, client)

    retry_message = client.calls[1]["user"]
    assert "VIOLATIONS" in retry_message
    assert "UNGROUNDED_NUMBER" in retry_message or "DIRECTION_MISMATCH" in retry_message
    assert "NOT being given new evidence" in retry_message

    # the bundle in the retry must be identical to the bundle in attempt 1
    first_payload = payload_mod.build_payload(s1)
    assert json.dumps(first_payload["metric_facts"]) in retry_message.replace(
        "\n", "\n"
    ) or all(
        f["fact_id"] in retry_message for f in first_payload["metric_facts"][:3]
    )


# ==========================================================================
# model failure handling — the application must not crash
# ==========================================================================
@pytest.mark.parametrize(
    "reason",
    [
        FailureReason.NO_API_KEY,
        FailureReason.TIMEOUT,
        FailureReason.RATE_LIMIT,
        FailureReason.MODEL_UNAVAILABLE,
        FailureReason.TRANSPORT,
        FailureReason.REFUSAL,
    ],
)
def test_every_model_failure_degrades_to_the_template(s1, reason):
    client = ScriptedClient([failing(reason)])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE
    assert result.delivered
    assert reason.value in result.fallback_reason


def test_a_missing_api_key_is_a_return_value_not_an_exception():
    client = AnthropicClient(api_key=None)
    response = client.complete(system="s", user="u")
    assert not response.ok
    assert response.failure_reason is FailureReason.NO_API_KEY
    assert "ANTHROPIC_API_KEY" in response.failure_detail


def test_malformed_output_degrades_to_the_template(s1):
    client = ScriptedClient([
        LLMResponse(ok=True, text="I'm afraid I can't do that.", parsed=None)
    ])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE


def test_schema_parsing_failure_degrades_to_the_template(s1):
    client = ScriptedClient([
        scripted_json({"headline": "x", "claims": "not a list"})
    ])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE


def test_an_empty_script_does_not_crash(s1):
    result = deliver_insight(s1, ScriptedClient([]))
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE


# ==========================================================================
# Gate 2 catches the model's lies
# ==========================================================================
def _single_claim_narrative(bundle, **claim):
    base = {
        "claim_id": "C01", "text": "", "claim_type": "observation",
        "evidence_ids": [], "metric_refs": [], "direction": "n/a",
    }
    base.update(claim)
    return {
        "headline": "Net Revenue moved in the affected slice",
        "claims": [base], "caveats": [], "recommendation_ids": [],
    }


def test_an_invented_number_from_the_model_is_caught(s1):
    bad = _single_claim_narrative(
        s1, text="Revenue fell by 41.70%, a loss of 1,204,880 INR.",
        metric_refs=["F-movement-pct"], direction="down",
    )
    client = ScriptedClient([scripted_json(bad), scripted_json(bad)])
    result = deliver_insight(s1, client)
    assert result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE
    # the first attempt's report is what caught it; re-verify to name the code
    from verification.engine import verify_narrative

    report = verify_narrative(s1, parse_narrative(bad))
    assert ViolationCode.UNGROUNDED_NUMBER in {v.code for v in report.violations}


def test_an_invented_driver_from_the_model_is_caught(s1):
    from verification.engine import verify_narrative

    bad = _single_claim_narrative(
        s1, text="A courier strike explains the movement.",
        claim_type="attribution", hypothesis_id="H-courier_strike",
        metric_refs=["F-movement-pct"], direction="down",
    )
    report = verify_narrative(s1, parse_narrative(bad))
    assert ViolationCode.UNKNOWN_DRIVER in {v.code for v in report.violations}


def test_an_invented_lever_from_the_model_is_caught(s1):
    from verification.engine import verify_narrative

    bad = {
        "headline": "x",
        "claims": [{
            "claim_id": "C01", "text": "Refund every affected customer.",
            "claim_type": "recommendation", "lever_id": "L_BLANKET_REFUND",
        }],
        "caveats": [], "recommendation_ids": ["L_BLANKET_REFUND"],
    }
    report = verify_narrative(s1, parse_narrative(bad))
    assert ViolationCode.UNKNOWN_LEVER in {v.code for v in report.violations}


def test_invalid_evidence_from_the_model_is_caught(s1):
    from verification.engine import verify_narrative

    bad = _single_claim_narrative(
        s1, text="Tickets recorded repeated failures.",
        evidence_ids=["T99999"], direction="up",
    )
    report = verify_narrative(s1, parse_narrative(bad))
    assert ViolationCode.INVALID_EVIDENCE_ID in {v.code for v in report.violations}


def test_an_unsupported_causal_claim_from_the_model_is_caught(s2):
    from verification.engine import verify_narrative

    top = s2.hypotheses[0]
    assert not top.causal_language_allowed
    bad = _single_claim_narrative(
        s2, text="Competitor pricing caused the decline.",
        claim_type="causal", hypothesis_id=top.hypothesis_id,
        evidence_ids=list(top.supporting_evidence_ids[:1]),
        metric_refs=["F-movement-pct"], direction="down",
    )
    report = verify_narrative(s2, parse_narrative(bad))
    assert ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED in {
        v.code for v in report.violations
    }


# ==========================================================================
# scenarios
# ==========================================================================
def test_s1_produces_a_verified_narrative(s1):
    client = ScriptedClient([scripted_json(faithful_payload(s1))])
    result = deliver_insight(s1, client)
    assert result.delivered
    assert result.mode is DeliveryMode.LLM_FIRST_PASS


def test_s2_preserves_uncertainty_and_refuses_causation(s2):
    """The model may not assert a cause the analysis declined to establish."""
    assert s2.overall_status is HypothesisStatus.CONFLICTED
    assert not any(h.causal_language_allowed for h in s2.hypotheses)

    client = ScriptedClient([scripted_json(faithful_payload(s2))])
    result = deliver_insight(s2, client)
    assert result.delivered
    assert not any(
        c.claim_type.value == "causal" for c in result.narrative.claims
    )


def test_s2_keeps_more_than_one_hypothesis_available(s2):
    payload = payload_mod.build_payload(s2)
    assert len(payload["hypotheses"]) >= 2
    assert all(
        not h["causal_language_allowed"] for h in payload["hypotheses"]
    )


def test_s3_and_s4_never_reach_the_model(s3, s4):
    """Gate 1's property: on an abstention the LLM is not called at all."""
    for bundle in (s3, s4):
        abstain, reason = is_structural_abstention(bundle)
        if not abstain:
            continue
        client = ScriptedClient([scripted_json({"headline": "invented"})])
        result = deliver_insight(bundle, client)
        assert result.mode is DeliveryMode.ABSTAINED
        assert result.telemetry.llm_calls == 0
        assert client.calls == [], "the model was called on an abstention"


def test_s4_sparse_history_abstains(s4):
    abstain, reason = is_structural_abstention(s4)
    assert abstain
    result = deliver_insight(s4, ScriptedClient([]))
    assert result.mode is DeliveryMode.ABSTAINED
    assert result.telemetry.llm_calls == 0
    assert not any(
        c.claim_type.value == "causal" for c in result.narrative.claims
    )


def test_s6_restricted_evidence_never_reaches_the_model(s6):
    """The payload cannot leak what the bundle does not contain."""
    from retrieval.types import SourceType

    payload = payload_mod.build_payload(s6)
    for item in payload["supporting_evidence"] + payload["contradicting_evidence"]:
        assert item["source_type"] != SourceType.CRM_NOTE.value
    assert payload["security_context"]["withheld_item_count"] >= 1


def test_s6_a_model_citing_restricted_evidence_is_blocked(s6, s1):
    from retrieval.types import SourceType
    from verification.engine import verify_narrative

    crm = [
        e for e in s1.supporting_evidence
        if e.source_type is SourceType.CRM_NOTE
    ]
    if not crm:
        pytest.skip("no CRM note available to borrow")

    bad = _single_claim_narrative(
        s6, text="An account escalation recorded repeated failures.",
        evidence_ids=[crm[0].evidence_id], direction="up",
    )
    report = verify_narrative(s6, parse_narrative(bad))
    assert not report.passed


# ==========================================================================
# telemetry
# ==========================================================================
def test_telemetry_records_the_call(s1):
    client = ScriptedClient([scripted_json(faithful_payload(s1))])
    result = deliver_insight(s1, client)
    t = result.telemetry
    assert t.llm_calls == 1
    assert t.total_input_tokens > 0 and t.total_output_tokens > 0
    assert t.total_latency_ms > 0
    assert t.to_dict()["bundle_id"] == s1.bundle_id


def test_telemetry_records_zero_calls_on_abstention(s4):
    result = deliver_insight(s4, ScriptedClient([]))
    assert result.telemetry.llm_calls == 0
    assert "never invoked" in result.telemetry.summary()


def test_telemetry_counts_the_retry(s1):
    bad = _single_claim_narrative(
        s1, text="Revenue rose 41.70%.", metric_refs=["F-movement-pct"],
        direction="up",
    )
    client = ScriptedClient([
        scripted_json(bad), scripted_json(faithful_payload(s1)),
    ])
    result = deliver_insight(s1, client)
    assert result.telemetry.retry_count == 1
    assert result.telemetry.llm_calls == 2


def test_telemetry_is_serialisable(s1):
    client = ScriptedClient([scripted_json(faithful_payload(s1))])
    result = deliver_insight(s1, client)
    assert json.dumps(result.telemetry.to_dict())


# ==========================================================================
# the boundary
# ==========================================================================
def test_the_llm_package_imports_no_forbidden_dependency():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    forbidden = ("langchain", "langgraph", "streamlit", "duckdb")
    for path in (root / "llm").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden:
            assert f"import {name}" not in text, f"{path.name} imports {name}"


def test_only_the_client_module_imports_the_sdk():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for path in (root / "llm").rglob("*.py"):
        if "__pycache__" in path.parts or path.name == "client.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "import anthropic" not in text, (
            f"{path.name} imports the SDK; provider details belong in client.py"
        )
