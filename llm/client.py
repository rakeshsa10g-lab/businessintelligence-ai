"""The model adapter (Architecture Part 3.1).

Everything provider-specific lives here. The rest of the system sees
`NarratorClient.complete(system, user, ...) -> LLMResponse` and knows nothing
about Anthropic, message formats or SDK exceptions — which is what makes the
architecture's claim honest: *model choice is a routing decision telemetry can
re-evaluate, not a religious one.* Swapping providers is a change to this file.

**The narrator has no tools.** No `tools=` parameter is passed, ever. That is
the strongest guarantee in the system and it is architectural rather than
behavioural: a model that cannot query cannot fabricate a query result, and no
prompt instruction is needed to prevent what the API surface does not offer.
`tests/test_llm.py::test_the_client_never_offers_tools` asserts it against the
recorded request.

**Failure is a return value, not an exception.** A missing key, a timeout, a
rate limit, an outage or malformed output all produce `LLMResponse.ok = False`
with a typed reason. The caller falls back to the deterministic template. An
application that crashes because a model was slow is an application that has
made the model load-bearing, which is exactly the dependency this design
refuses.
"""

from __future__ import annotations

import functools
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "models.yaml"
API_KEY_ENV = "ANTHROPIC_API_KEY"


class FailureReason(str, Enum):
    NONE = "none"
    NO_API_KEY = "no_api_key"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    REFUSAL = "refusal"
    MALFORMED_OUTPUT = "malformed_output"
    TRANSPORT = "transport"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LLMResponse:
    """One model call. `ok=False` carries the reason rather than raising."""

    ok: bool
    text: str = ""
    parsed: dict | None = None
    model: str = ""
    model_route: str = ""
    prompt_version: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    latency_ms: float = 0.0
    stop_reason: str = ""
    failure_reason: FailureReason = FailureReason.NONE
    failure_detail: str = ""
    request_had_tools: bool = False
    raw_request: dict = field(default_factory=dict)


@functools.lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    config = yaml.safe_load(p.read_text(encoding="utf-8"))
    for key in ("routes", "models", "generation"):
        if key not in config:
            raise ValueError(f"models.yaml is missing '{key}'")
    return config


def reload_config() -> None:
    load_config.cache_clear()


def model_for(route: str, config: dict | None = None) -> str:
    cfg = config or load_config()
    routes = cfg["routes"]
    if route not in routes:
        raise ValueError(
            f"unknown route '{route}'; known routes: {sorted(routes)}"
        )
    return routes[route]


def model_spec(model_name: str, config: dict | None = None) -> dict:
    cfg = config or load_config()
    if model_name not in cfg["models"]:
        raise ValueError(f"model '{model_name}' is not in models.yaml")
    return cfg["models"][model_name]


def estimate_cost_usd(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    config: dict | None = None,
) -> float:
    """Cost in USD from the prices in configuration.

    Cached input is billed at the multiplier in `cache`, so the figure a
    telemetry panel shows is arithmetic over the config rather than a guess.
    """
    cfg = config or load_config()
    spec = model_spec(model_name, cfg)
    multiplier = cfg.get("cache", {}).get("cached_input_price_multiplier", 0.10)

    fresh = max(0, input_tokens - cached_input_tokens)
    cost = fresh / 1_000_000 * spec["input_price_per_mtok_usd"]
    cost += (
        cached_input_tokens / 1_000_000
        * spec["input_price_per_mtok_usd"] * multiplier
    )
    cost += output_tokens / 1_000_000 * spec["output_price_per_mtok_usd"]
    return cost


# --------------------------------------------------------------------------
# the interface the rest of the system sees
# --------------------------------------------------------------------------
class NarratorClient(Protocol):
    """Anything that can turn a prompt pair into a response."""

    def complete(
        self,
        *,
        system: str,
        user: str,
        route: str = "narrate",
        prompt_version: str = "",
        max_tokens: int | None = None,
    ) -> LLMResponse: ...


