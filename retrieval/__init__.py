"""Stage 5 — evidence retrieval.

Given a movement detection established and attribution localised, find the
text and the records that support or contradict the leading explanation.

    entitlement -> metadata filter -> BM25 + dense -> RRF -> cohort -> signals

Two separations do most of the work:

  **structured vs unstructured.** Deploys, schema changes and finance rows
  have exact keys and are retrieved by SQL. Only prose is embedded. On
  Scenario 7 the answer is a schema-change row, and finding it by cosine
  similarity would be a worse system that happened to work.

  **entitlement before scoring.** Restricted documents are refused at the
  gateway, so they never reach an index, an IDF statistic or a rank. Filtering
  them out afterwards would already have leaked them.

No LLM is called here, including for query construction: a model that writes
its own search query is a model choosing what evidence it sees.
"""

from retrieval.engine import retrieve_evidence, structured_evidence
from retrieval.types import (
    CohortEvidence,
    ContradictionSignal,
    EvidenceItem,
    RetrievalResult,
    SourceType,
)

__all__ = [
    "retrieve_evidence",
    "structured_evidence",
    "CohortEvidence",
    "ContradictionSignal",
    "EvidenceItem",
    "RetrievalResult",
    "SourceType",
]
