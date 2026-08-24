# Architecture Decision Record

Short ADR format. Append new decisions; do not edit or delete old ones. If a decision is reversed, add a new entry that supersedes it and mark the original.

Status values: `Adopted` · `Rejected` · `Superseded by ADR-nnn` · `Proposed`

---

## ADR-001 — LangChain

**Status:** Rejected
**Date:** 2026-08-21
**Source:** Architecture Part 0, Part 2.1, Part 3.6

**Context.** LangChain is the default assumption for any LLM project, and the intern-standard stack bundles it with LangGraph, embeddings and Streamlit.

**Decision.** Do not take a direct dependency on `langchain`. `langchain-core` arriving transitively under LangGraph is acceptable and should be marked as transitive in `requirements.txt`.

**Rationale.** The LLM surface here is three narrow, schema-constrained calls over frozen inputs. LangChain 1.0's value is the `create_agent` middleware loop — an agent abstraction this architecture specifically must not have, because a model that can re-query data is the exact failure this system exists to prevent. Importing it buys nothing and costs auditability.

**Consequence.** Selection becomes a talking point: "we deliberately removed LangChain, here is the architectural reason." Rejections are the part of a stack decision that cannot be faked.

---

## ADR-002 — LangGraph

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 0, Part 2.2, Part 3.7, Part 12

**Context.** The pipeline is a state machine: conditional routing, two verification gates, a bounded retry cycle, an abstention branch and a human interrupt.

**Decision.** Adopt LangGraph as workflow orchestration only. Not as an agent framework.

**Rationale.** That control-flow shape is precisely what LangGraph models. Its checkpointer additionally yields the run trace, audit trail and lineage record — three separate Round 2 requirements — without extra code.

**Consequence.** Node functions stay thin; business logic lives in the layer packages, not in `graph/nodes.py`. Routing predicates must be pure functions of deterministic state.

---

## ADR-003 — Embeddings

**Status:** Adopted, narrowly scoped
**Date:** 2026-08-21
**Source:** Architecture Part 0, Part 2.3, Part 11

**Context.** Support tickets and CRM notes describe the same failure in many phrasings ("card declined", "payment failed", "gateway timeout"). Keyword-only retrieval misses that, and evidence recall decides whether a hypothesis is supported or the system abstains.

**Decision.** Use embeddings over the unstructured document corpus only (~1,500 documents). Hybrid retrieval: BM25 + dense, fused with Reciprocal Rank Fusion.

**Rationale.** Semantic recall is genuinely needed for free text. It is not needed, and is actively harmful, anywhere a definition must be exact.

**Consequence.** Embeddings go nowhere near KPI metadata, semantic definitions, changelog rows or numbers. Fuzzy-matching a source of truth is how the wrong definition reaches a narrative. Requires an in-domain retrieval eval (Part 11.6) before the embedding choice is trusted — MTEB rank is not evidence.

---

## ADR-004 — Vector database

**Status:** Rejected
**Date:** 2026-08-21
**Source:** Architecture Part 3.3, Part 24

**Context.** A vector store is the reflexive companion to embeddings.

**Decision.** No vector database. Vectors are held as plain in-memory / on-disk arrays.

**Rationale.** The corpus is roughly 2.3 MB of vectors. Managed vector infrastructure at that scale is operational cost with no retrieval benefit.

**Consequence.** Deployment stays one Python process and one file. Revisit only if the corpus grows by orders of magnitude.

---

## ADR-005 — DuckDB

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 3.4

**Decision.** DuckDB, single file, as the analytical store for all structured data.

**Rationale.** Real SQL semantics and analytical performance with zero server. A judge can clone and run the prototype in seconds; the star schema models the entity relationships exactly, which is also why GraphRAG is unnecessary (Part 24).

**Consequence.** Exactly one module (`semantic/gateway.py`) may open or query the database. See ADR-011.

---

## ADR-006 — Streamlit

**Status:** Adopted for the prototype, explicitly temporary
**Date:** 2026-08-21
**Source:** Architecture Part 2.4, Part 18

**Decision.** Streamlit for the Round 2 prototype UI. Build a decision workspace, not a chatbot.

**Rationale.** It is the only way to get a multi-persona, multi-state analytical UI built and demo-stable in the time available.

**Consequence.** Streamlit is presentation only — no analysis in callbacks. It is not the long-term answer and the roadmap slide should say so. A chat interface is explicitly rejected (Part 24): chat invites open-ended questions the gates cannot bound.

---

## ADR-007 — Statistical detection before the LLM

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 1.1, Part 6, Part 9

**Decision.** Detection and attribution are fully deterministic and run to completion before any model call. The LLM never decides whether a movement is real, nor which driver caused it.

**Rationale.** The system's central claim is that the LLM is not the source of quantitative truth. CALM (arXiv 2508.21273) showed LLM-as-judge improving anomaly detection AUC on some datasets and degrading it on others — not a foundation to put numbers on.

**Consequence.** Build stages 1 → 4 yield a defensible diagnostic engine with no LLM at all. That sequence is the critical path and must be protected.

---

## ADR-008 — Deterministic verification before human delivery

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 6, Part 13

**Context.** A 2026 fidelity audit (arXiv 2608.08126) found a model explaining risk factors inverted the direction on three of four, substituting its own priors for the supplied evidence.

**Decision.** Two gates. Gate 1 before generation checks data quality and coverage. Gate 2 after generation runs ten deterministic checks over every claim — membership, direction, coverage and others — before any text reaches a human. On failure the system descends a defined ladder ending in a deterministic template.

**Rationale.** Input-side constraints alone do not guarantee output fidelity. The check must be mechanical and must run last.

**Consequence.** Gate 2 is built **before** the narrator (Part 23), so the verification schema defines what narration may produce rather than the reverse. Any LLM-as-judge component is advisory only; primary checks stay deterministic.

---

## ADR-009 — Multi-agent architecture

**Status:** Rejected
**Date:** 2026-08-21
**Source:** Architecture Part 24

**Decision.** No multi-agent system, and argue against it explicitly.

**Rationale.** Multiple agents negotiating an answer is the direct opposite of "the LLM is not the source of quantitative truth." Every agent boundary is a place a number can mutate without a check. Gartner's "agent drift" warning applies; this architecture is already the guardian-agent pattern, and adding autonomy underneath defeats it.

**Consequence.** No autonomous agents, no agent-to-agent messaging, no tool-calling loop that lets a model fetch data.

---

## ADR-010 — Fine-tuning

**Status:** Rejected
**Date:** 2026-08-21
**Source:** Architecture Part 24

**Decision.** No fine-tuning, no LoRA.

**Rationale.** There are roughly 87 synthetic examples available; fine-tuning on that overfits to the data generator. More fundamentally the quality problem is *grounding*, which fine-tuning does not address.

