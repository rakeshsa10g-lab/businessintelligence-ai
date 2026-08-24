"""Stage 6 — hypothesis ranking and the frozen EvidenceBundle.

The boundary between deterministic analysis and the future LLM.

    attribution + retrieval
      -> hypotheses, one per plausible cause bucket, scored deterministically
      -> separation: is the top one actually distinguishable?
      -> freeze_evidence_bundle(...)

After the freeze there is no database access, no retrieval, no external call,
no re-scoring and no mutation. The model receives this object and nothing else,
which is what makes a later verification gate a set-membership test rather than
an aspiration: **if a fact is not in the bundle, it does not exist as far as
the narrative is concerned.**

No LLM appears in this package. No prompts, no SDK, no model of any kind.
"""

from evidence.bundle import (
    compute_hash,
    freeze_evidence_bundle,
    load_persona,
    verify_hash,
)
from evidence.hypothesis import build_hypotheses
from evidence.types import (
    EvidenceBundle,
    EvidenceRef,
    Hypothesis,
    HypothesisStatus,
    MetricFact,
    PersonaProfile,
    SecurityContext,
)

__all__ = [
    "freeze_evidence_bundle",
    "verify_hash",
    "compute_hash",
    "load_persona",
    "build_hypotheses",
    "EvidenceBundle",
    "EvidenceRef",
    "Hypothesis",
    "HypothesisStatus",
    "MetricFact",
    "PersonaProfile",
    "SecurityContext",
]
