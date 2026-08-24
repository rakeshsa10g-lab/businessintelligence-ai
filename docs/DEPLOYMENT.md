# Running BusinessIntelligence.ai

The Round 2 prototype is one Python process. There is no server tier, no
container orchestration and no cloud deployment, because none of those would
be exercised by a single-user demo — Stage 12 explicitly forbids
infrastructure added for appearance.

---

## Requirements

| | |
|---|---|
| **Python** | 3.13 (developed on 3.13.4). Requires 3.11+ for `ContextVar` defaults and `X \| Y` unions used throughout. |
| **Disk** | ~2.5 GB — most of it `torch`, pulled in by `sentence-transformers`. The warehouse is ~25 MB and the embedding index ~2 MB. |
| **RAM** | ~2 GB peak, during the embedding build. |
| **Network** | Needed once, to download `BAAI/bge-small-en-v1.5` (~130 MB). Afterwards the app runs entirely offline. |
| **OS** | Developed on Windows 11; CI runs Ubuntu. No OS-specific code. |

---

## Setup

```bash
git clone <repo>
cd businessintelligence-ai
pip install -r requirements.txt
```

Two fixtures must then be built. **Neither is committed** — both are large and
both are deterministic, so a rebuild is cheaper and more trustworthy than a
binary in version control:

```bash
python -m data.generate           # -> data/warehouse.duckdb   (~25 MB, ~40 s)
python -m retrieval.build_index   # -> data/embedding_index/   (~2 MB, ~60 s)
```

`data.generate` is seeded (`20260821`). Two runs produce byte-identical
output, which `tests/test_data.py::test_same_seed_produces_identical_output`
asserts.

```bash
streamlit run app.py
```

Opens on `http://localhost:8501`.

---

## Environment variables

| Variable | Required | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | **No** | Enables model-written narratives. Without it the graph routes to the verified deterministic template — see below. |
| `LANGGRAPH_STRICT_MSGPACK` | No | Set `true` to opt in early to LangGraph's future strict checkpoint serialization. The suite passes under it (ADR-031). |

There is no `.env` file and nothing reads one. The key is read exactly once,
in `llm/client.py`, via `os.environ.get`.

### Running without a key is a supported mode, not a degraded one

This is worth stating plainly because it is the mode the prototype currently
ships in and the mode every measurement in `eval/` was taken under.

With no key: detection, attribution, retrieval, hypothesis ranking, the frozen
`EvidenceBundle`, verification, confidence, recommendation and deferral all run
identically. Only the *sentence construction* differs — the wording comes from
`verification.build_deterministic_narrative` instead of a model, and it is put
through the same Gate 2 checks. The UI labels this **Verified template mode**
and states that no model reviewed the text.

What is *not* available without a key: any measurement of live model latency,
token usage, cost, or first-pass verification rate. Those are reported as
`LIVE LLM EVALUATION PENDING` rather than estimated.

---

## Persistence

Three stores, deliberately separate (see `docs/STORAGE_ARCHITECTURE.md`):

| Store | Path | Lifetime | Committed |
|---|---|---|---|
| Analytical warehouse | `data/warehouse.duckdb` | Rebuild any time | No — reproducible from seed |
| Graph checkpoints | `data/graph_checkpoints.sqlite` | Per run; holds paused human reviews | No — runtime state |
| Retrieval index | `data/embedding_index/` | Rebuild on corpus change | No — reproducible |

A paused `REVIEW_REQUIRED` run survives an app restart, because the
checkpointer is durable SQLite rather than in-memory. Deleting the checkpoint
file discards paused reviews and nothing else — the warehouse is untouched.

---

## Verifying the install

```bash
python -m pytest -p no:randomly          # full suite
python -m eval.run_graph_eval            # all 8 scenarios end to end
```

The graph evaluation is the fastest end-to-end confidence check: it drives
every scenario through the real graph and writes `eval/graph_report.md`.

---

## What is deliberately absent

No Dockerfile, no cloud deployment, no reverse proxy, no process manager, no
multi-user session store. The prototype is a single-process demo and adding
any of those would be infrastructure with nothing behind it.

`docs/PRODUCTION_EVOLUTION.md` sets out what each of them would be replaced
with, and — more usefully — the specific trigger that would make each one
necessary.
