# Round 2 requirement traceability

Every row maps a requirement from `docs/ROUND2_CASE.md` to running code, a
test that would fail if it broke, a demonstrable scenario, and where a judge
can see it.

**A requirement is only marked ✅ if it is demonstrable.** A class existing is
not evidence. Where something is partially met, the row says so and says what
is missing — an honest ⚠ is more useful than a ✅ that does not survive a
question.

Evidence base: **571 tests passing, 0 failures** (13:05); 8 scenarios driven
end to end through the real graph (`eval/graph_report.md`, 8/8 agreeing with
the direct-module path).

---

## R2-MPE — Minimum Prototype Expectations (hard acceptance criteria)

### R2-MPE-1 — 3–5 connected KPIs across 2–3 sources with different grains/cadences ✅

| | |
|---|---|
| **Implementation** | 6 KPI contracts, exceeding the 3–5 asked |
| **Files** | `semantic/kpis/{net_revenue,orders,sessions,conversion_rate,average_order_value,refund_rate}.yaml` |
| **Sources & cadences** | **S1** daily (`net_revenue`, `orders`, `sessions`, `average_order_value`) · **S2** hourly (`conversion_rate`) · **S3** weekly (`refund_rate`) |
| **Connected how** | Not merely co-located: `net_revenue = sessions × conversion_rate × AOV × net_realisation` is an exact LMDI identity that closes to **0.000000000%** |
| **Test** | `tests/test_semantic.py` (15), `tests/test_attribution.py::` identity conservation |
| **Scenario** | S1 — the driver chart *is* the identity decomposition |
| **UI** | Workspace → "Why did it move?" |
| **Evidence** | `eval/attribution_report.md` |

Grain differences are load-bearing, not decorative: the S3 weekly refund feed
is stamped T+3, so the most recent week is genuinely unavailable rather than
zero — which is what forces the freshness check to exist.

### R2-MPE-2 — Lightweight KPI/semantic contract ✅

| | |
|---|---|
| **Implementation** | `KPIContract`: definition, formula, drivers, dimensions, detection config, materiality rule, freshness rule, lineage, **security spec** |
| **Files** | `semantic/contract.py`, `semantic/registry.py`, `semantic/kpis/*.yaml` |
| **Test** | `tests/test_semantic.py`; `tests/test_chokepoint.py::test_gate_exposes_exactly_one_query_entrypoint` |
| **UI** | Audit → "Config · …" rows, contract version per run |
| **Evidence** | Every run's lineage records `net_revenue v1.2.0` |

Access restrictions live **in the contract**, not beside it — which is why the
entitlement decision can be computed without touching a database.

### R2-MPE-3 — At least two personas receiving different narratives/actions ✅

| | |
|---|---|
| **Implementation** | 3 personas: `meera` (analytics_lead), `priya` (ops_lead, West-scoped), `arjun` (finance_director) |
| **Files** | `config/personas.yaml`, `security/policy.yaml`, `recommendation/engine.py::persona_right` |
| **Test** | `tests/test_evidence.py::test_two_personas_get_different_bundles_from_the_same_event`; `tests/test_ui.py::test_personas_differ_in_entitlement_not_in_analysis` |
| **Scenarios** | S5a (ops_lead) vs S5b (finance_director) vs S1 (analytics_lead) — **same event**, three readers |
| **UI** | Sidebar "Read as"; masthead shows the active role |
| **Evidence** | `eval/graph_report.md` — identical `pct_delta`, different withheld counts and decision values |

The analytical truth is identical by design and asserted as such. What differs
is entitlement and decision rights: `L_GATEWAY_ESCALATE` is `request` for all
three, so "automate" means *raise the request*, never *perform the rollback*.

### R2-MPE-4 — One multi-factor KPI movement with known drivers ✅

| | |
|---|---|
| **Implementation** | Injected event E1: payment-gateway degradation, −25.0% net revenue, West × Web/Mobile App |
| **Files** | `data/generate.py`, `attribution/lmdi.py`, `attribution/adtributor.py` |
| **Test** | `tests/test_attribution.py` (43), `tests/test_adtributor.py` (16) |
| **Scenario** | S1 / S5a / S5b / S6 |
| **UI** | Workspace driver chart |
| **Evidence** | `eval/attribution_report.md` |

Conversion rate contributes **109.9%** of the movement — more than the whole,
because sessions moved the opposite way and partly offset it. The UI states
that explicitly rather than printing a number that reads as a bug.

### R2-MPE-5 — One low-confidence scenario: clarification or abstention ✅

