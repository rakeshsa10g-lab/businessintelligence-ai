# Storage architecture

Three stores, deliberately separate. The separation is the design: a graph run
that dies half way corrupts a checkpoint, never the analytical data.

| Store | Path | Purpose | Written by | Committed |
|---|---|---|---|---|
| **Analytical warehouse** | `data/warehouse.duckdb` | Facts, dimensions, evidence corpus, audit log | `data/generate.py` (build) · `security/audit.py` (audit rows only) | No — reproducible |
| **Graph checkpoints** | `data/graph_checkpoints.sqlite` | Paused runs, human review state | LangGraph `SqliteSaver` | No — runtime state |
| **Retrieval index** | `data/embedding_index/` | Doc ids + vectors | `retrieval/build_index.py` | No — reproducible |

---

## 1. DuckDB — the analytical warehouse

### Integrity, as measured

15 tables, 24.4 MB:

| Table | Rows | | Table | Rows |
|---|---:|---|---|---:|
| `fact_funnel_steps` | 821,760 | | `market_events` | 112 |
| `fact_sessions` | 205,440 | | `finance_adjustments` | 80 |
| `fact_orders` | 105,216 | | `schema_change_log` | 24 |
| `audit_log` | 31,990 | | `dim_channel` | 5 |
| `support_tickets` | 895 | | `dim_product_category` | 5 |
| `crm_notes` | 334 | | `dim_region` | 4 |
| `deploy_changelog` | 177 | | `dim_segment` | 3 |
| `source_watermarks` | 3 | | | |

### Read/write separation

Exactly three writers, and none of them is on the request path:

1. `data/generate.py` — builds the warehouse. **Not reachable from runtime code**, asserted by `tests/test_chokepoint.py::test_generator_is_not_reachable_from_runtime_code`.
2. `security/audit.py` — appends to `audit_log` only, using a connection the gateway passes in. It cannot open its own (`test_audit_writer_cannot_open_a_connection`) and cannot touch another table (`test_audit_writer_only_touches_the_audit_log`).
3. Nothing else.

**Reads** go through one function: `semantic.gateway.guarded_query`. No other
runtime module imports `duckdb` — asserted by
`test_gateway_is_the_only_module_importing_duckdb`.

### No accidental regeneration during app use

`data/generate.py` runs only when invoked as `python -m data.generate`. The
app never calls it; the import-graph audit shows no runtime edge into it.

One real incident worth recording: during Stage 11 the test suite regenerated
`data/SCENARIOS.md` and silently erased a hand-edit. That is *by design* — the
file is generated — but it is why edits now go into `data/generate.py` and why
ADR-028 made the harness the executable definition.

### Reproducible generation

Seeded `20260821`. Two runs produce byte-identical output, asserted by
`tests/test_data.py::test_same_seed_produces_identical_output` — which
regenerates the whole dataset and diffs it (the slowest test in the suite, and
worth it).

### The one growth concern

`audit_log` grows monotonically — 31,990 rows accumulated across development.
Nothing truncates it. For a prototype this is correct: an append-only audit
log that self-prunes is not an audit log. For production it needs retention
policy and partitioning; see `docs/PRODUCTION_EVOLUTION.md`.

---

## 2. SQLite — graph checkpoints

### Why durable rather than in-memory

A `REVIEW_REQUIRED` run is a real paused checkpoint that a person is expected
to come back to. An in-memory saver would lose it on restart, which would make
the human-review feature a demonstration of itself rather than the thing it
claims to be.

### Interrupt / resume, as measured

| | S2 | S3 |
|---|---|---|
| Reached review, interrupted | ✅ | ✅ |
| Analyst question exposed | ✅ | ✅ |
| Resumed on the **same** run id | ✅ | ✅ |
| **Bundle hash identical** across the pause | ✅ | ✅ |
| `pandas.Timestamp` in checkpointed state | NONE | NONE |

The identical bundle hash is the load-bearing assertion: the analyst's
decision attaches to exactly the evidence they reviewed.

### Strict serialization

`LANGGRAPH_STRICT_MSGPACK=true` — LangGraph's future default — produces
identical hashes and **zero** warnings. Verified in both modes.

Two fixes got it there:

- **ADR-031:** the allowlist is *derived* from the type modules (105 classes across 12 modules) rather than typed out, so it cannot fall behind a newly added type. The first attempt used the wrong shape and silently registered nothing — `DeferralDecision` came back as a plain `dict`.
- **Stage 11 P1-01:** `pandas.Timestamp` subclasses `datetime`, so Pydantic accepted it and LangGraph then refused to deserialise it. Fixed at the type boundary with `semantic.types.PlainDateTime`, not at the serialiser.

### No unsupported runtime objects

The LLM client and embedding index are passed through `config["configurable"]`
with a `__` prefix, which LangGraph excludes from checkpoint metadata. A
socket has no place in an audit record.
`test_runtime_handles_never_reach_the_checkpoint` asserts the prefix.

### No stale contamination

Run ids are unique per invocation. A deterministic id (scenario+persona) was
tried first and was a real bug: `invoke()` on an existing thread id returns
that thread's cached result, so a second run silently replayed the first
(ADR-032). `test_re_invoking_the_same_scenario_does_not_return_a_stale_run`
guards it.

WAL and SHM companion files are gitignored alongside the database — they are
just as much runtime state, and an orphaned pair survives deletion of the
`.sqlite` itself.

---

## 3. Retrieval index

### Reproducible build with recorded provenance

`data/embedding_index/meta.json`:

```json
{
  "model_name": "BAAI/bge-small-en-v1.5",
  "embedding_dim": 384,
  "corpus_hash": "a36a851495e788e0f04e2f8a27aef3e400a1373f38206159bf4dcf9ef03bc7c0",
  "built_at": "2026-08-23T12:03:26",
  "build_seconds": 62.852,
  "n_documents": 1341,
  "query_prefix": "Represent this sentence for searching relevant passages: "
}
```

The corpus hash makes staleness detectable rather than assumed: an index built
against a different corpus is identifiable without re-embedding anything.

### What the index actually contains

| File | Size | Contents |
|---|---:|---|
| `embeddings.npy` | 2.06 MB | 1,341 × 384 float vectors |
| `doc_ids.json` | 13 KB | **Ids only** — `["C00001", "C00002", …]` |
| `meta.json` | 327 B | provenance above |

**No document text is stored in the index.** Excerpts live in DuckDB behind
the gateway. This matters for the restricted-content question below.

### Restricted content in the index

The index is built over the **full** corpus, including 334 `crm_note`
documents that `ops_lead` may not read. Stated plainly rather than claimed
otherwise.

Why it is acceptable here:

- The artefact holds **ids and vectors, not text**.
- Entitlement filtering happens at query time **before** BM25/dense scoring, so a restricted document can neither be returned nor influence the ranking of its neighbours.
- `tests/test_security_chain.py` verifies absence at every downstream stage.

Why it would not be acceptable in production: embedding-inversion attacks can
recover approximate text from vectors, and one file spans all tenants. The
migration and its trigger are in `docs/PRODUCTION_EVOLUTION.md`.

---

## Rebuilding everything

```bash
python -m data.generate           # warehouse   ~40 s
python -m retrieval.build_index   # index       ~60 s
```

Neither is committed. Both are deterministic. A rebuild is cheaper and more
trustworthy than a binary in version control.
