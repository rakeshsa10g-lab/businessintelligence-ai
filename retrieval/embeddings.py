"""Local embedding index — no vector database, no hosted API.

`BAAI/bge-small-en-v1.5` via sentence-transformers, run locally. 1,341
documents at 384 dimensions is a 2 MB float32 matrix; a vector database would
add an index, a service and a failure mode to a numpy array that fits in L2
cache (ADR-004).

The index persists four things, and it persists them so a run can be
*disputed* rather than trusted:

    embeddings.npy   the matrix
    doc_ids.json     row order, so row i is always the same document
    meta.json        model name, dimension, corpus hash, build timestamp

If the corpus hash in `meta.json` does not match the corpus on disk, the index
is stale and `load_index` says so instead of returning quietly wrong vectors.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from retrieval.corpus import corpus_hash, document_texts
from retrieval.types import EvidenceItem

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "embedding_index"

# bge models are trained with an asymmetric query prefix: queries get the
# instruction, documents do not. Omitting it costs real retrieval quality, and
# it is the kind of detail that silently degrades a demo.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


class IndexError_(RuntimeError):
    """The persisted index cannot be used as-is."""


@dataclass
class EmbeddingIndex:
    """An in-memory index. Row i of `matrix` is `doc_ids[i]`."""

    matrix: np.ndarray                    # (n_docs, dim), L2-normalised
    doc_ids: list[str]
    model_name: str
    embedding_dim: int
    corpus_hash: str
    built_at: str
    build_seconds: float = 0.0

    def row_of(self, doc_id: str) -> int | None:
        return self._lookup.get(doc_id)

    def __post_init__(self) -> None:
        self._lookup = {d: i for i, d in enumerate(self.doc_ids)}

    def rows_for(self, doc_ids: list[str]) -> tuple[np.ndarray, list[str]]:
        """Submatrix for a candidate set, preserving the caller's order.

        This is how the entitlement filter stays upstream of scoring: only
        permitted rows are ever handed to the similarity computation.
        """
        idx, kept = [], []
        for doc_id in doc_ids:
            row = self._lookup.get(doc_id)
            if row is not None:
                idx.append(row)
                kept.append(doc_id)
        if not idx:
            return np.zeros((0, self.embedding_dim), dtype=np.float32), []
        return self.matrix[np.asarray(idx, dtype=int)], kept


def get_model(model_name: str = MODEL_NAME):
    """Load the sentence-transformer once per process."""
    global _model
    if _model is None or getattr(_model, "_bi_name", None) != model_name:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        model._bi_name = model_name
        _model = model
    return _model


def embed_documents(
    texts: list[str], model_name: str = MODEL_NAME, batch_size: int = 64
) -> np.ndarray:
    model = get_model(model_name)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,     # so cosine is a dot product
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_query(text: str, model_name: str = MODEL_NAME) -> np.ndarray:
    """Embed one query, with the bge instruction prefix."""
    model = get_model(model_name)
    vector = model.encode(
        [QUERY_PREFIX + text],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vector, dtype=np.float32)[0]


def build_index(
    documents: list[EvidenceItem],
    model_name: str = MODEL_NAME,
) -> EmbeddingIndex:
    started = time.perf_counter()
    texts = document_texts(documents)
    matrix = embed_documents(texts, model_name=model_name)
    return EmbeddingIndex(
        matrix=matrix,
        doc_ids=[d.evidence_id for d in documents],
        model_name=model_name,
        embedding_dim=int(matrix.shape[1]) if matrix.size else EMBEDDING_DIM,
        corpus_hash=corpus_hash(documents),
        built_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        build_seconds=time.perf_counter() - started,
    )


def save_index(index: EmbeddingIndex, directory: Path | None = None) -> Path:
    directory = directory or INDEX_DIR
    directory.mkdir(parents=True, exist_ok=True)
    np.save(directory / "embeddings.npy", index.matrix)
    (directory / "doc_ids.json").write_text(
        json.dumps(index.doc_ids), encoding="utf-8"
    )
    (directory / "meta.json").write_text(
        json.dumps(
            {
                "model_name": index.model_name,
                "embedding_dim": index.embedding_dim,
                "corpus_hash": index.corpus_hash,
                "built_at": index.built_at,
                "build_seconds": round(index.build_seconds, 3),
                "n_documents": len(index.doc_ids),
                "query_prefix": QUERY_PREFIX,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return directory


def load_index(
    directory: Path | None = None, expected_corpus_hash: str | None = None
) -> EmbeddingIndex:
    directory = directory or INDEX_DIR
    meta_path = directory / "meta.json"
    if not meta_path.exists():
        raise IndexError_(
            f"no index at {directory}. Run `python -m retrieval.build_index`."
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    matrix = np.load(directory / "embeddings.npy")
    doc_ids = json.loads((directory / "doc_ids.json").read_text(encoding="utf-8"))

    if len(doc_ids) != matrix.shape[0]:
        raise IndexError_(
            f"index is inconsistent: {len(doc_ids)} ids for "
            f"{matrix.shape[0]} rows"
        )
    if expected_corpus_hash and meta["corpus_hash"] != expected_corpus_hash:
        raise IndexError_(
            f"index was built from a different corpus "
            f"(index {meta['corpus_hash'][:12]}, "
            f"corpus {expected_corpus_hash[:12]}). Rebuild it."
        )

    return EmbeddingIndex(
        matrix=np.asarray(matrix, dtype=np.float32),
        doc_ids=doc_ids,
        model_name=meta["model_name"],
        embedding_dim=meta["embedding_dim"],
        corpus_hash=meta["corpus_hash"],
        built_at=meta["built_at"],
        build_seconds=meta.get("build_seconds", 0.0),
    )
