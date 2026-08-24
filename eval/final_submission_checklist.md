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
| **R2-DEL-1** | Business Proposal | `submission/R2_BUSINESS_PROPOSAL.md` + `_SOURCE.md` | ✅ **COMPLETE** | Nothing |
| **R2-DEL-2** | Working Prototype | the repository | ✅ **COMPLETE** | Nothing |
| **R2-DEL-3** | Pitch Presentation | `submission/R2_PITCH_DECK.md` + `_SOURCE.md` + `R2_PITCH_SPEAKER_NOTES.md` | ⚠ **CONTENT COMPLETE** | **Render only** — see below |

### R2-DEL-2 — complete

```bash
pip install -r requirements.txt
python -m data.generate && python -m retrieval.build_index
streamlit run app.py
```

8 demoable scenarios · 573 tests · CI workflow · clean git tree · reproducible
fixtures · no secrets.

### R2-DEL-1 — Business Proposal: complete

`submission/R2_BUSINESS_PROPOSAL.md` — 17 sections, ~5,600 words, with
`R2_BUSINESS_PROPOSAL_SOURCE.md` mapping every claim of consequence to its class
(**[M]** measured · **[S]** synthetic evaluation · **[R]** research-sourced ·
**[A]** assumption · **[I]** illustrative) and its artefact.

**How the business-case constraint was resolved:** option (b). Section 12
presents four *mechanisms* of value — operational, decision, risk and governance
— and declines to size three of them, stating for each what we can evidence and
what we cannot. Only the risk mechanism is backed by measurement. No revenue,
cost-saving or time-saved figure appears anywhere, and the section says why in
as many words.

### R2-DEL-3 — Pitch Presentation: content complete, render outstanding

**Written:**

| File | What it is |
|---|---|
| `submission/R2_PITCH_DECK.md` | 11-slide build spec, row by row, in the Round 1 design-system format |
| `submission/R2_PITCH_DECK_SOURCE.md` | Every slide claim → class → artefact. No number introduced that is not in `R2_BUSINESS_PROPOSAL_SOURCE.md` (§13 lists the repository artefacts that extend it) |
| `submission/R2_PITCH_SPEAKER_NOTES.md` | Slide-by-slide talk track, four timing plans, Q&A index |

**Reconciled, not duplicated:** the speaker notes name
`eval/final_demo_script.md` as authoritative for the live demo and provide a
slide ↔ demo-beat mapping so the two are never performed against each other.
`eval/judge_defense.md` remains the Q&A source; the notes index into it rather
than restating it.

**What remains — rendering only, no content work.** No scripted `.pptx`
workflow is configured in this repository and none was used in Round 1. The
Round 1 path was: build 1600×900 HTML in
`05_Design_System/case-deck-design-system` under `theme-accenture` → export PNG →
place into the official Accenture template (which mandates Arial and supplies the
title, team-details, video and thank-you slides) → export PDF. `R2_PITCH_DECK.md`
carries that procedure and the exact palette in its build notes.

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
| 1 | **R2-DEL-3 not rendered** — deck content written, `.pptx`/`.pdf` not produced | High | **Yes** — the competition accepts a file, not a markdown spec |
| 2 | Live LLM evaluation pending | Medium | No — template mode is honest and labelled |
| 3 | CI never executed | Low | No |
| 4 | Feedback loop unvalidated | Low | No — stated as implemented, not validated |
| 5 | Corpus diversity still 3.4% | Low | No — documented in the realism audit |

**Item 1 is the only remaining submission blocker, and it is a build step rather
than a decision.** Every content question the deck raises is answered in
`R2_PITCH_DECK.md`, and every number in it is traced in
`R2_PITCH_DECK_SOURCE.md`. R2-DEL-1 and R2-DEL-2 are complete.