# --------------------------------------------------------------------------
# the real one
# --------------------------------------------------------------------------
class AnthropicClient:
    """The Anthropic implementation. Roughly the fifteen lines Part 3.1 promised."""

    def __init__(
        self,
        api_key: str | None = None,
        config: dict | None = None,
        client: Any = None,
    ) -> None:
        self.config = config or load_config()
        self.api_key = api_key or os.environ.get(API_KEY_ENV)
        self._client = client

    def _sdk(self):
        if self._client is not None:
            return self._client
        import anthropic

        gen = self.config["generation"]
        self._client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=gen.get("timeout_seconds", 60),
            max_retries=gen.get("max_retries_transport", 2),
        )
        return self._client

    def complete(
        self,
        *,
        system: str,
        user: str,
        route: str = "narrate",
        prompt_version: str = "",
        max_tokens: int | None = None,
    ) -> LLMResponse:
        model_name = model_for(route, self.config)
        spec = model_spec(model_name, self.config)
        gen = self.config["generation"]

        if not self.api_key:
            return LLMResponse(
                ok=False, model=model_name, model_route=route,
                prompt_version=prompt_version,
                failure_reason=FailureReason.NO_API_KEY,
                failure_detail=(
                    f"{API_KEY_ENV} is not set; narration is unavailable and "
                    f"the deterministic template will be used"
                ),
            )

        cache_enabled = self.config.get("cache", {}).get("enabled", False)
        system_blocks: list[dict] = [{"type": "text", "text": system}]
        if cache_enabled:
            # The system prompt never changes across runs, so marking it
            # cacheable is what turns "cost per insight" into a real number.
            system_blocks[0]["cache_control"] = {"type": "ephemeral"}

        request = {
            "model": spec["model_id"],
            "max_tokens": max_tokens or spec.get("max_output_tokens", 2000),
            "temperature": gen.get("temperature", 0.0),
            "system": system_blocks,
            "messages": [{"role": "user", "content": user}],
        }
        # NOTE: no `tools` key. Not empty - absent. See the module docstring.

        started = time.perf_counter()
        try:
            message = self._sdk().messages.create(**request)
        except Exception as exc:  # noqa: BLE001 - every failure degrades
            return LLMResponse(
                ok=False, model=model_name, model_route=route,
                prompt_version=prompt_version,
                latency_ms=(time.perf_counter() - started) * 1000,
                failure_reason=_classify(exc),
                failure_detail=f"{type(exc).__name__}: {exc}",
                raw_request=_redact(request),
            )
        latency_ms = (time.perf_counter() - started) * 1000

        text = _text_of(message)
        usage = getattr(message, "usage", None)
        response = LLMResponse(
            ok=True,
            text=text,
            model=model_name,
            model_route=route,
            prompt_version=prompt_version,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cached_input_tokens=int(
                getattr(usage, "cache_read_input_tokens", 0) or 0
            ),
            latency_ms=latency_ms,
            stop_reason=str(getattr(message, "stop_reason", "") or ""),
            request_had_tools="tools" in request,
            raw_request=_redact(request),
        )

        parsed = extract_json(text)
        if parsed is None:
            return LLMResponse(
                **{
                    **response.__dict__,
                    "ok": False,
                    "failure_reason": FailureReason.MALFORMED_OUTPUT,
                    "failure_detail": (
                        "the response contained no parseable JSON object"
                    ),
                }
            )
        return LLMResponse(**{**response.__dict__, "parsed": parsed})


def _classify(exc: Exception) -> FailureReason:
    """Map an SDK exception onto a typed reason without importing its classes.

    Matching on the class name keeps this module importable when the SDK is
    absent, which is the situation a missing-key deployment is already in.
    """
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return FailureReason.TIMEOUT
    if "ratelimit" in name:
        return FailureReason.RATE_LIMIT
    if "notfound" in name or "overloaded" in name or "internalserver" in name:
        return FailureReason.MODEL_UNAVAILABLE
    if "authentication" in name or "permission" in name:
        return FailureReason.NO_API_KEY
    if "connection" in name or "apiconnection" in name:
        return FailureReason.TRANSPORT
    return FailureReason.UNKNOWN


def _text_of(message: Any) -> str:
    blocks = getattr(message, "content", None) or []
    parts = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts).strip()


def _redact(request: dict) -> dict:
    """Keep the shape of the request for telemetry, not its content."""
    return {
        "model": request.get("model"),
        "max_tokens": request.get("max_tokens"),
        "temperature": request.get("temperature"),
        "has_tools": "tools" in request,
        "system_blocks": len(request.get("system") or []),
        "messages": len(request.get("messages") or []),
    }


def extract_json(text: str) -> dict | None:
    """Pull the first complete JSON object out of a response.

    Models sometimes wrap JSON in a fenced block or add a sentence before it.
    Brace-matching rather than a regex, so a nested object does not truncate
    the parse, and a `None` return is a typed failure the caller handles
    rather than an exception.
    """
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# --------------------------------------------------------------------------
# test doubles
# --------------------------------------------------------------------------
class ScriptedClient:
    """Returns prepared responses. For tests and for offline demos.

    Not a mock of the SDK - a substitute for the whole adapter, so a test can
    exercise the generate/verify/retry loop without a network, a key, or a
    bill. The `calls` list records what was asked, which is how the no-tools
    and no-new-evidence invariants are asserted.
    """

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete(
        self,
        *,
        system: str,
        user: str,
        route: str = "narrate",
        prompt_version: str = "",
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append({
            "system": system, "user": user, "route": route,
            "prompt_version": prompt_version,
        })
        if not self.responses:
            return LLMResponse(
                ok=False, model="scripted", model_route=route,
                failure_reason=FailureReason.MODEL_UNAVAILABLE,
                failure_detail="the script ran out of responses",
            )
        return self.responses.pop(0)


def scripted_json(payload: dict, **kw) -> LLMResponse:
    """An `ok` response carrying a JSON body, for building scripts."""
    text = json.dumps(payload)
    return LLMResponse(
        ok=True, text=text, parsed=payload, model=kw.pop("model", "scripted"),
        input_tokens=kw.pop("input_tokens", 4000),
        output_tokens=kw.pop("output_tokens", 700),
        latency_ms=kw.pop("latency_ms", 1200.0), **kw
    )


def failing(reason: FailureReason, detail: str = "") -> LLMResponse:
    return LLMResponse(
        ok=False, model="scripted", failure_reason=reason,
        failure_detail=detail or reason.value,
    )