| | |
|---|---|
| **Implementation** | Six typed abstention states, each with a distinct remedy; cost-sensitive deferral rather than a confidence threshold |
| **Files** | `deferral/engine.py`, `deferral/types.py`, `ui/components/abstention.py` |
| **Test** | `tests/test_recommendation.py` (60), `tests/test_graph_failures.py` |
| **Scenarios** | **S2** conflicting evidence → REVIEW with analyst packet · **S3** thin evidence → REVIEW · **S7** → NO_MATERIAL_EVENT |
| **UI** | Workspace → "AWAITING YOUR DECISION" with the real question |
| **Evidence** | `eval/recommendation_report.md` |

S2's packet asks *"Two explanations are equally supported and imply different
owners. Which is it?"* — a question, not a shrug.

### R2-MPE-6 — One sparse-history / newly launched KPI scenario ✅

| | |
|---|---|
| **Implementation** | Coverage gate before any decomposition; `SPARSE_HISTORY` is a first-class outcome, not an error |
| **Files** | `detection/coverage.py`, `ui/components/abstention.py::sparse_history` |
| **Test** | `tests/test_detection.py`; `tests/test_graph_failures.py::test_sparse_history_is_a_path_not_an_error`; `tests/test_ui.py::test_sparse_history_does_not_claim_a_materiality_verdict` |
| **Scenario** | **S4** — `NewLaunch`, 52 of 56 required days |
| **UI** | "52 days of history are available. A seasonal baseline needs 56." + "about 4 more days" |
| **Evidence** | `eval/detection_report.md` |

The screen deliberately does **not** show a materiality chip: detection stops
at the coverage gate, before materiality is ever evaluated. Claiming "below
threshold" would assert a check that never ran.

### R2-MPE-7 — One role-based security/entitlement scenario ✅

| | |
|---|---|
| **Implementation** | Row filter + column mask + source denial, resolved before any read; retrieval filtered **before** ranking |
| **Files** | `security/entitlements.py`, `security/policy.yaml`, `semantic/gateway.py`, `retrieval/engine.py` |
| **Test** | `tests/test_entitlements.py` (13), **`tests/test_security_chain.py` (9)**, `tests/test_chokepoint.py` (10) |
| **Scenario** | **S6** — `priya` (ops_lead) denied `crm_notes`; 1 item withheld |
| **UI** | "Some evidence is unavailable for your role… (1 item withheld)" |
| **Evidence** | `eval/security_audit.md` |

`test_security_chain.py` follows one restricted source through all six stages
(SQL → retrieval → ranking → bundle → LLM payload → UI) and asserts absence at
each, **paired with proof a permitted reader does see it** — so no assertion
passes merely because data is missing.

### R2-MPE-8 — Evidence: freshness, method, contribution, confidence, lineage ✅

| Element | Where | Evidence |
|---|---|---|
| **Freshness** | `semantic/freshness.py`; `FreshnessRef` on the bundle; `freshness_lag_hours` per evidence item | Method tab; "Source lag at read time" on evidence cards |
| **Method** | `DetectionResult.method`, `AttributionResult.method`, `bundle.methods_used` | Method tab cards, read from run metadata not hard-coded |
| **Contribution** | LMDI per-driver contribution + share | Workspace driver chart |
| **Confidence** | 6 weighted components, banded, Laplace-smoothed calibration | Workspace reliability block |
| **Lineage** | 15 records accumulated *during* the run | Audit tab |
| **Test** | `tests/test_graph_failures.py::test_lineage_answers_every_question_the_brief_lists`, `test_lineage_is_accumulated_not_rebuilt_at_the_end` | |

Lineage is accumulated by the node that answers each question, not rebuilt at
the end — asserted by checking the records carry *different* timestamps.

### R2-MPE-9 — Clear breakdown of LLM vs non-LLM processing ✅

| | |
|---|---|
| **Implementation** | Five-layer boundary: deterministic / statistical / retrieval / LLM / human |
| **Files** | `docs/FINAL_SYSTEM_ARCHITECTURE.md` §4; `graph/routing.py` |
| **Test** | `tests/test_graph_routing.py::test_no_routing_predicate_reads_a_narrative` — reads the predicate **source**, so a predicate that started consulting model output fails even if behaviour looked right |
| **UI** | Method tab; Part 5 epistemic classes visually distinguish fact / analysis / evidence / hypothesis / recommendation |

Three structural guarantees: the narration request has **no `tools` key**;
`Narrative` has **no `confidence` field**; **no routing predicate reads model
output**. Each is architectural, not a prompt instruction.

### R2-MPE-10 — Runtime telemetry: latency, model calls, tokens, cost ⚠

| | |
|---|---|
| **Implementation** | Per-node telemetry captured *during* execution; run-level aggregates |
| **Files** | `graph/telemetry.py`, `graph/types.py::NodeTelemetry` |
| **Test** | `tests/test_graph_failures.py::test_telemetry_is_captured_during_the_run_not_reconstructed` |
| **UI** | Audit tab — 9 metrics + per-node timing table |
| **Evidence** | `eval/final_telemetry_report.md` |

