"""BM25 over the candidate corpus (Architecture Part 11.2).

Dense retrieval handles paraphrase; BM25 handles the terms an embedding
flattens: order ids (`ORD-88213`), SKUs, error codes (`PG-TIMEOUT-504`),
service names. Our corpus has both kinds in the same window, which is the
whole argument for running both.

Built over the *candidate* set rather than the whole corpus, so document
frequencies reflect the pool actually being searched - and so an unauthorised
document never contributes to an IDF, let alone to a rank.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from retrieval.types import EvidenceItem

# Keep alphanumerics together so `PG-TIMEOUT-504` survives as `pg`, `timeout`,
# `504` rather than being split on punctuation into noise.
_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class BM25Index:
    """A BM25Okapi index bound to an explicit, ordered candidate list."""

    def __init__(
        self,
        documents: list[EvidenceItem],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.documents = documents
        self.doc_ids = [d.evidence_id for d in documents]
        self.k1 = k1
        self.b = b
        corpus = [tokenize(d.full_text) for d in documents]
        # rank_bm25 cannot build on an empty corpus
        self._bm25 = BM25Okapi(corpus, k1=k1, b=b) if corpus else None

    def search(self, query: str, top_k: int | None = None) -> list[tuple[str, float, int]]:
        """Return (doc_id, score, rank) ordered best-first, rank starting at 1.

        Scores are returned rather than hidden: they are shown in the
        judge-facing evidence panel next to the dense score and the fused rank.
        """
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        order = sorted(
            range(len(self.doc_ids)),
            key=lambda i: (-float(scores[i]), self.doc_ids[i]),
        )
        if top_k is not None:
            order = order[:top_k]
        return [
            (self.doc_ids[i], float(scores[i]), rank)
            for rank, i in enumerate(order, start=1)
        ]
