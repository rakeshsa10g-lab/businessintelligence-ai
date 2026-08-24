"""Build and persist the local embedding index.

    python -m retrieval.build_index

Reproducible from the corpus: the index records the model name, the embedding
dimension and a content hash of the documents it was built from, and
`load_index` refuses to serve an index whose corpus hash no longer matches.
"""

from __future__ import annotations

import time

from retrieval import corpus as corpus_mod
from retrieval import embeddings as emb


def main() -> None:
    started = time.perf_counter()
    documents, withheld = corpus_mod.load_documents()   # full corpus, no principal
    load_seconds = time.perf_counter() - started

    print(f"loaded {len(documents)} documents in {load_seconds:.2f}s")
    by_type: dict[str, int] = {}
    for doc in documents:
        by_type[doc.source_type.value] = by_type.get(doc.source_type.value, 0) + 1
    for name, count in sorted(by_type.items()):
        print(f"  {name:<16} {count:>5}")

    print(f"\nembedding with {emb.MODEL_NAME} ...")
    index = emb.build_index(documents)
    directory = emb.save_index(index)

    print(f"  matrix       {index.matrix.shape}")
    print(f"  corpus hash  {index.corpus_hash[:16]}...")
    print(f"  build time   {index.build_seconds:.2f}s "
          f"({index.build_seconds / max(1, len(documents)) * 1000:.2f} ms/doc)")
    print(f"  saved to     {directory}")


if __name__ == "__main__":
    main()