**Consequence.** The stated position is the stronger one: "we deliberately did not fine-tune, because our failure mode is fabrication, not style."

---

## ADR-011 — Single data-access chokepoint

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 8.2, Part 21.3, Part 22

**Decision.** `semantic/gateway.py::guarded_query()` is the only code path that touches DuckDB. Entitlement and semantic-contract enforcement happen inside it, upstream of every consumer including the model.

**Rationale.** Row-, column- and domain-level security (`R2-CX-8`, `R2-MPE-7`) is only credible if it cannot be bypassed. One path is auditable; several are not.

**Consequence.** `tests/test_chokepoint.py` asserts the property mechanically. The predictable failure mode is a "quick" direct query in a notebook that becomes permanent — the test exists to catch exactly that.

---

## ADR-012 — Repository located outside OneDrive

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Operational judgment, not the architecture document

**Context.** All prior project material lives under `OneDrive/Desktop`. During Round 1, OneDrive file locking repeatedly blocked writes to open files.

**Decision.** The code repository lives at `C:\Users\rakes\dev\businessintelligence-ai`, outside the OneDrive sync root. Round 1 deliverables stay where they are.

**Rationale.** A synced `warehouse.duckdb` risks lock contention and partial-write corruption, and a sync event mid-demo is an avoidable failure. Python virtual environments also sync poorly.

**Consequence.** The project folder under `Desktop/BusinessIntelligence_AI_AIC2026/` remains the home for decks, research and submissions. Reversible in one move if a different location is preferred.

---

## ADR-013 — Reproducibility asserted on content, not file bytes

**Status:** Adopted (supersedes the wording of Architecture Part 23, Stage 1)
**Date:** 2026-08-21
**Source:** Architecture Part 23 Stage 1 "Done when: two runs from the same seed are byte-identical"

**Context.** The architecture document's Stage 1 acceptance criterion asks for two runs from one seed to produce byte-identical database files. Measured behaviour: two runs produce files of *identical size* but *different bytes*, while every table's contents compare equal row for row. DuckDB embeds internal metadata that varies between writes.

**Decision.** `tests/test_data.py::test_same_seed_produces_identical_output` asserts that the hashed **contents** of every generated table are identical, plus that `ground_truth.json` is byte-identical. It does not hash the database file.

**Rationale.** Byte equality of a database file is not achievable here and was never the property of interest. The property that matters is that the same seed yields the same data, which is what downstream detection and attribution accuracy depend on.

**Consequence.** One real bug surfaced while implementing this: the `dim_*` tables were created with `SELECT DISTINCT` and no `ORDER BY`, so DuckDB's parallel hash aggregate returned rows in unstable order across runs. Contents were equal as a set but not as a sequence. Fixed by adding `ORDER BY`. A file-byte check would have flagged this only as noise among the metadata differences; the content check located it precisely.

---

## ADR-014 — Freshness evaluated against a fixed demo clock

**Status:** Adopted
**Date:** 2026-08-21
**Source:** Architecture Part 7.3 (source cadences), Part 7.7 (LineageRecord)

**Context.** Source freshness is a graded Round 2 artifact (`R2-CX-2`, `R2-MPE-8`), and the S3 finance source is deliberately T+3. Evaluating lag against wall-clock time means every stored watermark drifts into "stale" simply because days pass — during Round 1 the dataset's own end date had already moved into the future relative to the machine clock, producing a negative lag of −227 hours.

**Decision.** `data.spec.DEMO_NOW` is a fixed notional clock (2026-08-17 12:00). Both `LineageRecord.freshness_lag_hours` and `FreshnessStatus` are computed against it. `LineageRecord.computed_at` remains real wall-clock time, because that is audit metadata about when the query actually ran.

**Rationale.** A freshness panel that reads "stale" on every source regardless of configuration demonstrates nothing. Pinning the evaluation clock makes the S1-fresh / S3-lagging contrast reproducible on any day, including in a recorded demo.

**Consequence.** Lineage and the freshness panel can never disagree, because both read one clock. When this moves beyond a prototype, `DEMO_NOW` becomes `datetime.now()` at a single call site.

---

## ADR-015 — PELT penalty is a dimensionless BIC multiplier, not a fixed constant

**Status:** Adopted
**Date:** 2026-08-22
**Source:** Architecture Part 9.2 step 4; Killick, Fearnhead & Eckley (2012)

**Context.** The KPI contracts shipped `pelt_penalty` as a bare number (8.0 to 12.0). With ruptures' `l2` cost, a segment's cost is a sum of squared deviations, so the penalty carries the units of the metric squared. Measured on the West slice, the residual variance is 4.85e7 against a penalty of 12.0 — seven orders of magnitude apart. PELT returned 65 changepoints across 229 days, one every three days: it was segmenting noise, and the same constant would behave differently again on `conversion_rate` (a proportion) and `orders` (a count).

**Decision.** `pelt_penalty` is now the dimensionless multiplier beta in `pen = beta * sigma^2 * log(n)`, with sigma estimated by MAD from the residual. beta = 1.0 is the BIC penalty and is the value all five contracts carry.

**Rationale.** A penalty expressed in squared rupees cannot be reused across a percentage and a count. The BIC form is the standard remedy, and it makes the contract value mean the same thing for every KPI. sigma comes from the MAD rather than the standard deviation so the event being searched for does not inflate the threshold meant to find it — the same argument that already justified MAD for the z-score.

**Consequence.** `tests/test_detection.py::test_pelt_penalty_is_scale_invariant` asserts that multiplying a series by 1000 leaves the changepoint unchanged, which the previous fixed penalty could not satisfy. Targets hold across beta in [1.0, 3.0]; recall is unaffected across the whole sweep.

---

## ADR-016 — STL smoothers are set so the decomposition cannot absorb the event

**Status:** Adopted
**Date:** 2026-08-22
**Source:** Architecture Part 9.2 step 2

**Context.** Two separate leaks were measured, both silent.

*Trend.* statsmodels defaults the trend smoother to roughly `1.5 * period / (1 - 1.5 / seasonal)`, about 23 days at period 7. That is agile enough to bend into a two-week incident. A planted 25% collapse in the West slice measured **-6.76%** because the counterfactual followed the event down. At a 57-day smoother the same event measured -24.47%, against a ground truth of -24.98%.

*Seasonal.* The statsmodels minimum of 7 lets the weekly shape re-form around a fortnight-long event. On a clean synthetic series a planted -25% event measured **+2.26%** at `seasonal=7` and exactly **-25.00%** at 13 or above.

**Decision.** `trend = max(8 * period + 1, min_history_days + 1)` and `seasonal = max(7, 2 * period + 1)`, both forced odd.

