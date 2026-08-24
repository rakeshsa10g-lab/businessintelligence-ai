# Production evolution

Nothing in this document is implemented. It exists to answer one question
honestly: *what would actually have to change, and what would tell you it was
time?*

Each row names a **trigger** — a specific observable condition — rather than a
volume ("if we scale"). A migration without a trigger is a guess about the
future; a migration with one is a plan.

---

## What the prototype is

| Layer | Round 2 prototype |
|---|---|
| Frontend | Streamlit, one page, four tabs |
| Orchestration | LangGraph, 26 nodes, in-process |
| Analytics | statsmodels / ruptures / scipy / numpy, in-process |
| Warehouse | DuckDB, one file, embedded |
| Retrieval | `sentence-transformers` + numpy matrix, 1,341 vectors in memory |
| Workflow state | SQLite checkpoint file |
| Identity | a dropdown |
| Model access | Anthropic SDK, direct |
| Observability | telemetry captured into the run result |
| Deployment | one Python process on a laptop |

This is a defensible shape for a single-user demo. It is not a small version
of a production system — several parts are the *wrong* shape for production
rather than an undersized one, and the table below says which.

---

## Migrations, with triggers

### 1. DuckDB → enterprise warehouse / lakehouse

| | |
|---|---|
| **Today** | One 24 MB file, single writer, embedded in the process |
| **Production** | Snowflake / Databricks / BigQuery, or an existing warehouse |
| **Trigger** | **Any of:** the data no longer fits one machine; a second concurrent writer is needed; the source data already lives in an enterprise warehouse and copying it is the wrong direction |
| **What survives** | `semantic/gateway.py` is a single function. Swapping the engine is one implementation change behind an interface `tests/test_chokepoint.py` already pins |
| **What does not** | DuckDB-specific SQL; the assumption that a read is microseconds |
| **Honest note** | This is the *easiest* migration, precisely because the chokepoint was built first. It is also the one most likely to be unnecessary — most enterprises would point this at a warehouse they already have |

### 2. In-memory index → managed vector search

| | |
|---|---|
| **Today** | 1,341 × 384 floats in a numpy array; brute-force cosine; **one index across all tenants** |
| **Production** | pgvector, Vertex Matching Engine, or a search service with row-level security |
| **Trigger** | **Security, before scale.** The first customer with contractual data isolation. Brute force is fine to ~10⁵ documents; the single-tenant artefact is a problem at customer *two* |
| **Why security leads** | The index holds ids and vectors, not text — but embedding inversion can recover approximate content, and one file spans every tenant. Query-time filtering protects the *result*; it does not protect the *artefact* |
| **What survives** | The RRF fusion layer and the entitlement-before-ranking ordering. Both are independent of the store |

### 3. SQLite checkpoints → durable workflow state

| | |
|---|---|
| **Today** | One SQLite file on local disk |
| **Production** | Postgres-backed LangGraph checkpointer, or a managed workflow service |
| **Trigger** | The app runs on more than one process or machine — at which point a local file is invisible to the other one, and a paused human review becomes unresumable depending on which instance the analyst lands on |
| **What survives** | Everything. LangGraph's checkpointer is an interface; `graph/build.py::make_checkpointer` is the only place that names SQLite |
| **Already prepared** | The serialisation allowlist (ADR-031) and the `PlainDateTime` normalisation were both needed *because* state must survive a round trip. That work does not have to be redone |

### 4. Streamlit → embedded web / BI frontend

| | |
|---|---|
| **Today** | Streamlit, server-rendered, one session at a time |
| **Production** | React/Next embedded in the customer's BI tool, or a Power BI / Tableau extension |
| **Trigger** | **Any of:** insights need to appear where analysts already work rather than in a separate app; more than ~10 concurrent users (Streamlit reruns the whole script per interaction); a design requirement Streamlit's component model cannot express |
| **What survives** | `RunResult.as_dict()` is already fully JSON-serialisable, and `tests/test_ui.py` enforces that the UI computes nothing. A different frontend consumes the same object |
| **What does not** | Every Streamlit widget. The `ui/` package would be rewritten — which is the correct cost, because it is presentation only |

