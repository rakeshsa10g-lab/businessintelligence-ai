# Final system architecture — as built

This documents what the code actually does. Where the implementation diverges
from `ROUND2_TECHNICAL_ARCHITECTURE.md`, the divergence is stated with the ADR
that recorded it — the aspirational document is not quietly corrected to match.

---

## 1. System context

```
                    ┌──────────────────────────────────────┐
   analyst ────────►│  Streamlit  (app.py, ui/)            │
   (one process,    │  presentation only                   │
    one user)       └──────────────┬───────────────────────┘
                                   │  run_insight(request) -> RunResult
                                   │  resume_review(run_id, outcome)
                    ┌──────────────▼───────────────────────┐
                    │  LangGraph  (graph/)                 │
                    │  26 nodes · 6 branch points · 1 cycle│
                    │  workflow runtime, no analysis       │
                    └──────────────┬───────────────────────┘
             ┌─────────────────────┼──────────────────────────┐
             ▼                     ▼                          ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │ analytical       │  │ retrieval        │  │ generation         │
   │ detection/       │  │ retrieval/       │  │ llm/               │
   │ attribution/     │  │ BM25+dense+RRF   │  │ verification/      │
   │ confidence/      │  │                  │  │ (Gate 2)           │
   │ recommendation/  │  │                  │  │                    │
   │ deferral/        │  │                  │  │                    │
   └────────┬─────────┘  └────────┬─────────┘  └─────────┬──────────┘
            │                     │                       │
            └──────────┬──────────┘                       │
                       ▼                                  ▼
          ┌────────────────────────┐        ┌──────────────────────┐
          │ semantic/gateway.py    │        │ Anthropic API        │
          │ THE ONLY DuckDB caller │        │ optional; absent ->  │
          └───────────┬────────────┘        │ template mode        │
                      ▼                     └──────────────────────┘
   ┌───────────────────────────────────────────────────┐
   │ data/warehouse.duckdb  ·  data/embedding_index/   │
   │ data/graph_checkpoints.sqlite                     │
   └───────────────────────────────────────────────────┘
```

Every arrow into storage passes through `semantic/gateway.py`.
`tests/test_chokepoint.py` asserts no other runtime module imports `duckdb`.

---

## 2. Component responsibilities

Each entry states what the component is **not** responsible for, because that
is where the boundaries actually get violated.

### `semantic/` — contracts and the data chokepoint
- **Responsibility** KPI contracts (definition, formula, drivers, thresholds, lineage, security); the single guarded query path.
- **In** `kpi_id`, `Window`, dimensions, `Principal`.
- **Out** `MetricSeries` with lineage and freshness attached.
- **Technology** DuckDB, Pydantic, YAML.
- **NOT responsible for** deciding whether a movement matters, or what caused it. It returns rows; judgement lives downstream.

### `security/` — entitlement policy and audit
- **Responsibility** Resolve a `Principal` into row filters, denied columns and denied sources; write an append-only audit row for every read, including denials.
- **In** `Principal`, `KPIContract`.
- **Out** `AccessDecision`; rows in `audit_log`.
- **NOT responsible for** enforcing the decision — the gateway applies it. Splitting *decide* from *apply* is what lets the policy be unit-tested without a database.

### `detection/` — is it real, and does it matter
- **Responsibility** Coverage gate → STL → robust MAD z-score → PELT changepoint → materiality rule.
- **Out** `DetectionResult` with one of four outcomes: `MATERIAL_EVENT`, `NO_MATERIAL_FINDING`, `SPARSE_HISTORY`, `INSUFFICIENT_DATA`.
- **NOT responsible for** explaining the movement, or for deciding what to do about it.

### `attribution/` — what drove it
- **Responsibility** LMDI identity decomposition, Adtributor dimension ranking, moving-block bootstrap robustness, difference-in-differences counterfactual.
- **Out** `AttributionResult`, including `causal_language_licensed` — a *licence*, not a score.
- **NOT responsible for** asserting causation. It grants or withholds permission for causal wording; the narrator may not override it.

### `retrieval/` — corroboration and contradiction
- **Responsibility** Entitlement filter → per-cause-bucket queries → BM25 + dense embeddings → reciprocal rank fusion → cohort aggregation → deterministic contradiction signals.
- **NOT responsible for** deciding which hypothesis wins, and **not** for access control — it consumes an already-filtered candidate set.