**Rationale.** Both smoothers must be too stiff to track anything the materiality gate would call sustained. Eight cycles comfortably exceeds any such event and is bounded below by the contract's own `min_history_days`; two cycles of seasonal smoothing stops a weekly retail rhythm from reinventing itself fortnightly. Neither is a knife edge — trend smoothers of 57, 91 and 127 recover the same effect to within 1.5pp.

**Consequence.** This was the single largest source of error in Stage 3, and it was invisible from the outcome alone: the pipeline ran cleanly and returned confident, wrong magnitudes. `test_stl_trend_smoother_cannot_track_the_event_it_should_expose` pins it with a planted event and an explicit tolerance.

---

## ADR-017 — Materiality thresholds are calibrated against a measured noise floor

**Status:** Adopted
**Date:** 2026-08-22
**Source:** Architecture Part 9.2 step 6

**Context.** `net_revenue` shipped with `min_rel_effect_pct: 2.0`, authored by intuition. Running the detector across all 68 slices over an event-free holdout period (2025-12-01..2026-05-31, ending before the first injected event) gives a null distribution of the top segment's |relative effect| with **median 3.00%** and **p99 7.90%**. The threshold sat below the median of pure noise, so the gate admitted nearly every slice it was shown — untuned precision was 0.425.

**Decision.** `min_rel_effect_pct: 9.0`, taken from the p99 of that null distribution. `min_abs_effect` stays at 250,000 INR: its own null tops out at 75,172 INR, so it was never the leaking arm.

**Rationale.** The threshold is calibrated on a period containing no injected events, so it is fitted to the data's noise level rather than to the answer key. This matters because the obvious alternative — raising the threshold until precision improves — would have produced a similar number with no defensible basis and no reason to expect it to transfer.

**Consequence.** Only `net_revenue` has been calibrated this way. The other four contracts still carry intuition-authored relative floors and should be given the same treatment before they are trusted; this is recorded as a known limitation rather than silently generalised. A Welch p-value computed on the PELT-selected segment is **not** a valid guard here: the window was chosen to maximise displacement, so the test is circular and returns p < 0.001 on pure noise. It is reported for transparency but never gates alone.

---

## ADR-018 — The revenue identity is evaluated on one analytical population