### 5. Dropdown → enterprise IAM

| | |
|---|---|
| **Today** | Persona chosen from a dropdown. **No authentication whatsoever** |
| **Production** | OIDC / SAML against the corporate IdP; group membership maps to `Principal` |
| **Trigger** | **Before any real data touches this system.** Not a scale trigger — a correctness one |
| **What survives** | The entire entitlement engine. `security/entitlements.py` takes a `Principal` and never asks where it came from; all 32 security tests continue to apply unchanged |
| **What is missing today** | Only proof that the caller *is* the persona they selected. The authorisation half is real, tested, and enforced at the chokepoint |
| **Honest framing** | This is the single largest gap between prototype and production, and it is a one-layer gap rather than a redesign |

### 6. Direct SDK → model gateway

| | |
|---|---|
| **Today** | `llm/client.py` calls Anthropic directly; key from environment |
| **Production** | A gateway providing key rotation, per-tenant quota, request logging, failover and cost attribution |
| **Trigger** | **Any of:** more than one team shares the key; per-tenant cost attribution is required; an outage needs a fallback model rather than falling back to the template |
| **What survives** | `NarratorClient` is a `Protocol` with one method. A gateway client satisfies it without touching `narrator.py` |
| **Already prepared** | Failures are return values, not exceptions (ADR-025), so a gateway's typed error modes fit the existing shape |

### 7. Run telemetry → observability platform

| | |
|---|---|
| **Today** | Per-node telemetry captured during the run, rendered in the Audit tab, discarded when the process ends |
| **Production** | OpenTelemetry traces to Datadog / Honeycomb; `audit_log` to a retained store |
| **Trigger** | Anyone needs to answer "what happened last Tuesday" after the process has restarted, or to alert on a rate rather than inspect a run |
| **What survives** | `NodeTelemetry` already carries what a span needs — name, start, end, status, attributes. It is a span in all but serialisation |
| **Also needed** | `audit_log` grows monotonically (31,990 rows in development) with no retention policy. Production needs partitioning and retention, and an audit log that self-prunes needs that decision made deliberately |

### 8. One process → horizontal workers

| | |
|---|---|
| **Today** | One process. An S1 run takes ~49 s wall clock and blocks it |
| **Production** | A queue with stateless workers; the UI polls a run id |
| **Trigger** | Concurrent demand exceeds one run at a time — which at ~15–50 s per run is roughly *two simultaneous users*, not a thousand |
| **Blocking issue** | Not CPU. **DuckDB permits a single writer**, and the audit log is written on every read. This is the concrete thing that must change first, and it is the same migration as row 1 |
| **What survives** | The graph is already a state machine with durable checkpoints — the hard part of making work resumable across workers is done |
| **Honest note** | This is the migration most often claimed cheaply. It is not cheap here, and the reason is storage, not compute |

---

## What would *not* change

Worth stating, because it is the part that was expensive to get right:

- **The deterministic/AI boundary.** No routing predicate reads model output; the narration request has no `tools` key; `Narrative` has no `confidence` field. None of that is a prototype convenience.
- **The freeze boundary.** `EvidenceBundle` is hashed and immutable; Gate 2 checks against it. This is what makes verification mechanical rather than aspirational.
- **Entitlement before ranking.** Filtering after ranking leaks information through the scores of neighbouring documents. The ordering is correct at any scale.
- **The typed module contracts.** 0 circular imports, every engine taking a `Principal` or a frozen bundle, nothing reading global state to discover who is asking.

---

## Sequencing

If this became a product, the order is driven by risk, not by difficulty:

1. **Enterprise IAM** — before any real data. Everything else is premature until the caller's identity is proven.
2. **Warehouse + per-tenant retrieval** — together, since both are data-isolation concerns and row 8 depends on row 1.
3. **Durable workflow state + workers** — when a second concurrent user appears.
4. **Model gateway + observability** — when the cost of *not* having them becomes visible, which is usually the first incident.
5. **Embedded frontend** — last. It is the most visible change and the least risky one to defer.
