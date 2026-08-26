# Final transmission audit

The product/judge audit scored the submission **74/100 — strong contender**,
with one conclusion driving everything below:

> **The product is stronger than the pitch currently communicates.**

This pass closed the transmission gap. **No analytical architecture changed.**
No agents, GraphRAG, vector database, real-time infrastructure or new models
were introduced. Three UI additions were made — all of them surface data the
engine already produced — plus a set of claim corrections that made several
numbers *smaller* or more qualified.

---

## 1. What changed

### Pitch and rendering

| # | Item | Before | After |
|---|---|---|---|
| 1 | **Hero screenshot cropped** | `object-fit: cover` on a 1400×3118 portrait capture hid the driver chart, the 109.9% figure, the evidence count, the reliability block and the "Raise the request" button | Untouched capture split at a section boundary and shown as **two adjacent panels**. All five elements now visible and legible at presentation scale. Nothing redrawn, no aspect distortion |
| 2 | **Abstention arrived too late** | First appeared on Slide 05; the opening four slides read as a generic BI copilot | Slide 03 now carries a red-bordered card: *"…and when the evidence conflicts, this screen does not appear at all"*, pointing at S2. No new slide added |
| 7 | **Business value under-argued** | A single card about analysts | Four mechanism cards on Slide 11 — **faster diagnosis · safer decisions · governed action · auditability** — each tied to something already built, with *"No ROI figure is claimed anywhere in this project"* stated in the kicker |

### Claim corrections — every one of these made a claim weaker