### `evidence/` — hypothesis ranking and the freeze boundary
- **Responsibility** Score hypotheses, then **freeze** an `EvidenceBundle` and hash it.
- **NOT responsible for** anything after the freeze. This is the architectural seam: after `freeze_evidence_bundle`, no component may add a fact.

### `verification/` — Gate 2
- **Responsibility** 10 deterministic checks over a narrative against the frozen bundle; also builds the deterministic template narrative.
- **NOT responsible for** improving a bad narrative. It reports violations; routing decides.

### `llm/` — constrained narration
- **Responsibility** One schema-constrained call. No tools key, ever.
- **NOT responsible for** any number, any confidence, any lever id, or any routing decision.

### `confidence/`, `recommendation/`, `deferral/`
- **Responsibility** Banded confidence with Laplace-smoothed calibration; lever lookup with impact read from measured movement; cost-sensitive automate/review/abstain.
- **NOT responsible for** narrative text. Wording is downstream of all three.

### `graph/` — workflow runtime
- **Responsibility** State, routing, telemetry, lineage accumulation, checkpointing, the human interrupt.
- **NOT responsible for** any analysis. Nodes are thin wrappers; `graph/nodes.py` calls module functions and stores typed results.

### `ui/` — presentation
- **Responsibility** Render a `RunResult`.
- **NOT responsible for** computing anything. Enforced by `tests/test_ui.py`, which fails if `ui/` imports any analytical engine, and by a test asserting only `ui/state.py` may start a run.

---

## 3. Data flow

```
request (persona, kpi, window, slice)
   │
   ├─ resolve_intent ......... persona -> Principal            [deterministic]
   ├─ load_contract .......... KPI contract v1.x               [deterministic]
   ├─ enforce_entitlements ... AccessDecision + audit row      [deterministic]
   │      └─ denied ─────────────────────────► ACCESS_DENIED
   ├─ detect ................. STL/MAD/PELT/materiality        [statistical]
   │      ├─ sparse ─────────────────────────► ABSTAIN_SPARSE_HISTORY
   │      ├─ not material ───────────────────► NO_MATERIAL_EVENT
   │      └─ bad coverage ───────────────────► ABSTAIN_DATA_QUALITY
   ├─ attribute .............. LMDI + Adtributor + DiD         [statistical]
   ├─ retrieve ............... entitlement -> BM25+dense+RRF   [retrieval]
   ├─ rank_hypotheses ........ score, then FREEZE + hash       [deterministic]
   ├─ gate_1 ................. enough to write about?          [deterministic]
   │      └─ insufficient ───────────────────► ABSTAIN_INSUFFICIENT_EVIDENCE
   ├─ narrate ................ constrained model call          [LLM]
   ├─ gate_2 ................. 10 deterministic checks         [deterministic]
   │      ├─ pass ──────────────────► calibrate
   │      ├─ fail, attempts<2 ──────► retry_narrate ──┐
   │      └─ fail, attempts>=2 ─────► deterministic_template
   ├─ calibrate .............. banded + Laplace calibration    [deterministic]
   ├─ recommend .............. lever catalogue, impact READ    [deterministic]
   ├─ defer .................. expected-loss comparison        [deterministic]
   │      ├─ automate ──────────────► deliver ► VERIFIED_LLM | VERIFIED_TEMPLATE
   │      ├─ review ────────────────► human_review ► interrupt() ► REVIEW_REQUIRED
   │      └─ abstain ───────────────► typed abstention terminal
   └─ log_run ................ single exit; telemetry finalised
```

---

## 4. The deterministic / AI boundary

| Layer | Components | What it decides |
|---|---|---|
| **Deterministic** | contracts, entitlement, materiality rule, hypothesis scoring, Gate 2, confidence, levers, deferral, all routing | every number, every threshold, every branch |
| **Statistical** | STL, MAD z-score, PELT, LMDI, Adtributor, bootstrap, difference-in-differences | magnitude, significance, contribution, causal *licence* |
| **Retrieval** | BM25, dense embeddings, RRF, cohorts | which documents corroborate or contradict |
| **LLM** | one narration call | **wording only**, inside a fixed schema |
| **Human** | analyst review via `interrupt()` | the decision itself when the system defers |

Three properties make the boundary structural rather than a matter of prompt
discipline:

