# Final submission checklist

---

## Part A — Round 2 requirements → implementation → test → demo → evidence

### R2-MPE — hard acceptance criteria

| ID | Requirement | Implementation | Test | Demo | Evidence | ✔ |
|---|---|---|---|---|---|:---:|
| **MPE-1** | 3–5 KPIs, 2–3 sources, different grains | 6 contracts, sources S1/S2/S3, cadences daily/hourly/weekly | `test_semantic` (15) | S1 driver chart *is* the identity | `eval/attribution_report.md` | ✅ |
| **MPE-2** | Semantic contract | `semantic/kpis/*.yaml` incl. security spec | `test_semantic`, `test_chokepoint` | Audit tab, contract version | every run's lineage | ✅ |
| **MPE-3** | ≥2 personas, different narratives/actions | 3 personas, per-lever decision rights | `test_evidence`, `test_ui` | **S5a vs S5b** (demo beat 7) | `eval/graph_report.md` | ✅ |
| **MPE-4** | Multi-factor movement | E1 −25%, LMDI + Adtributor | `test_attribution` (43), `test_adtributor` (16) | **S1, beats 1–2** | `eval/attribution_report.md` | ✅ |
| **MPE-5** | Low-confidence: clarify or abstain | 6 abstention states, cost-sensitive deferral | `test_recommendation` (60) | **S2, beat 6** | `eval/recommendation_report.md` | ✅ |
| **MPE-6** | Sparse history | Coverage gate; `SPARSE_HISTORY` first-class | `test_detection`, `test_graph_failures` | S4 (optional beat 7) | `eval/detection_report.md` | ✅ |
| **MPE-7** | Role-based entitlement | Row + column + source, before ranking | **`test_security_chain` (9)**, `test_entitlements` (13) | S6 (optional beat 7) | `eval/security_audit.md` | ✅ |
| **MPE-8** | Freshness, method, contribution, confidence, lineage | All five on the bundle | `test_graph_failures` lineage tests | Method + Audit tabs | 15 lineage records/run | ✅ |
| **MPE-9** | LLM vs non-LLM breakdown | 5-layer boundary | `test_no_routing_predicate_reads_a_narrative` | Method tab; 5 epistemic classes | `docs/FINAL_SYSTEM_ARCHITECTURE.md` §4 | ✅ |
| **MPE-10** | Telemetry: latency, calls, tokens, cost | Captured during execution | `test_telemetry_is_captured_during_the_run` | Audit tab, 9 metrics | `eval/final_telemetry_report.md` | ⚠ |

**MPE-10 is ⚠**: latency, node timings, retries and terminal state are
**measured**; model calls, tokens and cost are **0** because no API key exists.
Plumbing implemented and tested with fake clients; live figures are
`LIVE LLM EVALUATION PENDING` and are not estimated.

### R2-OBJ — objectives

| ID | Objective | ✔ | Note |
|---|---|:---:|---|
| OBJ-1 | Detect and prioritise material movements | ✅ | STL+MAD+PELT+materiality |
| OBJ-2 | Reconcile heterogeneous sources | ✅ | 3 cadences; schema-rename stitching |
| OBJ-3 | Rank drivers with appropriate methods | ✅ | LMDI + Adtributor + bootstrap + DiD |
| OBJ-4 | Persona narratives with traceable evidence | ✅ | Every claim cites an id; Gate 2 enforces |
| OBJ-5 | Communicate uncertainty, abstain | ✅ | 6 states; `UNCALIBRATED` where < 10 cases |
| OBJ-6 | Actions with levers, constraints, decision rights | ✅ | `AutomationScope`: request ≠ execute |
| OBJ-7 | Learn from feedback | ⚠ | Implemented and wired; **zero real cycles** |
| OBJ-8 | Security, cost, latency, scalability | ⚠ | Security + latency measured; cost unmeasured; scale untested |

### R2-CX — complexities

