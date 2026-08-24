"""The constrained narrator, and the generate -> verify -> retry loop.

    deliver_insight(bundle, client) -> InsightDelivery

The ladder is Architecture Part 6.4, implemented exactly:

    1. generate, then verify
    2. on correctable failure: ONE retry with the typed violations
    3. on second failure, or any model failure: the deterministic template,
       labelled VERIFIED_TEMPLATE_MODE

**The fallback is never silent.** `InsightDelivery.mode` says which path
produced the text, and the template mode is a labelled state the UI is meant to
show. Being able to point at the moment the system refused a fluent sentence is
a stronger demonstration than the sentence.

**Structural failures do not retry.** Sparse history, insufficient evidence and
entitlement refusals are properties of the bundle, not of the wording. Asking a
model to try again at explaining something that cannot be explained is how a
system talks itself into an answer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from evidence.types import EvidenceBundle, HypothesisStatus
from llm import payload as payload_mod
from llm.client import (
    FailureReason,
    LLMResponse,
    NarratorClient,
    estimate_cost_usd,
    load_config,
)
from llm.telemetry import LLMCallRecord, NarrationTelemetry
from verification.engine import build_deterministic_narrative, verify_narrative
from verification.types import (
    Claim,
    ClaimType,
    Narrative,
    Severity,
    VerificationReport,
    ViolationCode,
)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Violation codes a rewrite can plausibly fix. Everything hard is correctable
# in principle - the model wrote it, so the model can unwrite it - which is
# why the retry gate is about the BUNDLE's state rather than the violation's.
CORRECTABLE = frozenset({
    ViolationCode.UNGROUNDED_NUMBER,
    ViolationCode.UNGROUNDED_DATE,
    ViolationCode.UNKNOWN_DRIVER,
    ViolationCode.DIRECTION_MISMATCH,
    ViolationCode.MISSING_EVIDENCE,
    ViolationCode.INVALID_EVIDENCE_ID,
    ViolationCode.RESTRICTED_EVIDENCE,
    ViolationCode.DOMINANT_DRIVER_OMITTED,
    ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED,
    ViolationCode.UNKNOWN_LEVER,
    ViolationCode.INVALID_METRIC_REF,
})


class DeliveryMode(str, Enum):
    LLM_FIRST_PASS = "LLM_FIRST_PASS"
    LLM_AFTER_RETRY = "LLM_AFTER_RETRY"
    VERIFIED_TEMPLATE_MODE = "VERIFIED_TEMPLATE_MODE"
    ABSTAINED = "ABSTAINED"


class NarrationError(ValueError):
    """The narrator was asked to do something it must not."""


@dataclass
class InsightDelivery:
    """What came out, how, and everything needed to audit the decision."""

    narrative: Narrative
    report: VerificationReport
    mode: DeliveryMode
    bundle_hash: str
    telemetry: NarrationTelemetry
    attempts: int = 0
    fallback_reason: str = ""

    @property
    def delivered(self) -> bool:
        return self.report.passed

    def explain(self) -> str:
        return (
            f"{self.mode.value} after {self.attempts} model call(s); "
            f"Gate 2 {'passed' if self.report.passed else 'BLOCKED'} "
            f"({self.report.hard_violation_count} hard); "
            f"{self.telemetry.total_latency_ms:.0f} ms, "
            f"${self.telemetry.total_cost_usd:.4f}"
        )


# --------------------------------------------------------------------------
# prompts
# --------------------------------------------------------------------------
def load_prompt(version: str | None = None, config: dict | None = None) -> tuple[str, str]:
    """Return (prompt_version, text). Versioned on disk, selected in config."""
    cfg = config or load_config()
    name = version or cfg.get("prompts", {}).get(
        "narration", "narration_v3_constrained"
    )
    path = PROMPT_DIR / f"{name}.txt"
    if not path.exists():
        raise NarrationError(
            f"no prompt '{name}' in {PROMPT_DIR}; "
            f"available: {sorted(p.stem for p in PROMPT_DIR.glob('*.txt'))}"
        )
    return name, path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
def parse_narrative(parsed: dict) -> Narrative:
    """Turn the model's JSON into the typed schema.

    Unknown fields are dropped rather than tolerated: `confidence` is the one
    that matters, because a model that emits it once will emit it again, and a
    confidence value the system did not compute must never reach a reader.
    """
    if not isinstance(parsed, dict):
        raise NarrationError("model output is not a JSON object")

    claims: list[Claim] = []
    for i, raw in enumerate(parsed.get("claims") or [], start=1):
        if not isinstance(raw, dict):
            raise NarrationError(f"claim {i} is not an object")
        try:
            claim_type = ClaimType(str(raw.get("claim_type", "observation")))
        except ValueError:
            raise NarrationError(
                f"claim {i} has unknown claim_type "
                f"{raw.get('claim_type')!r}"
            ) from None

        direction = str(raw.get("direction") or "n/a")
        if direction not in ("up", "down", "flat", "n/a"):
            direction = "n/a"

        claims.append(Claim(
            claim_id=str(raw.get("claim_id") or f"C{i:02d}"),
            text=str(raw.get("text") or "").strip(),
            claim_type=claim_type,
            evidence_ids=tuple(str(x) for x in (raw.get("evidence_ids") or [])),
            metric_refs=tuple(str(x) for x in (raw.get("metric_refs") or [])),
            direction=direction,
            hypothesis_id=(
                str(raw["hypothesis_id"])
                if raw.get("hypothesis_id") else None
            ),
            lever_id=str(raw["lever_id"]) if raw.get("lever_id") else None,
        ))

    if not claims:
        raise NarrationError("model output contains no claims")

    return Narrative(
        headline=str(parsed.get("headline") or "").strip(),
        claims=tuple(claims),
        caveats=tuple(str(c) for c in (parsed.get("caveats") or [])),
        recommendation_ids=tuple(
            str(x) for x in (parsed.get("recommendation_ids") or [])
        ),
        generated_deterministically=False,
    )


# --------------------------------------------------------------------------
# should we even call the model?
# --------------------------------------------------------------------------
def is_structural_abstention(bundle: EvidenceBundle) -> tuple[bool, str]:
    """A bundle with nothing to explain must not be narrated by a model.

    Gate 1's most important property (Part 13.1): when it fails, the LLM is
    *never called* - not called and ignored. That is a cost argument and a
    safety argument, and `llm_calls = 0` on abstained runs is a line telemetry
    can prove.
    """
    if not bundle.hypotheses:
        return True, (
            f"bundle carries no hypotheses ({bundle.overall_status.value}): "
            f"{bundle.status_reason}"
        )
    if bundle.overall_status in (
        HypothesisStatus.INSUFFICIENT, HypothesisStatus.MULTI_DIMENSIONAL
    ):
        return True, (
            f"bundle status is {bundle.overall_status.value}: "
            f"{bundle.status_reason}"
        )
    return False, ""


# --------------------------------------------------------------------------
# the loop
# --------------------------------------------------------------------------
def generate_narrative(
    bundle: EvidenceBundle,
    client: NarratorClient,
    *,
    prompt_version: str | None = None,
    config: dict | None = None,
) -> tuple[Narrative | None, LLMResponse, str]:
    """One generation attempt. Returns (narrative or None, response, error)."""
    cfg = config or load_config()
    version, system = load_prompt(prompt_version, cfg)
    user = payload_mod.render_user_message(bundle)

    response = client.complete(
        system=system, user=user, route="narrate", prompt_version=version
    )
    if not response.ok:
        return None, response, response.failure_detail

    try:
        return parse_narrative(response.parsed or {}), response, ""
    except NarrationError as exc:
        return None, response, str(exc)


def deliver_insight(
    bundle: EvidenceBundle,
    client: NarratorClient | None = None,
    *,
    prompt_version: str | None = None,
    config: dict | None = None,
    allow_retry: bool = True,
) -> InsightDelivery:
    """Generate, verify, retry once, then fall back. Never raises."""
    cfg = config or load_config()
    telemetry = NarrationTelemetry(bundle_id=bundle.bundle_id)
    started = time.perf_counter()

    def template(mode: DeliveryMode, reason: str, attempts: int) -> InsightDelivery:
        narrative = build_deterministic_narrative(bundle)
        report = verify_narrative(bundle, narrative, run_id=bundle.bundle_id)
        telemetry.total_wall_ms = (time.perf_counter() - started) * 1000
        return InsightDelivery(
            narrative=narrative, report=report, mode=mode,
            bundle_hash=bundle.bundle_hash, telemetry=telemetry,
            attempts=attempts, fallback_reason=reason,
        )

    # --- structural abstention: the model is never called -----------------
    abstain, reason = is_structural_abstention(bundle)
    if abstain:
        return template(DeliveryMode.ABSTAINED, reason, attempts=0)

    if client is None:
        return template(
            DeliveryMode.VERIFIED_TEMPLATE_MODE,
            "no model client was supplied", attempts=0,
        )

    # --- attempt 1 --------------------------------------------------------
    narrative, response, error = generate_narrative(
        bundle, client, prompt_version=prompt_version, config=cfg
    )
    telemetry.record(_record(response, attempt=1, cfg=cfg, error=error))

    if narrative is None:
        return template(
            DeliveryMode.VERIFIED_TEMPLATE_MODE,
            f"generation failed ({response.failure_reason.value}): {error}",
            attempts=1,
        )

    report = verify_narrative(bundle, narrative, run_id=bundle.bundle_id)
    if report.passed:
        telemetry.total_wall_ms = (time.perf_counter() - started) * 1000
        return InsightDelivery(
            narrative=narrative, report=report,
            mode=DeliveryMode.LLM_FIRST_PASS,
            bundle_hash=bundle.bundle_hash, telemetry=telemetry, attempts=1,
        )

    hard = [v for v in report.violations if v.severity is Severity.HARD]
    correctable = [v for v in hard if v.code in CORRECTABLE]

    max_retries = cfg["generation"].get("max_retries_verification", 1)
    if not allow_retry or max_retries < 1 or not correctable:
        return template(
            DeliveryMode.VERIFIED_TEMPLATE_MODE,
            f"first attempt failed {len(hard)} hard check(s) and "
            f"{'retry is disabled' if not allow_retry else 'none is correctable'}",
            attempts=1,
        )

    # --- attempt 2: the same bundle, the violations, no new evidence ------
    version, system = load_prompt(prompt_version, cfg)
    retry_user = payload_mod.render_retry_message(
        bundle, narrative.model_dump(mode="json"), correctable
    )
    retry_response = client.complete(
        system=system, user=retry_user, route="narrate", prompt_version=version
    )
    retry_error = ""
    retry_narrative = None
    if retry_response.ok:
        try:
            retry_narrative = parse_narrative(retry_response.parsed or {})
        except NarrationError as exc:
            retry_error = str(exc)
    else:
        retry_error = retry_response.failure_detail
    telemetry.record(_record(retry_response, attempt=2, cfg=cfg, error=retry_error))

    if retry_narrative is None:
        return template(
            DeliveryMode.VERIFIED_TEMPLATE_MODE,
            f"retry failed to produce a usable narrative: {retry_error}",
            attempts=2,
        )

    retry_report = verify_narrative(
        bundle, retry_narrative, run_id=bundle.bundle_id
    )
    if retry_report.passed:
        telemetry.total_wall_ms = (time.perf_counter() - started) * 1000
        return InsightDelivery(
            narrative=retry_narrative, report=retry_report,
            mode=DeliveryMode.LLM_AFTER_RETRY,
            bundle_hash=bundle.bundle_hash, telemetry=telemetry, attempts=2,
        )

    return template(
        DeliveryMode.VERIFIED_TEMPLATE_MODE,
        f"retry still failed {retry_report.hard_violation_count} hard check(s)",
        attempts=2,
    )


def _record(
    response: LLMResponse, *, attempt: int, cfg: dict, error: str = ""
) -> LLMCallRecord:
    cost = 0.0
    if response.model and response.model in cfg.get("models", {}):
        cost = estimate_cost_usd(
            response.model, response.input_tokens, response.output_tokens,
            response.cached_input_tokens, cfg,
        )
    return LLMCallRecord(
        attempt=attempt,
        route=response.model_route or "narrate",
        model=response.model,
        prompt_version=response.prompt_version,
        ok=response.ok and not error,
        latency_ms=response.latency_ms,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cached_input_tokens=response.cached_input_tokens,
        estimated_cost_usd=cost,
        stop_reason=response.stop_reason,
        failure_reason=response.failure_reason.value,
        failure_detail=error or response.failure_detail,
        had_tools=response.request_had_tools,
    )
