"""Telemetry for model usage (Architecture Part 20).

A structured record per call and per insight. No UI, no dashboard — those are
later stages. What matters now is that the numbers exist and are arithmetic
over `config/models.yaml` rather than estimates: cost per insight is the
strongest economic line in the deck, and it only survives scrutiny if a reader
can recompute it from the prices in configuration.

The most useful field is the one that is often zero. `llm_calls = 0` on an
abstained run is the proof that Gate 1 does not call the model and then discard
the answer — it never calls it (Part 13.1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class LLMCallRecord:
    """One model call."""

    attempt: int
    route: str
    model: str
    prompt_version: str
    ok: bool
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    estimated_cost_usd: float = 0.0
    stop_reason: str = ""
    failure_reason: str = "none"
    failure_detail: str = ""
    had_tools: bool = False
    at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def cache_hit_rate(self) -> float:
        if not self.input_tokens:
            return 0.0
        return self.cached_input_tokens / self.input_tokens


@dataclass
class NarrationTelemetry:
    """Everything one insight cost, across attempts."""

    bundle_id: str
    calls: list[LLMCallRecord] = field(default_factory=list)
    total_wall_ms: float = 0.0

    def record(self, call: LLMCallRecord) -> None:
        self.calls.append(call)

    # -- aggregates --------------------------------------------------------
    @property
    def llm_calls(self) -> int:
        return len(self.calls)

    @property
    def retry_count(self) -> int:
        return max(0, len(self.calls) - 1)

    @property
    def total_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def total_cached_tokens(self) -> int:
        return sum(c.cached_input_tokens for c in self.calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.estimated_cost_usd for c in self.calls)

    @property
    def models_used(self) -> list[str]:
        return sorted({c.model for c in self.calls if c.model})

    @property
    def any_call_had_tools(self) -> bool:
        """Must always be False. The narrator is never given tools."""
        return any(c.had_tools for c in self.calls)

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "llm_calls": self.llm_calls,
            "retry_count": self.retry_count,
            "models_used": self.models_used,
            "prompt_versions": sorted(
                {c.prompt_version for c in self.calls if c.prompt_version}
            ),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "total_wall_ms": round(self.total_wall_ms, 1),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cached_input_tokens": self.total_cached_tokens,
            "estimated_cost_usd": round(self.total_cost_usd, 6),
            "any_call_had_tools": self.any_call_had_tools,
            "calls": [asdict(c) for c in self.calls],
        }

    def summary(self) -> str:
        if not self.calls:
            return (
                f"{self.bundle_id}: llm_calls=0 "
                f"(the model was never invoked for this bundle)"
            )
        return (
            f"{self.bundle_id}: {self.llm_calls} call(s) to "
            f"{', '.join(self.models_used)}, "
            f"{self.total_input_tokens} in / {self.total_output_tokens} out "
            f"({self.total_cached_tokens} cached), "
            f"{self.total_latency_ms:.0f} ms, "
            f"${self.total_cost_usd:.4f}"
        )


def append_jsonl(record: dict, path: Path) -> None:
    """Append one insight's telemetry. JSONL so a run never rewrites history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