✅ CX-1 · CX-2 · CX-3 · CX-4 · CX-5 · CX-6 · CX-7 · CX-8
⚠ CX-9 (feedback typed; **no drift detection**) · CX-10 (config + arithmetic exist; **no live measurement**)

---

## Part B — Deliverables

| ID | Deliverable | File | Status | Remaining |
|---|---|---|:---:|---|
| **R2-DEL-1** | Business Proposal | — | ❌ **NOT STARTED** | See below |
| **R2-DEL-2** | Working Prototype | the repository | ✅ **COMPLETE** | Nothing |
| **R2-DEL-3** | Pitch Presentation | — | ❌ **NOT STARTED** | See below |

### R2-DEL-2 — complete

```bash
pip install -r requirements.txt
python -m data.generate && python -m retrieval.build_index
streamlit run app.py
```

8 demoable scenarios · 573 tests · CI workflow · clean git tree · reproducible
fixtures · no secrets.

### R2-DEL-1 — Business Proposal: what remains

The case asks for problem framing, solution design, target users, business
case and impact, a phased roadmap, and key risks with mitigations.

**What already exists and can be cited directly:**

| Proposal section | Source |
|---|---|
| Problem framing | `docs/ROUND2_CASE.md` + `docs/ROUND1_MASTER.md` (cited research) |
| Solution design | `docs/FINAL_SYSTEM_ARCHITECTURE.md` |
| Target users | 3 implemented personas with real entitlement differences |
| Phased roadmap | `docs/PRODUCTION_EVOLUTION.md` — 8 migrations, each with a trigger |
| Key risks | `eval/judge_defense.md` weak-answer table; `eval/security_audit.md` residual risks |
| Evidence | every report in `eval/` |

**What must be written fresh — and the honest constraint:** the **business
case and impact** section. No revenue, cost-saving or time-saved figure is
supported by anything in this repository, and `eval/claim_audit.md` confirms
none is claimed. The proposal must either (a) present impact as an explicit
modelled scenario with its assumptions stated, or (b) present the *mechanism*
of value and decline to size it. Inventing a number here would contradict the
one thing this project has been consistent about.

### R2-DEL-3 — Pitch Presentation: what remains

**Already written:** `eval/final_demo_script.md` (3-minute structure, beat by
beat, with what not to do) and `eval/judge_defense.md` (24 anticipated
questions with weak answers flagged).

**Must be built:** the slide deck itself. Suggested spine — the three things
from the go/no-go below.

---

## Part C — Final release checks

| Check | Result |
|---|:---:|
| Clean git tree | ✅ |
| Release commit exists | ✅ |
| No secrets committed | ✅ regex scan of staged content |
| No browser profiles | ✅ 16 MB `.chrome_qa_profile` removed and ignored |
| No model artifacts committed | ✅ index gitignored, reproducible |
| No debug/temp files | ✅ |
| Requirements install cleanly | ✅ **fixed in Stage 12** — four blocks were commented out while their imports were live |
| Application starts | ✅ |
| Demo scenarios run | ✅ 8/8, agreeing with the direct-module path |
| Full tests pass | ✅ see final run |
| CI workflow present | ✅ `.github/workflows/test.yml` — ⚠ never executed |
| Deployment commands work | ✅ verified end to end |

---

## Part D — Open items, ranked

| # | Item | Severity | Blocks submission? |
|---|---|---|:---:|
| 1 | **R2-DEL-1** business proposal not written | High | **Yes** — it is a required deliverable |
| 2 | **R2-DEL-3** pitch deck not built | High | **Yes** — it is a required deliverable |
| 3 | Live LLM evaluation pending | Medium | No — template mode is honest and labelled |
| 4 | CI never executed | Low | No |
| 5 | Feedback loop unvalidated | Low | No — stated as implemented, not validated |
| 6 | Corpus diversity still 3.4% | Low | No — documented in the realism audit |

**Items 1 and 2 are the only submission blockers, and both are documents
rather than code.** The prototype (R2-DEL-2) is complete.