| # | Claim | Before | After |
|---|---|---|---|
| 3 | Outcome split | **50% / 25% / 25%**, unqualified | **4 / 2 / 2 of 8**, with *"across the 8 synthetic demonstration scenarios — a set built to exercise every terminal state. These are NOT production workload rates"* rendered on the slide itself, not hidden in speaker notes |
| 4 | Verification | **"0% verification failure rate"** | **Removed.** Every narrated run took the deterministic template path, because no API key is configured — the figure measured the template's agreement with the gate, not a model's. Replaced with *"3/3 injected corruption classes rejected"* and *"10/10 corrupted narratives blocked"*. Slide 06 now states plainly: **verification mechanism tested ≠ live LLM reliability measured** |
| 5 | Retrieval | `final_evaluation_report.md` still carried the pre-realism figures (BM25 p@5 0.810, RRF MRR 0.964) **and** the stale conclusion *"hybrid did not beat BM25"*; the deck had over-corrected to *"the first evidence the hybrid retriever earns its place"* | Both wrong, in opposite directions. Now: BM25 0.552/0.654 · **Dense 0.567/0.778** · RRF 0.552/**0.697**. Conclusion: corpus realism removed a lexical shortcut; **dense** became the stronger single method under paraphrase; **fusion did not beat dense** — RRF recall@10 sits *between* the two. Hybrid is retained as a **robustness mechanism**, explicitly not as a measured win |
| 6 | Detection | Led with **1.000 / 1.000** | Leads with **0 false positives across 48 evaluated clean slices** — the half a generator cannot rig. Injected-event recall of 1.000 reported second with its methodology limit attached |

### UI — three additions, no new computation

| # | Item | What was built |
|---|---|---|
| 9 | **Evidence visibly real** | `render_summary` showed counts only. It now renders up to **1 contradicting + 2 supporting** real items — source, timestamp, excerpt — reusing the existing `_item_card`. Contradicting leads, because a dissenting document changes a decision more than a third confirming one. Full set still one click away |
| 10 | **KPI time-series** | New `ui/components/kpi_series.py`. Reads `decomposition.dates/observed/trend` and `changepoint_dates` straight off `DetectionResult` — **nothing is computed in the UI**. Shows the series, the STL trend, the investigation window and the detected changepoint |
| 8 | **Colour semantics** | Resolved as **Option A**, and it exposed a false claim in our own audit |

**On item 8, in detail.** `eval/growth_design_ux_mapping.md` asserted red was
used *"only"* on contradicting-evidence cards and hard violations. That was
false and the S1 hero screenshot disproves it at a glance: `drivers.py` paints
the conversion-rate bar (−57,959) red. Resolved in favour of the chart — red
means down is the stronger mental model in a revenue decomposition, and
recolouring to protect a narrower reservation would cost more comprehension
than the reservation was worth. The rule is now the broader, true one:
**red = adverse** (negative contribution, or evidence arguing against the
hypothesis); **green = favourable**. The driver chart states the rule inline
beneath the bars, so UI and documentation now agree at the point of use.

### Demo (item 11)

Restructured so the differentiator lands at **1:30 instead of 2:15**:

`0:00 what moved` → `0:20 why` → `0:45 evidence + reliability` → `1:10 action`
→ **`1:30 introduce conflicting evidence`** → **`2:00 the system refuses to choose`**
→ `2:30 entitlement or audit trail`

The two beats that previously delayed S2 were folded into the beats they belong
to. Rationale recorded in the file: everything before 1:30 is legible as a
competent BI copilot, so arriving at the refusal after the judge has already
formed a category judgement wastes it.

---

## 2. Live LLM status

**`LIVE LLM EVALUATION PENDING` — unchanged, and nothing was fabricated.**

No `ANTHROPIC_API_KEY` is present in the environment, no `.env`, no
`.streamlit/secrets.toml`. `eval/run_llm_eval.py` remains implemented and unrun.
First-pass verification rate, retry rate, fallback rate, latency, tokens and
cost are **unmeasured and not estimated**.

The pass tightened wording so nothing implies otherwise — item 4 above exists
precisely because "0% verification failure rate" read like a live-model result
and was not one.

---

## 3. Validation

| Check | Result |
|---|---|
| Full test suite | **574 passed, 0 failed** |
| All 8 scenarios render | **8 / 8** via `scripts/_walkthrough.py` |
| Deck re-rendered | 11 slides → `submission/R2_BUSINESSINTELLIGENCE_PITCH.pdf` |
| Slides inspected as images | Yes — 03, 06, 07, 09, 11 re-inspected after changes |
| Hero screenshot uncropped | **Verified in the rendered PNG:** driver chart, 109.9%, evidence count, reliability block and "Raise the request" all visible |
| Abstention visible early | **Slide 03** |
| Evidence visibly shown | `SUPPORTS`/`CONTRADICTS` cards present in rendered S1 output; drill-down pointer confirms `render_summary_items` fired |
| KPI series renders | S1 annotated; **S7 shows 0 changepoint/window annotations** and the caption *"detection did not find a material event, so nothing here is annotated as one"*; S4 likewise unannotated |
| Stale numbers | 571 → 574; corpus 1,341 → 1,336; retrieval figures replaced |

**The S7 check is the one that mattered.** A chart that annotated a changepoint
on a schema-rename artefact would assert an event the system explicitly
declined to call — the exact habituation failure the materiality gate exists to
prevent. Annotations are gated on `DetectionOutcome`, not on whether the
underlying fields happen to be populated.

---

## 4. Updated pitch strengths

1. **The differentiator is now unmissable and early.** Slide 03 flags it, Slide 05 proves it, Slide 07 quantifies it, the demo reaches it at 1:30.
2. **The hero slide finally shows the product.** The single strongest asset — a real screenshot of a working system — was being cropped in half.
3. **Evidence is visible rather than counted**, in a product whose entire argument is that it does not ask to be taken on trust. That gap was the sharpest thing the audit found.
4. **The claim discipline now survives a hostile read.** Three claims were weakened in this pass and one was found false in our own UX audit. A submission that corrects itself downward under scrutiny is more credible than one that never needs to.
5. **The KPI chart closes a BI-literacy gap.** A BI audience expects to see the series before accepting a decomposition of it.

---

## 5. Remaining weaknesses

Ranked, and none of them closed by this pass because none could be honestly:

| # | Weakness | Why it remains |
|---|---|---|
| 1 | **No live LLM evaluation** | No API key. The harness exists and is unrun |
| 2 | **All evaluation is synthetic** | Ground truth is known by construction. The largest open risk |
| 3 | **No baseline time-to-explanation** | Therefore no time-saving or ROI claim is possible, and none is made |
| 4 | **No authentication** | Persona is a dropdown. Authorisation is real and tested; identity is not |
| 5 | **Only the HIGH confidence band is calibrated** | MEDIUM and LOW report `UNCALIBRATED` |
| 6 | **Feedback loop unvalidated** | Implemented, typed, wired — zero real cycles |
| 7 | **Hybrid retrieval is unproven** | Now stated outright: this evaluation does not show RRF beating dense. A single-retriever dense configuration is a legitimate thing for a pilot to test |
| 8 | **~2 concurrent users** | DuckDB single writer plus audit-on-read |

---

## 5b. Final claim-consistency sweep

Every occurrence of the audited terms was classified. **CURRENT** = a live
submission-facing claim. **HISTORICAL** = a record of what was true at an
earlier stage, deliberately preserved.

| Term | Verdict | Notes |
|---|---|---|
| `50%` / `25%` | **CURRENT, corrected** | Now rendered as counts (**4 / 2 / 2 of 8**) with percentages parenthetical, and the demonstration-set qualifier at the point of use in `slide-07`, `R2_PITCH_DECK.md`, `R2_BUSINESS_PROPOSAL.md` §10 and both source mappings |
| `0%` (verification failure) | **REMOVED from all submission-facing material** | Was still present in `R2_BUSINESS_PROPOSAL.md` §10 after the first pass; removed with an inline explanation. Retained in `eval/final_telemetry_report.md` as a raw telemetry row, now carrying a ⚠ and the reason it is not quoted anywhere |
| `1.000` | **SYNTHETIC EVALUATION, reframed** | Never leads. Every occurrence is labelled *injected-event recall* with the construction limit attached |
| `0.778` / `0.697` / `0.654` | **SYNTHETIC EVALUATION, current** | Consistent across proposal §10, both source mappings, `slide-09`, `final_evaluation_report.md` §3 |
| `574` | **CURRENT** | Normalised across the checklist (was 573), `round2_traceability.md`, `test_strategy.md`, `final_telemetry_report.md` and the `prototype_readiness.md` top matrix |
| `571` | **HISTORICAL — preserved deliberately** | Three places: the Stage 12 section of `prototype_readiness.md`; the DuckDB-contention signature `571 → 439 collected` in `test_strategy.md`, where the numbers *are* the evidence; and `product_judge_audit.md`, which flagged the inconsistency and must keep its own finding legible. Also **not** a test count in `74,571` / `53,571` INR — currency, left alone |
| "hybrid retrieval" | **CURRENT, corrected in four more places** | `BRIGHTDECK_PROMPT.md`, `R2_BUSINESS_PROPOSAL_SOURCE.md` (two rows, one of which had it exactly backwards), and the **generator** `eval/run_retrieval_eval.py` |
| "dense retrieval" | **CURRENT** | Correctly stated as the stronger single method, and as justifying an embedding model rather than fusion |
| "confidence" | **CURRENT** | Always a band plus a track record; `Narrative` has no `confidence` field. `UNCALIBRATED` below the ten-case floor |
| "causal" | **CURRENT** | Always *licensed*, never asserted. Denied on S3 |

### Two findings worth naming

**1. The hybrid conflation had spread further than the first pass caught.**
Four additional occurrences survived, including one in
`R2_BUSINESS_PROPOSAL_SOURCE.md` that was **exactly inverted** — it marked
*"hybrid is insurance we can afford"* as **superseded**, when that framing is
the accurate one and *"hybrid earns its place"* was the error. Corrected.

**2. `eval/retrieval_report.md` is generated, and its prose was wrong.**
It asserted *"RRF matches the best single retriever on recall@10 and MRR"* —
true of the pre-realism corpus, false now (RRF 0.697 vs dense 0.778). Because
the file carries `Generated by python -m eval.run_retrieval_eval`, a hand-edit
would have been erased on the next run — the same trap this project already hit
once with `data/SCENARIOS.md`. **The fix went into the generator**, at
`eval/run_retrieval_eval.py`.

### MRR framing (audit item 2B)

MRR is **kept** — it is a real metric and the retrieval tables report it
alongside precision@5 and recall@10. What was removed is its use as *proof*:
`R2_BUSINESS_PROPOSAL_SOURCE.md` described RRF's 0.838 as **"Best MRR of the
three"**, which presented a 0.005 lead over BM25 on 14 queries as a result.
Every current discussion is now centred on **recall@10**, which is the
decision-relevant metric here because the bundle builder takes the top-k rather
than only the first hit.

---

## 6. Claim audit status

`eval/claim_audit.md` updated. Every quantitative claim in the deck traces to
`R2_BUSINESS_PROPOSAL_SOURCE.md` or a current `eval/` report. Corrections
applied in this pass are recorded there rather than silently overwritten —
including the hybrid-retrieval over-correction, which is now logged as *"partly
superseded, and re-corrected"* rather than left reading as a win.

Terms searched for and still absent from all user-facing material: customer
savings · enterprise ROI · adoption numbers · market share · productivity gain ·
unqualified "accuracy" · "production-ready" · "real-time" · "autonomous" other
than as a negation.

---

## 7. Score reassessment

**Not reassessed, deliberately.** The 74/100 came from an independent audit;
re-scoring our own submission against our own fixes would be exactly the kind
of self-certification this project's evidence discipline exists to prevent. What
can be said factually is which of the audit's findings are now closed:

| Audit finding | Status |
|---|---|
| Hero screenshot cropped | **Closed** — verified in the rendered image |
| Abstention too late | **Closed** — Slide 03 and demo at 1:30 |
| 50/25/25 unqualified | **Closed** — qualifier at point of use |
| 0% verification failure misleading | **Closed** — claim removed and reframed |
| Stale retrieval evaluation | **Closed** — figures and conclusion both corrected |
| Detection headline overstated | **Closed** — false positives lead |
| Business value under-argued | **Closed** — four mechanisms, no fabricated ROI |
| Growth.Design colour contradiction | **Closed** — and a false claim in our own audit corrected |
| Evidence counted not shown | **Closed** — real items on the default screen |
| KPI visualisation missing | **Closed** — series, trend, changepoint, window |
| Live LLM evaluation | **Open** — no key; unchanged and unfabricated |

Ten of eleven closed. The eleventh cannot be closed without a credential, and
inventing it would forfeit more than it would win.