**Status:** Adopted (deviates from Architecture Part 7.1's stated identity)
**Date:** 2026-08-22
**Source:** Architecture Part 7.1 (the five connected KPIs), Part 10.1 (LMDI)

**Context.** Part 7.1 states the identity as

```
Net Revenue = Sessions x Conversion Rate x Average Order Value x (1 - Refund Rate)
```

Implemented literally — Sessions and Conversion from S2 product analytics, Refund Rate from S3 finance, AOV and Net Revenue from S1 — it closes to only **94.8%** on the West slice. LMDI's entire value proposition is exact, residual-free conservation, so a 5% closure gap is not a rounding annoyance: it makes the guarantee meaningless. The gap was measured and decomposed rather than plugged.

*Finding 1 — the S1/S2 difference is a population mismatch, not a definition or timing one.* `fact_sessions` (S2) is generated **from** `fact_orders` (S1), so the underlying population is identical. Two deliberate distortions separate them: 3.5% of S2 rows carry `region IS NULL` (VPN / opted-out clients, declared in the contract as `known_null_columns`), and hourly session counts carry instrumentation noise. Measured on the West baseline window, a region-filtered S2 session total sits **−4.45%** below S1; remove the region filter and the gap collapses to **−0.12%**. That collapse is the diagnostic: it is the region filter interacting with unknown-geo rows, not a different definition of a session. The conversion *ratio* itself matches to **+0.00%**, because S2 scales sessions and orders together — only the level differs.

*Finding 2 — the fourth factor was the wrong quantity.* Net revenue is `gross − discount − return`. The S3 finance refund rate is `refund_amount / gross` and **excludes discounts entirely**; on the West baseline it reads 0.0838 against a warehouse leakage rate of 0.1345. Using `(1 − refund_rate)` therefore leaves discounts — a component roughly as large as returns — permanently unexplained. This is a genuine definition mismatch between S1 and S3, not a data error.

**Decision.**

1. Add a `sessions` KPI contract sourced from `fact_orders` (S1) under the same filters as Net Revenue, Orders and AOV. Part 7.1 names Sessions as an identity factor but lists only K1–K5, so no contract existed for it.
2. Evaluate the identity as

```
net_revenue = sessions x conversion_rate x average_order_value x net_realisation
```

   with every factor read from S1, where `conversion_rate = orders/sessions`, `average_order_value = gross/orders` and `net_realisation = net/gross`. The product telescopes to net revenue exactly.
3. Report the S1↔S2 and S1↔S3 differences as `SourceReconciliation` records attached to the decomposition — measured, classified and explained — rather than absorbing them into a residual term.

**Rationale.** Chosen over the alternative (keep the cross-source identity and carry a reconciliation term) because a decomposition that does not conserve cannot support the claim LMDI exists to support. A plug term would also be indistinguishable, in the output, from a real driver — which is precisely how a data-integration artefact gets narrated as a business event. The heterogeneous-source story the case asks for is not lost: it is now *explicitly measured and reported* instead of silently degrading the arithmetic.

**Consequence.** Closure is exact (measured gap 0.000000000%, conservation residual 6.9e-14% of the change — floating point only). The deviation from the architecture's literal wording is the fourth factor's name and definition, and it is deliberate. S2 conversion and the S3 refund rate remain first-class KPIs for detection and narrative; they are simply not used as identity factors. `tests/test_attribution.py::test_identity_closes_on_a_single_population` pins the result, and `test_mixed_source_identity_fails_conservation` pins the failure it replaced so the regression cannot return silently.

---

## ADR-019 — A dimension must have redistributed, not merely explain

**Status:** Adopted (extends Architecture Part 10.2)
**Date:** 2026-08-22
**Source:** Architecture Part 10.2 (Adtributor), Part 4.2 (HotSpot / Squeeze as the V2 path)

**Context.** Architecture Part 10.2 selects a dimension when its greedy candidate set clears `T_EP`. Implemented literally, that admits a case it should decline. Construct a cube where the movement lives in the *interaction* — the `(A,X)` and `(B,Y)` cells drop, the others hold:

| | X | Y |
|---|---:|---:|
| **A** | 25 → 15 | 25 → 25 |
| **B** | 25 → 25 | 25 → 15 |

Both marginals are unchanged: `d1` still reads 50/50 and so does `d2`. Neither dimension localises anything. Yet each reaches **EP = 1.00** by naming *every* element, clears `T_EP`, and the engine reported `ATTRIBUTED` on `d1` — a confident answer to a question Adtributor cannot answer.

This is precisely the case HotSpot and Squeeze exist for, and Part 4.2 already records that both are deliberately out of scope for Round 2. The defect was not that we lack them; it was that we did not notice when we needed them.

**Decision.** A dimension qualifies as an explanation only if it clears `T_EP` **and** its candidate set has total surprise above `T_SURPRISE = 1e-9`. When no dimension qualifies, return `MULTI_DIMENSIONAL_CASE` and route to human review.

**Rationale.** Zero Jensen-Shannon divergence is not a small number, it is the statement *prior and posterior are the same distribution* — the dimension's shares did not move, so it carries no localisation information whatever its explanatory power. `T_SURPRISE` is therefore the numerical tolerance on an equality, not a tuned threshold, and it is the one signal that separates a one-dimensional cause from a combination one without implementing an MCTS over the attribute lattice.

Checked in both directions: the NSDI '14 worked example is unaffected (device type carries surprise 0.138), the West event is unaffected (region 4.15e-4), and `test_a_one_dimensional_cause_is_still_attributed` pins that a genuine single-dimension cause is not swallowed by the new rule.

**Consequence.** Non-qualifying dimensions remain in `AdtributorResult.dimensions` rather than being dropped — a reader is entitled to see that data centre X *did* clear the explanatory-power bar and was set aside because its share never moved. `MULTI_DIMENSIONAL_CASE` sets `requires_human_review` and denies causal language, since there is no single slice to make a claim about.

---

## ADR-020 — A `sessions` contract and gateway document access for Stage 5

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 11 (retrieval), Part 8.2 / ADR-011 (the chokepoint)

**Context.** Stage 5 reads documents, not metrics. ADR-011 says exactly one module touches DuckDB, and `tests/test_chokepoint.py` enforces it by scanning the runtime packages. `retrieval/` is a runtime package, so it cannot open its own connection — but `guarded_query` is built around KPI contracts and evidence documents have none.

**Decision.** Add `gateway.documents(source_type, principal)`, read-only, returning raw rows plus a withholding reason. Source-level entitlement is resolved **inside the gateway** via a new `security.entitlements.source_access(principal)`, which reads the same `policy.yaml` that `decide()` does. `retrieval` is added to `RUNTIME_PACKAGES` in the chokepoint test.

**Rationale.** Enforcing at the gateway rather than in the retrieval layer makes the required ordering structural rather than conventional: a document a role may not read is never materialised, so it cannot reach BM25's document frequencies, the dense neighbourhood, or a rank position. A retrieval layer that filtered afterwards would already have leaked the document into the ranking, and "we removed it from the display" is not a defence.

**Consequence.** One precedence rule had to be settled. The `ops_lead` policy denies `S3` wholesale but allowlists `support_tickets`, `market_events` and `deploy_changelog` by name — and those documents live in S3. Checking the source id first would strip an ops lead of the ticket evidence the case explicitly grants them; ignoring it would hand them `finance_adjustments`, which they are not listed for. `SourceAccess.permits` therefore resolves named allow/deny before the coarse source id. `test_ops_lead_is_denied_crm_notes_at_the_source` and `test_unauthorised_documents_are_removed_before_any_scoring` pin both halves.

---

## ADR-021 — Retrieval searches every plausible cause bucket, not the presumed one

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 11.1 step 2 ("cause-bucket keyword sets")

**Context.** The first implementation keyed a single keyword list off the dominant LMDI factor: a `conversion_rate` movement was searched with `payment, gateway, checkout, declined, timeout, card`. On Scenario 1 that works, because E1 really is a gateway failure. On Scenario 2 it fails badly. E2 is a South/Apparel movement whose planted causes are a competitor promotion and a stockout; its dominant identity factor is also `conversion_rate`, so retrieval searched for payment terms and returned *"Payment failed at checkout"* as the top result while the competitor and stockout evidence sat below it. The engine assumed the cause and then found what it assumed.

**Decision.** `CAUSE_BUCKETS` maps each driver to a list of `(bucket, keywords)` pairs, and `build_queries` emits one query per bucket. BM25 and dense run per bucket and RRF fuses across buckets as well as across retrievers.

**Rationale.** A conversion drop has several genuine mechanisms — checkout can fail, stock can run out, a rival can undercut — and which one applies is Stage 6's question, not retrieval's. Fusing separate per-bucket rankings also beats blending the vocabularies into one long query: each bucket's evidence wins its own ranking instead of competing for word overlap in a single blended one.

**Consequence.** On E2 the top six results now carry both sides — *Category price war reported*, *Rival launches festive discounting early*, and *repeated out-of-stock messages on core SKUs* — which is the balanced-evidence behaviour the scenario was designed to produce. Cost is one query embedding per bucket (~23 ms each, three buckets for `conversion_rate`).

---

## ADR-022 — Hypothesis score is a product of movement confidence and evidence fit

**Status:** Adopted (corrects Architecture Part 10.5)
**Date:** 2026-08-23
**Source:** Architecture Part 10.5 (deterministic hypothesis scoring)

**Context.** Part 10.5 specifies one weighted sum:

```
score = 0.30*contribution + 0.15*surprise + 0.15*(1-p) + 0.20*evidence_strength
      + 0.10*temporal_precedence + 0.10*counterfactual
```

That works when the competing hypotheses are different **drivers or slices**, because contribution then genuinely differs between them. Ours are competing **cause buckets** for one driver and one slice — *"was the West conversion drop a platform failure, a stockout, or competitive pressure?"* — and for those, contribution, robustness, the counterfactual, temporal precedence and surprise are all properties of the **movement**. Every hypothesis about that movement inherits them identically.

Measured on Scenario 1 with three hypotheses:

| component | internal_product | internal_inventory | external_competitor | spread |
|---|---:|---:|---:|---:|
| contribution | 1.000 | 1.000 | 1.000 | **0.000** |
| statistical_strength | 1.000 | 1.000 | 1.000 | **0.000** |
| robustness | 1.000 | 1.000 | 1.000 | **0.000** |
| temporal_precedence | 1.000 | 1.000 | 1.000 | **0.000** |
| counterfactual | 1.000 | 1.000 | 1.000 | **0.000** |
| evidence_support | 0.829 | 0.688 | 0.317 | 0.512 |

Eighty per cent of the weight was a constant added to every hypothesis. The scores compressed into [0.863, 0.966] and a textbook high-confidence scenario came out `CONFLICTED`.

**Decision.** Separate the two questions and multiply:

```
score = movement_confidence x evidence_fit x contradiction_multiplier
```

`movement_confidence` (contribution, surprise, robustness, precedence, counterfactual) is computed once and reported on the bundle. `evidence_fit` (bucket alignment, distinct documents, source diversity, cohort signal, temporal tightness) is what ranks the hypotheses. A new `bucket_alignment` term asks whether the source types a cause *would* produce are actually present — a platform failure should leave a deploy record, competitive pressure should leave market events.

**Rationale.** A product rather than a sum because both must hold: a well-established movement with nothing corroborating a particular cause should score low, and so should a well-corroborated cause for a movement that was never established. A sum lets either carry the other. After the change, S1 separates 0.906 / 0.248 (`SUPPORTED`) and S2 stays at 0.739 / 0.663 (`CONFLICTED`) — which is the correct answer to each.

**Consequence.** Two further defects surfaced and were fixed. The separation rule combined an absolute margin and a dominance ratio with `OR`, so the stricter test always bound: a margin of 0.176 was reported as ambiguous because the ratio came to 1.24 against a 1.25 threshold, and the reason string printed the false comparison `margin 0.176 < 0.10`. Margin is now the test, with the ratio applied only in the low-score band. Separately, routine deploy records — a changelog window contains one every few days — were corroborating the product hypothesis in every scenario; a deploy that happens on a schedule is not evidence about a movement that happened once.

`config/scoring.yaml` v3.0.0. Weights remain hand-set and are declared as such: claiming a learned weighting off four labelled examples is exactly what a sharp judge catches.

---

## ADR-023 — Causal language requires a SUPPORTED hypothesis, not merely a passing counterfactual

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 10.3, Part 6.4; extends ADR-017's causal gate

**Context.** Stage 4's counterfactual licenses causal wording when a difference-in-differences shows the movement is specific to the affected slice rather than market-wide. That is a claim about **the movement**, not about **which cause**. Carried onto hypotheses unchanged, every hypothesis for a licensed movement inherited the licence — including a runner-up resting on a single CRM note. On Scenario 1 the second and third hypotheses both displayed *causal language: LICENSED* on one supporting document each, which would have allowed a narrator to write *"competitive pressure caused the decline"* with the counterfactual's authority behind it.

**Decision.** `causal_language_allowed` on a hypothesis is `attribution.causal_language_licensed AND status is SUPPORTED`. When the counterfactual passed but the hypothesis did not separate, the reason records exactly that.

**Rationale.** The counterfactual establishes that something local to this slice moved it. Naming *which* thing additionally requires the evidence to have separated one explanation from the alternatives. A `CONFLICTED` verdict means it did not, and asserting a cause there is the precise error the gate exists to prevent — so on Scenario 2 no hypothesis carries causal language at all, which is correct: with two live explanations you cannot assert either.

**Consequence.** `internal_data_schema` was also made a first-class candidate hypothesis whenever a schema change falls in the evidence window. It is not tied to a driver, because a definition change can move any metric, and it is the one cause whose correct conclusion is "no business action" — it has to be able to compete rather than being unreachable.

---

## ADR-024 — Gate 2 checks the structured claim, not the prose

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 6.3 (enforcement mechanisms), Part 13.2 (Gate 2)

**Context.** The obvious design for a hallucination guard is to generate prose and then check it. That requires parsing intent from natural language, which is the one thing a verifier cannot do reliably — and a verifier that is unreliable in the direction of *accepting* is worse than none, because it converts an unchecked claim into a checked-looking one.

**Decision.** The narrative schema is a list of typed `Claim` objects carrying references into the frozen bundle: `evidence_ids`, `metric_refs`, `hypothesis_id`, `lever_id`, `direction`. Prose is assembled from validated claims. Eleven checks run against the references and the text, and hard violations block delivery.

`Narrative` deliberately has **no `confidence` field**. Confidence is computed deterministically elsewhere; omitting the slot means there is nowhere for a model to hallucinate one, which is a stronger guarantee than an instruction not to.

**Rationale, per check family.** Numeric grounding, driver membership, citation validity and lever membership are set-membership tests — decidable, fast, and not open to argument. Direction consistency compares two things that must agree: the structured field a verifier can check, and the direction words a human actually reads. Dominant-driver coverage is the only check that catches misleading by *selection* rather than by statement, where every individual sentence is true and the narrative still points at the wrong thing.

**Consequence — three deliberate ceilings, stated rather than hidden.**

*Vocabulary, not semantics.* Direction and causal detection match fixed word lists. A sentence conveying a rise without using a rise word passes unexamined. The alternative is a semantic judge, which means a second model whose errors nobody can audit; Part 13.2 already classes the LLM judge as advisory for exactly this reason.

*The allowlist admits cohort figures as well as `metric_facts`.* Both are frozen into the bundle and computed deterministically, so neither can be invented, but the allowlist is wider than the strict reading of Rule 3.

*Structural integers 0–3 pass unconditionally.* No business figure in this system is a bare single digit, and requiring a metric fact for the `1` in `#1` would make every ranked list unverifiable.

Dates are extracted and validated **before** number extraction, then removed from the text. Without that, `2026-07-12` decomposes into 2026, 7 and 12, and a correctly cited date produces three ungrounded-number violations.

**Measured.** Nine hand-written invalid narratives, each carrying exactly one lie and written independently of the checker: 9/9 identified by the expected code, **0 false acceptances**. Six valid narratives including the licensed causal claim and the associative phrasing of a conflicted case: **0 false rejections**.

Two defects surfaced in the deterministic narrative when it was run through its own gate — a cohort statement quoting `baseline_weeks`, which the bundle did not carry, and hypothesis scores quoted in prose with no backing fact. The first was fixed by carrying the field; the second by not stating scores, since a ranking artefact is not a business figure and admitting it would have meant widening the allowlist.

---

## ADR-025 — The narrator has no tools, and failure is a return value

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 3.1 (model selection), Part 6.3 (enforcement), Part 6.4 (the failure ladder)

**Context.** Stage 8 introduces the only model call in the system. Every safety property built in Stages 0–7 depends on that call being unable to do anything except phrase what it was given.

**Decisions.**

*No tools, ever.* The narration request has no `tools` key — not an empty one, absent. Part 6.3 calls this the strongest guarantee in the system because it is architectural rather than behavioural: a model that cannot query cannot fabricate a query result, and no instruction is needed to forbid what the API does not offer. `test_the_client_never_offers_tools` asserts it against the recorded request rather than against the code that builds it.

*Failure is a return value.* A missing key, timeout, rate limit, outage, refusal or malformed output all produce `LLMResponse.ok = False` with a typed reason, and the caller falls back to the deterministic template. An application that raises because a model was slow has made the model load-bearing, which is the dependency this design exists to refuse. Six failure modes are tested; all six degrade.

*The model is never called on a structural abstention.* Sparse history, insufficient evidence and multi-dimensional cases return before any request is built, and telemetry records `llm_calls = 0`. Part 13.1's point is that Gate 1 does not call the model and discard the answer — it never calls it, and that is provable from the telemetry rather than asserted.

*The payload is a projection of the bundle, not the whole object.* Compiled SQL, residual arrays and bootstrap state are withheld: a narrator has no use for them, they would dominate the token budget, and the compiled SQL carries entitlement predicates. Hypothesis scores are withheld too — a score is a ranking artefact, and showing it invites the model into a numeric violation. The measured payload is ~2,950 tokens against Part 3.1's 4–6K budget.

*Model routing is configuration.* `config/models.yaml` v2.0.0 restores Part 3.1's three-route policy — Opus 5 for narration, Haiku 4.5 for intent, Sonnet 5 as fallback. v1.0.0 had defaulted narration to Sonnet and never listed Opus at all. A test asserts that no model name appears anywhere in `llm/`.

**Prompt selection — what was and was not measured.** Three variants exist: `narration_v1_concise`, `narration_v2_evidence_forward` and `narration_v3_constrained`. v3 is configured as the default, and it was chosen on **design grounds, not measured ones**: it states the enforcement mechanism explicitly, so the model knows which of its instincts will be rejected and why.

Part 18 of the Stage 8 brief asks that the choice be made on verification pass rate, latency and cost. **That comparison has not been run**, because it requires a live API key and this environment has none. `eval/run_llm_eval.py --prompts` implements it and will produce the table; until it is run, the default is a designed choice and is recorded here as one. Substituting a plausible-looking number for a measurement is exactly the failure this architecture spends seven stages guarding against, and it would be a poor place to start.

**Consequence.** 55 Stage 8 tests pass against a scripted client, which is what allows a test to assert behaviour under timeout, rate limit and malformed output — cases a live model will not produce on demand. The live evaluation (70 generations, estimated $3.19 from the prices in configuration) is implemented and gated behind `ANTHROPIC_API_KEY`; `--plan` prints the estimate without sending anything.

---

## ADR-026 — Confidence is banded with a base rate, and the deferral rule is not a threshold

**Status:** Adopted
**Date:** 2026-08-23
**Source:** Architecture Part 13.4 (confidence), Part 14.4 (deferral; Mozannar & Sontag 2020)

**Decisions.**

*Confidence is computed, never generated.* Six weighted components from `config/confidence.yaml` v1.0.0, a contradiction multiplier, a band, and a calibration lookup. The narrator's schema has no confidence field (ADR-025), so there is no slot to hallucinate one into.

*One deviation from Part 13.4.* Its formula weights `(1 - p_value)` at 0.20. That p-value is the Welch test on the PELT-selected window, which ADR-017 showed is a post-selection statistic reading p < 0.001 on pure noise — weighting it would put a fifth of the confidence on a number that is high whether or not anything happened. Bootstrap robustness replaces it and answers the same question without being computed on the window selected for being extreme.

*Bands with base rates, never a bare score.* `config/calibration.json` is seeded by `eval/seed_calibration.py` from 64 labelled cases in the ground-truth run: **HIGH 12/12, MEDIUM 1/2, LOW 0/1, INSUFFICIENT 34/49**. Only HIGH clears the ten-case reporting floor, so MEDIUM and LOW report `UNCALIBRATED` — the system says it does not know how often a medium call has been right, because it does not. `is_synthetic` is a stored field, not a comment.

**Three corrections found by running it.**

*The seeder bucketed by the wrong band.* Seeding against an empty table degrades every reported band to `UNCALIBRATED`, so bucketing on the reported band recorded the bootstrap rather than the signal. It now buckets on the raw score band. It also scored abstention on E4 as wrong, when declining to explain 23 days of history is the correct answer.

*A 12/12 calibration made the deferral rule degenerate.* Feeding the raw 1.0 into `(1 - p_model) x cost_of_error` gives a model loss of exactly zero at **every** decision value, so the model arm won every comparison and the cost-sensitive rule silently became "always automate". Twelve correct out of twelve is not evidence of a 100% success rate; it is evidence that no failure has been observed yet. The arithmetic now uses a Laplace-smoothed estimate, `(correct + 1) / (total + 2)` — 12/12 becomes 0.93 — while the display still shows the raw counts, because a reader should see "12 of 12" and not a smoothed decimal.

*Request rights are not approval rights.* An earlier guardrail deferred whenever the persona could not *approve* the lever. It fired on every scenario, leaving the expected-loss arithmetic deciding nothing — which is a worse failure than the one it was guarding against, because a rule that never binds is a rule nobody can evaluate. Automating "escalate to engineering" for an ops lead means auto-raising the *request*, not performing the rollback. `AutomationScope` now records which is meant, and the override fires only when the persona has no rights at all. Four guardrails remain: disruptive levers are never automated, no rights means no automation, `INSUFFICIENT` and below abstains rather than defers, and `UNCALIBRATED` always defers because there is no `p_model` to put in the comparison.

**Consequence.** All three outcomes occur across the scenarios: S1/S5a/S5b/S6 automate (raise the request), S2/S3 review with an analyst packet, S4/S7 abstain across two distinct reasons. Six abstention states carry distinct remedies rather than collapsing into one bucket.

This paragraph was itself stale for one revision — it described the run from *before* the request/approval fix, when the over-broad guardrail still forced S5 and S6 to review. It is the reason for ADR-027: a decision that is restated in prose drifts from the decision that is computed.

---

## ADR-027 — The generated report is the only authoritative statement of a scenario outcome

**Status.** Accepted. **Date.** 2026-08-23. **Supersedes.** Nothing; constrains ADR-026.

**Context.** A Stage 9 consistency audit compared every scenario's terminal decision as *computed* against every place it was *described*. They disagreed. The ADR-026 consequence paragraph said S2/S5/S6 review and S3/S4/S7 abstain; the implementation automates S5a/S5b/S6 and reviews S3. The prose was written from the run that preceded the request/approval fix and was never regenerated, so the fix was recorded one paragraph above a summary that contradicted it.

The same drift had produced a second instance in `eval/recommendation_report.md` itself: the deferral section listed an **approval rights** guardrail that `config/deferral.yaml` had already replaced with `require_persona_any_rights`. A generated report had a hand-written sentence inside it, and only the hand-written sentence was wrong.

Neither error changed a decision. Both would have misled a reader — and one of them was in the document a judge would read.

**Decision.** The scenario table in `eval/recommendation_report.md` is the single authoritative representation of each scenario's terminal decision, and it is generated in full from the objects the pipeline returns. It carries all eight dimensions — confidence band, calibration state, recommendation, automation scope, decision, abstention state, persona, entitlement withholding — so that no consumer has to reconstruct any of them from prose.

Three rules follow:

1. **No hand-written sentence in a generated report may restate a computed value.** Descriptions of *policy* may be prose; statements of *outcome* are interpolated or absent. The guardrail bullets now read from `config/deferral.yaml` rather than paraphrasing it.
2. **ADR consequence paragraphs name outcomes, not tables.** Where an ADR must cite results, it cites them as of a stated run and defers to the report.
3. **The report says so in its own text.** It opens with the sentence that any disagreeing description is stale, which tells a reader who finds two answers which one to trust.

**Also fixed under this audit.** `automation_scope` was being set on `review` outcomes, so a deferred decision carried `execute`. Harmless today because nothing reads scope without reading `automated`, but the field's name is an authorisation claim and it was making one on a decision that had declined to act. Scope is now `NONE` unless the decision automated; the persona's authority remains on the recommendation as `persona_right`, so nothing is lost. **No scenario decision changed.**

**Consequence.** Eight scenarios, one table, eight dimensions. Two vacuous tests were replaced: one asserted a config flag rather than the behaviour it configures, and one asserted `x != y or True`. Writing the replacements surfaced that `L_PRICING_REVIEW` rests on a *single* guard — `finance_director` is both a persona this system runs as and an approver of that lever — where `L_CHECKOUT_ROLLBACK` rests on two. That is correct behaviour today and a single point of failure tomorrow, so it is now recorded in a test that fails if the asymmetry changes. 429 tests in total.

---

## ADR-028 — The evaluation harness is the authoritative executable scenario definition

**Status.** Accepted. **Date.** 2026-08-23. **Extends.** ADR-027.

**Context.** ADR-027 established that `eval/recommendation_report.md` is authoritative for what each scenario *decides*. It left open a prior question: what each scenario *is*. Two answers existed. `data/SCENARIOS.md` defined seven scenarios with personas assigned in Round 1; `eval/run_recommendation_eval.py` ran eight, with different personas on four of them.

Neither document deferred to the other, so the divergence survived undetected until it was looked for directly. It had also survived a hand-edit: a note describing the divergence was written into `data/SCENARIOS.md` and silently erased, because that file is *generated* by `data/generate.py` and the next regeneration overwrote it. The same failure mode as ADR-027's second instance — hand-written prose inside a generated artifact — this time destroying the correction rather than preserving an error.

**Decision.** The harness is the executable definition of a scenario. `data/scenario_manifest.json` and `data/SCENARIOS.md` are generated documentation of it, and a test asserts they agree with `SCENARIOS`/`PERSONAS` in the harness scenario-by-scenario and persona-by-persona. A disagreement is a documentation bug by construction, and it now fails rather than accumulating.

The Round-1 assignment is **preserved on each manifest entry** as `original_spec_persona` / `original_spec_id` with a `divergence_reason`, and rendered as a historical section rather than overwritten. A superseded decision that simply vanishes cannot be audited: a reader who meets the old personas quoted in an older document needs to be able to tell that they were replaced deliberately.

**Why the harness and not the spec.** The Round-1 assignment gave S1 to `priya` and S2 to `arjun`, confounding two variables — a difference between those runs could come from the event or from the role, and no output separated them. The harness varies one factor at a time: S1–S4 hold the persona fixed and vary the event; S1/S5a/S5b hold the event fixed and vary the persona. S5 was a single row naming two personas, so the two runs it implied had no separate identity and neither could be cited; it is now S5a and S5b. This is a design correction, not a convenience.

**Scope.** Documentation and identifiers only. No injected event, slice, window, seed, or generated row changed — the manifest and summary were rewritten from the existing row counts specifically so the warehouse was not rebuilt. `S6` and `S7` were never reassigned. No scenario decision changed; the report is byte-identical in every decision cell.

**Consequence.** Eight scenarios with one definition each, in a file generated from the thing that runs them. Two tests added - the manifest matches the harness, and the superseded assignment is retained with its reason - alongside the existing coverage check, which was renamed to stop asserting "seven". 431 tests in total.

---

## ADR-029 — Gate 1b decides whether anything can be written, not who resolves a tie

**Status.** Accepted. **Date.** 2026-08-23. **Amends.** Architecture Part 12.4.

**Context.** Part 12.4 specifies three outcomes for `route_sufficiency`: `abstain_evid`, `clarify` and `narrate`, where `clarify` fires when the top two hypotheses are within 0.08 of each other with different cause buckets. Wiring that predicate into the graph and running the executable scenarios produced a measured contradiction on S2.

S2's top two hypotheses score 0.7595 (`external_competitor`) and 0.6827 (`internal_inventory`) — a margin of 0.0768, inside the threshold, different buckets. Part 12.4 therefore ends the run at `clarify`.

The deferral engine, reached only if the run continues, classifies exactly the same state as `conflicting_evidence`, routes it to **review**, and builds an analyst packet whose recommended clarification reads *"Two explanations are equally supported and imply different owners. Which is it: …"*.

So two mechanisms were making one judgement, the cruder one fired first, and what it discarded was a packet asking the very question its own abstention wanted asked. The Stage 9 report says S2 reviews; the graph said S2 abstains. One of them had to go.

**Decision.** `route_sufficiency` returns two values, `insufficient` and `narrate`. The split is by kind:

- **Can anything be written at all?** A generation question. Gate 1b owns it.
- **Who resolves a tie?** A decision question. `deferral/` owns it, has owned it since Stage 9, and answers it with a packet rather than a sentence.

Ambiguity has not stopped being interesting: `is_ambiguous()` still computes it and `gate_1` records it on the state for the audit trail. It just no longer terminates a run.

`ABSTAIN_CONFLICTING_EVIDENCE` remains a terminal state, reached through the deferral engine's abstention mapping rather than through Gate 1b.

**The `clarify` node was not deleted, it was corrected.** It now serves the case it was always the right shape for: a request naming a KPI that does not exist, answered by listing the ones that do. That is a question a user can answer. A contract that exists but will not parse still goes to `CONTRACT_ERROR`, because that one is answered by fixing a file, and degrading it into a polite clarification would hide a broken deployment behind a conversational message.

**Consequence.** S2 reaches `REVIEW_REQUIRED` with a packet, matching Stage 9. Two terminals that were previously unreachable in practice are now both reachable and tested.

---

## ADR-030 — A retry cap must be enforced on a counter that failures advance

**Status.** Accepted. **Date.** 2026-08-23.

**Context.** The verify/retry cycle is capped at two narration attempts. The cap is `route_verification`, which compares `state["narration_attempts"]` against `MAX_NARRATION_ATTEMPTS`.

The telemetry wrapper catches exceptions from a node, records the failure and returns an error on the state so the router can decide what it means. When the narrate node *raised* — a malformed client, an unreachable API — the exception escaped before the node returned, so `narration_attempts` was never incremented. `route_verification` saw `attempts == 0` on every pass, and `gate_2 → retry_narrate → gate_2` ran until the process died with a Windows access violation.

It was found by a test whose own fake was wrong: a stub `LLMResponse` missing a required argument raised `TypeError` inside the node. The bad fake was a one-line fix. The unbounded cycle it exposed was the actual defect, and nothing else in the suite would have reached it, because every other path returned normally.

**Decision.** Two changes, at different levels.

1. **A failed generation is an expected condition, not a node fault.** The narrate node catches generation failures itself and returns `narrative=None` with the attempt counter incremented. The budget is spent whether the model answered badly or did not answer at all — those are the same cost.
2. **A structural bound that does not depend on bookkeeping.** The graph runs with `recursion_limit=40` against a longest legitimate path of about 18 nodes. The counter is still the real cap; this catches the class of bug where the counter is the thing that is wrong.

**A third case, distinguished.** No configured client at all is *not* a transient failure, and retrying an absent model is theatre that logs an attempt the system never made. `model_available=False` routes straight to the deterministic template.

**Consequence.** A narrator that raises on every call now terminates `VERIFIED_TEMPLATE` after exactly one retry, asserted by a regression test that counts visits to `gate_2`. The cap is enforced twice — by the router and by the node — because the failure mode of an uncapped retry is unbounded spend on a paid API.

---

## ADR-031 — Runtime handles live in config, and checkpointed types are registered

**Status.** Accepted. **Date.** 2026-08-23.

**Context.** Two serialisation faults, found by running rather than by reading.

*Handles on state.* The LLM client and embedding index were carried on `InsightState` so nodes could stay pure functions of it. The checkpoint serialiser rejected them: `Type is not msgpack serializable: _Client`. The complaint was correct. A checkpoint is an audit record of what a run concluded, and a socket has no place in one.

*Types not registered.* LangGraph 1.2 deserialises unregistered types with a warning that they "will be blocked in a future version". The first fix attempt registered them as one-element tuples; the API wants classes or `(module, name)` pairs, so nothing was registered and the allowlist silently did nothing. `DeferralDecision` came back as a plain `dict`, and `state["deferral"].outcome` raised `AttributeError` deep inside a resumed run.

The test that should have caught it asserted `values.get(key) is not None`. A `dict` is not None. The weak assertion passed while the value was already broken.

**Decision.** Runtime handles are passed through `config["configurable"]` with a `__` prefix, which LangGraph excludes from checkpoint metadata. The allowlist is *derived* from the type modules rather than typed out — every class each module defines, as classes — so it cannot fall behind a newly added type. The round-trip test names the expected class instead of checking for non-None.

**Consequence.** Resume works under `LANGGRAPH_STRICT_MSGPACK=true`, which is the future default: same run id, same bundle hash, every typed object intact. 105 classes across 12 modules are registered. Nothing that is not a finding crosses the checkpoint boundary.

---

## ADR-032 — A run identifier must be unique per execution, not derived from what was asked

**Status.** Accepted. **Date.** 2026-08-24.

**Context.** `ui/state.py` built each analysis run's id deterministically from
scenario and persona: `f"UI-{scenario.id}-{persona_id}"`. The graph's
checkpointer is durable (ADR-031) and keyed by thread id. `compiled.invoke()`
on a thread id that already reached a terminal checkpoint returns that
checkpoint's state rather than executing anything.

The consequence: clicking "Run analysis" a second time for the same
scenario+persona — or, just as easily, re-running after fixing an unrelated
bug elsewhere in the UI — silently returned the *first* run's answer. Nothing
about the returned `RunResult` distinguished a fresh execution from a stale
one; both looked like a complete, successful run. It was found only because a
lineage-string fix (see below) kept failing to appear in a live walkthrough
after being applied and verified by the graph test suite in isolation — the
UI was serving a cached run from before the fix.

A related, sharper case: `ui/components/movement.py`'s materiality chip read
`is_material` as a plain boolean and rendered "Below materiality threshold"
whenever it was false — true for `NO_MATERIAL_FINDING`, but also for
`SPARSE_HISTORY` and `INSUFFICIENT_DATA`, neither of which ever reaches the
materiality check. S4's screen claimed a verdict that was never computed. This
is a different bug from the stale-checkpoint one, but it surfaced in the same
walkthrough pass and belongs in the same record: both are cases where a
rendered sentence stated something more specific than what the system had
actually established.

**Also found in this pass, same root cause as ADR-030's `checks_run`
confusion:** two lineage-string sites in `graph/nodes.py` interpolated
`report.checks_run` — `tuple[CheckResult, ...]`, not a count — directly into
an f-string, producing a raw Python repr of ten dataclass instances inside a
one-line audit answer. Nothing in the Stage 10 test suite caught it, because
every existing test asserted a lineage entry *existed* for "verification",
never what it said.

**Decision.**

1. **`run_id` is fresh per invocation unless the caller supplies one
   explicitly.** `InsightRequest.new_run_id()` always mints a new id when none
   is given. Tests and eval scripts that need reproducible ids (`"F-S1"`,
   `"T-S1"`) still pass one explicitly and are unaffected. `ui/state.analyse()`
   passes none, so every click is a genuine execution. `resume_review` and
   `pending_review` continue to use the *specific* id a run returned, carried
   in session state — resuming a paused run is the one place reusing an id is
   correct, because it is the same run continuing, not a new one starting.
2. **`RunResult` carries `scenario_id`.** The UI's staleness check now
   compares what was actually asked for — `(scenario_id, persona_id)` — rather
   than reconstructing the id scheme it must no longer rely on.
3. **The materiality chip branches on the actual `DetectionOutcome`,** not on
   `is_material` alone, so it can only claim the specific verdict that was
   actually computed.
4. **Lineage answers get a regression guard against raw reprs**
   (`test_lineage_never_carries_a_raw_python_repr`), because the existing
   "does an entry exist" tests are structurally unable to catch a wrong
   answer inside a right entry.

**A second, unrelated widget bug found in the same pass.** `app.py`'s persona
selector used a fixed Streamlit widget key (`"persona_pick"`). A keyed
Streamlit widget ignores a changed `index=` argument on every rerun after the
first — its value lives in `session_state` once set. Loading the app
(default persona `meera`) and then selecting scenario S6 without separately
touching the persona control left the persona at `meera`, silently defeating
S6 — the one scenario built specifically to demonstrate entitlement
withholding for `ops_lead`. Fixed by scoping the key to the scenario id
(`f"persona_pick_{scenario.id}"`), so each scenario's own default persona
takes effect when it is selected, while a manual override within one scenario
still persists across reruns.

**None of the four findings above were caught by reading code.** All four were
caught by generating the real page and reading the real sentence — the
premise `scripts/_walkthrough.py` and `eval/ui_walkthrough.md` were built on.

**Consequence.** Every scenario in the walkthrough now executes fresh on every
run; S4's chip states only the check that actually ran; S6 shows its
withholding by default; lineage answers are guarded against carrying a raw
Python repr again. Four regression tests added:
`test_re_invoking_the_same_scenario_does_not_return_a_stale_run`,
`test_lineage_never_carries_a_raw_python_repr`,
`test_sparse_history_does_not_claim_a_materiality_verdict`,
`test_the_persona_selector_key_is_scoped_per_scenario`.
