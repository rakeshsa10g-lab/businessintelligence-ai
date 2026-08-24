"""Stage 7 — Gate 2, the deterministic post-generation verifier.

    verify_narrative(bundle, narrative) -> VerificationReport
    build_deterministic_narrative(bundle) -> Narrative

A future LLM-generated narrative reaches a human only if every claim in it is
supported by the frozen `EvidenceBundle`. Eleven checks, all mechanical: no
model, no randomness, no external service, and no knowledge of Streamlit,
LangGraph, prompts, retrieval or the database.

The deterministic narrative is not a hidden fallback. It is mechanically
rendered from the bundle and therefore faithful by construction, and it is also
the verifier's own test: if the faithful narrative fails Gate 2, the gate is
wrong.
"""

from verification.engine import (
    build_deterministic_narrative,
    narrative_hash,
    verify_narrative,
)
from verification.types import (
    Claim,
    ClaimType,
    Narrative,
    Severity,
    VerificationReport,
    Violation,
    ViolationCode,
)

__all__ = [
    "verify_narrative",
    "build_deterministic_narrative",
    "narrative_hash",
    "Claim",
    "ClaimType",
    "Narrative",
    "Severity",
    "VerificationReport",
    "Violation",
    "ViolationCode",
]