1. **The narration request has no `tools` key** — not empty, absent. A model that cannot query cannot fabricate a query result.
2. **`Narrative` has no `confidence` field.** There is nowhere for a model to write one.
3. **No routing predicate reads model output.** `graph/routing.py` is asserted against its own source: a predicate that started reading `state["narrative"]` fails the test.

---

## 5. Security boundary

```
Principal
   │
   ▼
security.decide() ──────────► AccessDecision (row filter, denied cols/sources)
   │
   ▼
semantic.gateway.guarded_query()  ◄── THE ONLY DuckDB CALLER
   │   applies row filter + column mask, writes audit row
   ▼
MetricSeries ────► detection ────► attribution
   │
   ▼
retrieval: corpus filtered BY PRINCIPAL **before** BM25/dense scoring
   │        withheld items are COUNTED, never ranked
   ▼
EvidenceBundle.security_context {denied_sources, withheld_item_count}
   │
   ▼
LLM payload — built from the frozen bundle only
   │
   ▼
UI — renders the withheld COUNT, never the content
```

**Where restricted data becomes unreachable:** at the retrieval candidate
filter, before ranking. This ordering is the point — filtering after ranking
would let a restricted document influence the score of everything around it,
which leaks information about its existence and content even if the document
itself is dropped.

`tests/test_security_chain.py` follows one restricted source (`crm_notes`,
denied to `ops_lead`) through all six stages and asserts absence at each,
paired with proof that a permitted reader *does* see it — so no assertion can
pass merely because the data is missing.

---

## 6. Failure paths

Every path terminates in a typed state and every one is tested by causing the
fault, not by asserting a handler exists (`tests/test_graph_failures.py`).

| Failure | Terminal | Behaviour |
|---|---|---|
| No material event | `NO_MATERIAL_EVENT` | Quieter screen: no chart, no action. Deliberate — a non-event that looks like an event trains readers to ignore alerts. |
| Sparse history | `ABSTAIN_SPARSE_HISTORY` | States days available vs required and how long to wait. |
| Bad data quality | `ABSTAIN_DATA_QUALITY` | Stops before analysing; raw exception confined to Audit. |
| Insufficient evidence | `ABSTAIN_INSUFFICIENT_EVIDENCE` | Names the missing source. |
| Conflicting evidence | `REVIEW_REQUIRED` | Real `interrupt()`; analyst packet carries the question. |
| Unknown KPI | `CLARIFY_REQUESTED` | Lists the KPIs that exist. |
| Broken contract | `CONTRACT_ERROR` | Loud, never degraded into a polite abstention. |
| Model unavailable | `VERIFIED_TEMPLATE` | Not a failure — a supported mode. |
| Malformed model output | retry once → `VERIFIED_TEMPLATE` | Capped at two attempts, enforced in both router and node (ADR-030). |
| Verification failure | retry once → `VERIFIED_TEMPLATE` | The delivered narrative always passes Gate 2. |
| Node exception | typed terminal | Recorded in telemetry; never a traceback in the Workspace. |
| Telemetry/lineage failure | run continues | A lineage formatting fault degrades the record, never the analysis. |

---

## 7. Divergences from the aspirational architecture

| Part | Aspirational | As built | Why |
|---|---|---|---|
| 12.4 | Gate 1b has a `clarify` branch on hypothesis ambiguity | Gate 1b has two outcomes; ambiguity is the deferral engine's call | ADR-029 — measured: it abstained on S2 while discarding an analyst packet that asked the very question |
| 12.3 | `resolve_intent` uses an LLM to parse free text | Resolves an already-structured request; no model | Calling a model to re-derive supplied values would put a model upstream of every routing decision |
| 12.2 | Nodes 7–9 separate (identity, attribute, counterfactual) | One `attribute` node | `attribution.attribute()` returns one typed result; splitting would mean calling private helpers. Lineage still records all three methods |
| 10.5 | Weighted-sum hypothesis score | Product form | ADR-022 — the weighted sum could not discriminate; 5 of 6 components had spread 0.000 |
| 13.4 | Confidence includes `(1 - p_value)` | Bootstrap robustness instead | ADR-017 — the p-value is post-selection and reads p<0.001 on noise |
| 7.1 | Identity over three source populations | Single S1 population | ADR-018 — closed to only 94.8%; now 0.000000000% |