**Measured:** total runtime, per-node latency, retrieval time, deterministic
time, graph overhead (13–40 ms), retry count, terminal state.

**⚠ Not measured:** model latency, tokens, cost — all **0** because no
`ANTHROPIC_API_KEY` exists. The plumbing is implemented and tested with fake
clients; the live figures are `LIVE LLM EVALUATION PENDING` and are **not**
estimated.

---

## R2-OBJ — Round 2 objectives

| ID | Objective | Status | Evidence |
|---|---|:---:|---|
| **R2-OBJ-1** | Detect and prioritise material movements | ✅ | STL + MAD + PELT + materiality; `eval/detection_report.md` |
| **R2-OBJ-2** | Reconcile data across heterogeneous sources | ✅ | 3 sources, 3 cadences; schema-change stitching (`marketplace`→`Marketplace`); ADR-018 |
| **R2-OBJ-3** | Identify and rank drivers using appropriate methods | ✅ | LMDI + Adtributor + bootstrap + DiD; `eval/attribution_report.md` |
| **R2-OBJ-4** | Persona-specific narratives with traceable evidence | ✅ | 3 personas; every claim cites an evidence id; Gate 2 enforces it |
| **R2-OBJ-5** | Communicate uncertainty; abstain when appropriate | ✅ | 6 abstention states; banded calibrated confidence; S2/S3/S4/S7 |
| **R2-OBJ-6** | Actions grounded in levers, constraints, decision rights | ✅ | 7-lever catalogue; `AutomationScope` separates *raise request* from *execute* (ADR-026) |
| **R2-OBJ-7** | Learn from analyst and business-user feedback | ⚠ | 5 typed outcomes routed to named artifacts; 2 update live. **Loop is implemented, not exercised** — no analyst has used it |
| **R2-OBJ-8** | Realistic security, cost, latency, scalability constraints | ⚠ | Security & latency measured. **Cost unmeasured** (no key); **scalability not tested** — single process by design |

### On R2-OBJ-7 and R2-OBJ-8

`feedback/store.py` implements five outcomes with `ROUTING` naming each
consumer, and only `accepted` and `escalated` update live — because both are
counters needing no model. No fine-tuning, no auto-applied prompt changes.
That is a defensible design, but the loop has run zero real cycles: the
calibration table is seeded from 64 synthetic cases, and `p_human` in
`config/deferral.yaml` is **seeded, not measured**.

---

## R2-CX — Complexities addressed

| ID | Complexity | Status | Where |
|---|---|:---:|---|
| R2-CX-1 | Multiple interacting drivers | ✅ | LMDI identity; offsetting factors shown explicitly |
| R2-CX-2 | Different cadences, grains, quality, coverage | ✅ | S1 daily / S2 hourly / S3 weekly T+3; coverage gate |
| R2-CX-3 | Inconsistent KPI definitions and calendars | ✅ | Semantic contracts; S7 schema-rename artefact caught, not explained away |
| R2-CX-4 | Sparse history | ✅ | S4 |
| R2-CX-5 | Statistical **and** business materiality | ✅ | Both legs; S7 fails the business leg while passing the statistical one |
| R2-CX-6 | Contradictory evidence, confidence calibration | ✅ | S2; contradiction multiplier; `UNCALIBRATED` band |
| R2-CX-7 | Role-based personalisation | ✅ | S5a/S5b/S6 |
| R2-CX-8 | Row-, column-, domain-level security + auditability | ✅ | All three enforced; append-only `audit_log`, now correlated per run |
| R2-CX-9 | Drift, feedback, continuous evaluation | ⚠ | Feedback typed and routed; **drift detection not built** |
| R2-CX-10 | LLM economics — model, tokens, latency, caching, cost | ⚠ | Routing and price config exist; cost arithmetic implemented; **no live measurement** |

---

## R2-DEL — Deliverables

| ID | Deliverable | Status |
|---|---|:---:|
| **R2-DEL-1** | Detailed Business Proposal | ⚠ **Not this repository's scope.** Technical evidence a proposal would cite is here (`eval/`, `docs/`); the proposal document itself is not written |
| **R2-DEL-2** | Working Prototype | ✅ `streamlit run app.py`; 8 demoable scenarios; 571 tests |
| **R2-DEL-3** | Pitch Presentation | ⚠ **Not built.** Deferred to the final polish stage |

---

## Summary

| | Count |
|---|---:|
| Fully demonstrable ✅ | **19** |
| Partial, with the gap stated ⚠ | **7** |
| Not met ❌ | **0** |

Every ⚠ has the same root in one of three places: **no API key** (cost,
tokens, live LLM quality), **no real users yet** (feedback loop, `p_human`), or
**deliberately out of scope** (proposal, pitch, drift detection, scaling).

None of them is a claim that could not be substantiated on request.
