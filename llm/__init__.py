"""Stage 8 — the constrained narrator.

    deliver_insight(bundle, client) -> InsightDelivery

The LLM is not an analyst. It cannot query, retrieve, calculate, rank or
decide: it receives a frozen EvidenceBundle and turns finished analysis into
persona-appropriate language. Everything it writes passes through Gate 2 before
any human sees it.

Three guarantees, all architectural rather than behavioural:

  **No tools.** The narration request has no `tools` key. A model that cannot
  query cannot fabricate a query result, and no prompt instruction is needed
  to prevent what the API surface does not offer.

  **No confidence.** The output schema has no such field, so there is nowhere
  for a model to put a number the system did not compute.

  **No silent fallback.** Model failure, malformed output or a second Gate 2
  failure all produce the deterministic template, labelled
  VERIFIED_TEMPLATE_MODE. The application never crashes because a model was
  slow, and never pretends the template was the model's work.
"""

from llm.client import (
    AnthropicClient,
    FailureReason,
    LLMResponse,
    NarratorClient,
    ScriptedClient,
    estimate_cost_usd,
)
from llm.narrator import (
    DeliveryMode,
    InsightDelivery,
    deliver_insight,
    generate_narrative,
    is_structural_abstention,
)
from llm.telemetry import LLMCallRecord, NarrationTelemetry

__all__ = [
    "deliver_insight",
    "generate_narrative",
    "is_structural_abstention",
    "DeliveryMode",
    "InsightDelivery",
    "AnthropicClient",
    "ScriptedClient",
    "NarratorClient",
    "LLMResponse",
    "FailureReason",
    "estimate_cost_usd",
    "LLMCallRecord",
    "NarrationTelemetry",
]
