"""Reciprocal Rank Fusion (Architecture Part 11.2).

    RRF(d) = sum over lists of  1 / (k + rank(d))

Fusing by *rank* rather than score is the point. A BM25 score of 14.2 and a
cosine of 0.81 are not on a common scale, and no fixed weighting makes them
comparable across queries - the BM25 score depends on corpus statistics that
shift with every candidate pool. Rank is scale-free, so the fusion stays
stable when the pool changes.

k = 10 per Part 11.2. A larger k flattens the contribution of top ranks; a
smaller k lets a single list dominate. `eval/run_retrieval_eval.py` sweeps it
so the choice is measured rather than asserted.
"""

from __future__ import annotations

from collections import defaultdict

DEFAULT_K = 10


def reciprocal_rank_fusion(
    rank_lists: list[list[str]], k: int = DEFAULT_K
) -> list[tuple[str, float, int]]:
    """Fuse ranked id lists. Returns (doc_id, rrf_score, fused_rank).

    Documents missing from a list simply contribute nothing from it, which is
    the behaviour that lets a strong BM25 hit survive being invisible to the
    dense model and vice versa.
    """
    if k <= 0:
        raise ValueError(f"RRF k must be positive, got {k}")

    scores: dict[str, float] = defaultdict(float)
    for lst in rank_lists:
        for rank, doc_id in enumerate(lst, start=1):
            scores[doc_id] += 1.0 / (k + rank)

    # ties broken by id so the ordering is deterministic across runs
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(doc_id, score, rank) for rank, (doc_id, score) in enumerate(ordered, start=1)]
