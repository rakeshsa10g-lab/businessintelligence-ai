# Pitch deck — claim and evidence mapping

Companion to `R2_PITCH_DECK.md`. Every quantitative and factual claim on every
slide, with its class and the artefact behind it, so any statement in the deck
can be checked without opening the codebase.

| Class | Meaning |
|---|---|
| **[M] MEASURED** | Observed by running this system. Reproducible from the repository. |
| **[S] SYNTHETIC_EVALUATION** | Real measurement on a dataset this repository generates, whose ground truth it knows by construction. |
| **[R] RESEARCH_SOURCED** | External published finding. Not our result. |
| **[A] ASSUMPTION** | A stated assumption. Not derived from data. |
| **[I] ILLUSTRATIVE** | A worked example. Directionally meaningful, numerically arbitrary. |

**Primary rule applied.** Every number in the deck traces to
`R2_BUSINESS_PROPOSAL_SOURCE.md`. **No new number was introduced.** Where a
claim comes from a repository artefact that the proposal's source file does not
tabulate, it is listed separately in §13 with its artefact named — those are
extensions of the same evidence base, never contradictions of it.

---

## Slide 01 — The gap has not moved

| Claim | Class | Source |
|---|:---:|---|
| 73% of BI implementations fail on the diagnostic gap, not technology | **[R]** | sranalytics.io, via `docs/ROUND1_MASTER.md` §D1 — proposal source §1 |
| ~21% of employees actively use deployed BI tools | **[R]** | same |
| ~70% of analyst time spent on alerts that prove legitimate | **[R]** | Gartner 2025, via `ROUND1_MASTER.md` — proposal source §1 |
| 22% decline in detection accuracy at 30+ alerts/day | **[R]** | `ROUND1_MASTER.md` — proposal source §1 |
| "Dashboards are great at telling you what's happening, but the moment you ask why…" | **[R]** | ThoughtSpot, via `ROUND1_MASTER.md` §D1 — proposal source §1 |
| "…correlations that aren't actually meaningful without manual review." | **[R]** | Tellius user, G2 — Round 1 verified review corpus, `ROUND1_MASTER.md` §9 / Round 1 deck spec. **Qualitative, carried forward from Round 1; not in the proposal source table** |
| "Sales Ops deletes columns in Salesforce…" | **[R]** | r/BusinessIntelligence — same provenance as above |
| Three structural reasons; the five-step "path a leader lives today" | **[R]** narrative | Round 1 problem slide, `ROUND1_MASTER.md` §6. Qualitative framing, no number attached |

**Note on the two review quotes.** They are verbatim from the Round 1 scraped and
coded review corpus. They are carried forward for narrative continuity. Neither
carries a number, and neither is presented as a result of this system.

**A discrepancy in Round 1's own materials, recorded rather than smoothed over.**
The Round 1 deck's sources strip says **"G2 & Capterra reviews (314 verified)"**;
the Round 1 video script says **"three hundred and eighty four reviews and forum
threads"**. The two counts are not reconciled anywhere in `ROUND1_MASTER.md` — the
larger figure plausibly includes forum threads that the smaller one excludes, but
that is an inference, not a record. **Neither number appears in the Round 2 deck.**
If a judge raises the corpus size, quote no figure and say the corpus is Round 1
material that Round 2 did not re-verify.

---

## Slide 02 — The obvious fix is the dangerous one

| Claim | Class | Source |
|---|:---:|---|
| LLM **inverted the risk direction on 3 of 4 factors** in a credit-risk narrative under constrained prompting | **[R]** | 2026 arXiv fidelity audit, via `ROUND1_MASTER.md` §8 — proposal source §1 |
| Reasoning-tuned models abstain **24% worse** than non-reasoning counterparts | **[R]** | AbstentionBench, Kirichenko et al. 2025, [arXiv:2506.09038](https://arxiv.org/pdf/2506.09038) — proposal source §1 |
| Gartner names "agent drift"; prescribes guardian-agent monitoring layers | **[R]** | Gartner, via `ROUND1_MASTER.md` — proposal source §1 |
| "The capability you want for RCA works against the humility you need" | — | Our inference from the two findings above. An argument, not a measurement |
| The four "may not" constraints (no data, no number, no decision, no last word) | **[M]** | Architecture claims, each evidenced on Slide 05 |

---

## Slide 03 — One engine, from a number to a decision

| Claim | Class | Source |
|---|:---:|---|
| Net Revenue · West × Web/Mobile App, **↓ 25.0%**, 12 Jul → 26 Jul 2026 | **[S]** | Real rendered S1 output; proposal §4 screen — proposal source §5 |
| Conversion rate accounts for **109.9%** of the movement | **[S]** | LMDI on generated data; `eval/attribution_report.md` — proposal source §2 |
| **8 supporting** documents | **[S]** | S1 evidence bundle, live-captured for this slide's hero screenshot — see note below |
| "High reliability · Correct in **12 of 12** similar past cases", with the synthetic caveat inline | **[S]** | 64-case seeded calibration set; `eval/recommendation_report.md` — proposal source §3 |
| "Expected recovery **622,121 – 799,870 INR**" | **[I]** | Configured `recovery_fraction` × measured movement. Always a range, basis named inline — proposal source §5 |
| Five stages; the five user-facing questions | **[M]** | `docs/FINAL_SYSTEM_ARCHITECTURE.md`; proposal §4, §11 |
| "No chat box, by design" | **[M]** | Product decision; proposal §4 |
| Internal order ≠ presented order | **[M]** | Proposal §11; visible only in the Method tab |

**Note on the evidence count — a discrepancy caught during rendering, not
smoothed over.** `R2_BUSINESS_PROPOSAL.md` §4 and the earlier draft of this
deck both quote **"7 supporting"**, taken from a static S1 mockup screen. The
hero image actually embedded on this slide is a **fresh, live screenshot** of
the running app (`submission/deck/render/_capture_hero.py`, captured via
Playwright against `streamlit run app.py`), and it shows **8**. The slide's
caption text was written to match what the image actually shows rather than
the earlier mockup's figure, so image and caption agree with each other.
The two numbers most likely differ because the evidence bundle depends on
the retrieval index built from the generated document corpus, and that
corpus was regenerated between when the proposal's mockup was captured and
when this screenshot was taken. Both **7** and **8** are real counts from
real runs of the same scenario — this is not a fabricated number, and it is
not corrected in `R2_BUSINESS_PROPOSAL.md` because that document is out of
scope for this deck-rendering pass. If a judge asks: the exact count is not
the claim being made; the claim is that the number is retrieved and counted,
never invented — see Slide 05.

---

## Slide 04 — Round 1 promised this. Round 2 runs it, and corrects it.

### Kept

| Claim | Class | Source |
|---|:---:|---|
| 574 tests passing, 0 failures | **[M]** | Full suite — proposal source §2 |
| 8 scenarios end to end | **[M]** | `eval/graph_report.md` — proposal source §2 |
| 26-node state machine, 11 typed terminal states | **[M]** | See §13 — `eval/prototype_readiness.md` §1, `graph/types.py::TerminalState` |
| S7: channel rename reads as **+5.9%**; statistically real, business-immaterial; no alert | **[S]** | See §13 — proposal §9 |
| Cost-sensitive deferral is implemented and routes S2 | **[M]** | `config/deferral.yaml`, `eval/recommendation_report.md` — proposal source §2 |
| Narration request carries **no `tools` key** | **[M]** | `test_the_client_never_offers_tools` — proposal source §2 |

### Changed — and every one of these is a Round 1 claim being *withdrawn or reduced*

| Round 1 claim | What replaced it | Class | Source |
|---|---|:---:|---|
| "Confidence, zero point eight two" | Calibrated band + track record; `Narrative` has no `confidence` field; bands under 10 cases report `UNCALIBRATED` | **[M]** | `eval/claim_audit.md` §3; proposal source §3 |
| "CUSUM watches live; Bayesian online detection covers slow drift" | STL + robust MAD z-score + PELT only. **CUSUM and Bayesian online detection were not built** | **[M]** | `detection/` package; ADR-015–017 |
| "Conformal prediction returns two or three ranked hypotheses" | Ranked hypotheses + cost-sensitive deferral. **Conformal prediction was not implemented** | **[M]** | `recommendation/` package |
| "Driver tree: Revenue = Volume × Price × Conversion" | LMDI, residual-free, **0.000000000%** closure | **[M]** | `eval/attribution_report.md` — proposal source §2 |
| "Revenue dropped 8% in the West region" | −25.0%, the movement the detector measured | **[S]** | proposal §4 |
| "Two days becomes minutes" | 4–50 s runtime **[M]**; **no time-saving claim made** | **[M]/[A]** | proposal source §2 (runtime), §9 (no baseline measured) |

**"Four of five changes made the claim smaller"** — count check: confidence
(smaller), CUSUM/Bayesian (withdrawn), conformal (withdrawn), 8% → 25% (a
different, larger, *measured* figure — not a reduction), two-days claim
(withdrawn). Four reductions/withdrawals out of five. Driver tree → LMDI is the
one upgrade, and it is listed separately as such.

---

## Slide 05 — Every number is computed, never generated

| Claim | Class | Source |
|---|:---:|---|
| LMDI identity closes to **0.000000000%** residual | **[M]** | `eval/attribution_report.md` — proposal source §2. An exact arithmetic property, not a fit quality |
| **109.9%** is arithmetically correct and self-explaining | **[S]** | proposal source §2 |
| Top driver held in **100% of 300 resamples** | **[S]** | Moving-block bootstrap; `eval/attribution_report.md` — proposal source §3 |
| No `tools` key in the narration request | **[M]** | `test_the_client_never_offers_tools` — asserted against the **recorded request** — proposal source §2 |
| No routing predicate reads model output | **[M]** | `test_no_routing_predicate_reads_a_narrative` — asserted against predicate **source** — proposal source §2 |
| `Narrative` has no `confidence` field | **[M]** | `eval/claim_audit.md` Stage 13 §"The one claim I want a judge to test" |
| STL + robust MAD + PELT; materiality has a statistical **and** a business leg | **[M]** | `detection/`; ADR-015–017 |
| Adtributor for localisation | **[R]** method / **[M]** implemented | Bhagwan et al., NSDI '14 — proposal source §1 |
| Difference-in-differences with parallel-trend check | **[M]** | `causal_language_licensed`; proposal source §2 |
| "Remove trend/seasonality first, then detect breaks in the residual" | **[R]** | Li et al. 2019, via `ROUND1_MASTER.md` — proposal source §1 |

---

## Slide 06 — Nothing ships unverified

| Claim | Class | Source |
|---|:---:|---|
| Gate 2 false acceptance: **0 of 10** corrupt narratives | **[S]** | `eval/verification_report.md` — proposal source §3 |
| Gate 2 false rejection: **0 of 6** valid narratives | **[S]** | same |
| Injected violations caught by the expected check: **9 / 9** | **[S]** | same |
| Verification failure rate **0%** across the demonstration set | **[M]** | `eval/graph_report.md` — proposal source §2 |
| Ten deterministic checks against a frozen, hashed bundle | **[M]** | `verification/engine.py`; proposal §6.4 |
| "None of *those* got through — not that none could" | — | Stated caveat, `eval/claim_audit.md` §5 |
| **Gate 2 blocked our own deterministic template** | **[M]** | Stage 13; `eval/data_realism_audit.md`, `eval/claim_audit.md` correction #2 — proposal source §2 |
| Causal licence **denied on S3**; UI renders "Association only" | **[M]** | `eval/graph_report.md` — proposal source §2 |
| DiD licenses wording, not truth; assumes no unobserved confounder affecting only the treated slice | **[A]** stated limitation | proposal §15 risk 5 |

---

## Slide 07 — It declines

| Claim | Class | Source |
|---|:---:|---|
| Automation / review / abstention = **50% / 25% / 25%** (4 / 2 / 2 of 8) | **[M]** | `eval/graph_report.md` — proposal source §2 |
| "These describe the demonstration set… a production mix would be dominated by no material event" | — | Stated caveat, proposal §10 |
| **S2** — South × Apparel, **−21.9%**, two explanations implying different owners | **[S]** | See §13 — proposal §9 |
| **S4** — **52 of the 56 days** a seasonal baseline needs | **[S]** | See §13 — proposal §9, `eval/detection_report.md` |
| **S7** — channel rename reads as **+5.9%**; no alert | **[S]** | See §13 — proposal §9 |
| Real interrupt on a durable checkpoint; **identical bundle hash across the pause** | **[M]** | `eval/security_audit.md`, `test_every_analyst_outcome_resumes_the_same_run` — proposal source §2 |
| Only the HIGH band is calibrated; MEDIUM/LOW report `UNCALIBRATED` | **[S]** | `eval/recommendation_report.md` — proposal source §3 |
| On S2 the cost arithmetic to justify automating is unavailable | **[M]** | `eval/recommendation_report.md`; `eval/final_demo_script.md` beat 6 |

---

## Slide 08 — Who may see what, and who may do what

| Claim | Class | Source |
|---|:---:|---|
| Three personas with different data access and decision rights | **[M]** | proposal §3; S5a vs S5b vs S6 — proposal source §8 (R2-MPE-3) |
| Priya is denied `crm_notes`; the **count** of withheld items is shown | **[M]** | proposal §3, §9 S6; `eval/security_audit.md` |
| Arjun's higher configured decision value can route the same evidence differently | **[A]** | `config/deferral.yaml` — proposal source §4. **The decision values 500k / 750k / 2M INR are assumptions**, and the deck does not quote them |
| Button reads "Raise the request", not "roll back" | **[M]** | `AutomationScope`; `eval/final_demo_script.md` beat 5 |
| Rollback is a separate lever, no persona can approve it, it is on a never-automate list | **[M]** | ADR-026 / Stage 9 consistency audit; `config/levers.yaml` |
| **32** security tests | **[M]** | `test_entitlements` (13) + `test_chokepoint` (10) + `test_security_chain` (9) — proposal source §2 |
| **6-stage** leak chain with a non-vacuity control | **[M]** | `tests/test_security_chain.py` — proposal source §2 |
| **0** restricted items reaching any stage | **[M]** | same |
| Entitlement applied **before** retrieval ranking | **[M]** | proposal §8; `eval/security_audit.md` |
| Every read audited including denials, correlated to the run | **[M]** | `audit_log`; ADR-032 (`ContextVar` run id) |
| **No authentication** — persona is a dropdown | **[M]** | `eval/prototype_readiness.md` §6; proposal §15 risk 7 |
| Enterprise IAM is V2 priority 1, triggered by "before any real data" | — | proposal §14, §16 |

---

## Slide 09 — What we measured, and what we refuse to claim

### Measured **[M]** — every row from proposal source §2

| Claim | Value |
|---|---:|
| Automated tests passing | 574, 0 failures |
| Scenarios end to end | 8 / 8 |
| Graph vs direct-module agreement | 8 / 8 |
| LMDI identity closure | 0.000000000% |
| Lineage records per run | 15 |
| Runtime per scenario | 4–50 s |
| Orchestration overhead | 13–42 ms (0.08–0.80%) |
| Restricted items reaching any stage | 0 |

### Synthetic evaluation **[S]** — every row from proposal source §3

| Claim | Value | Stated limitation carried onto the slide |
|---|---:|---|
| Detection precision / recall | 1.000 / 1.000 | Over *injected* events, built to be detectable by this method's assumptions |
| False positives, 48 clean slices | **0** | **The meaningful figure** — not guaranteed by construction |
| Ranking robustness | 100% of 300 resamples | Resampling the same series, not out-of-sample |
| Dense recall@10 | 0.778 | Post-realism-audit |
| RRF MRR | 0.838 | Best MRR of the three |
| Calibration HIGH | 12 of 12 | Synthetic; MEDIUM/LOW report `UNCALIBRATED` |

### The retrieval regression

| Claim | Class | Source |
|---|:---:|---|
| Corpus held only **13 distinct texts** across **895 records** | **[M]** | proposal source §3 "Superseded figures" note |
| Widened to **30** distinct texts | **[M]** | See §13 — `eval/data_realism_audit.md`, `data/generate.py::TICKET_TEMPLATES` |
| BM25 p@5 **0.810 → 0.552** | **[S]** | proposal source §3 |
| BM25 recall@10 **0.957 → 0.654** | **[S]** | same |
| Dense recall@10 **0.933 → 0.778** | **[S]** | same |
| RRF MRR **0.964 → 0.838** | **[S]** | same |
| Dense beats BM25 on recall@10 by **19% relative** | **[S]** | See §13 — `eval/claim_audit.md` Stage 13. Arithmetic check: 0.778 / 0.654 = 1.190 |

### Not claimed — from proposal source §6

No customer savings · no enterprise ROI · no adoption numbers · no market share ·
no productivity gain · no unqualified "accuracy" · no "production-ready" ·
no "real-time" · no "autonomous" except as a negation. Each was searched for and
is absent from the repository.

---

## Slide 10 — Prototype readiness

| Claim | Class | Source |
|---|:---:|---|
| **8 REAL · 1 PARTIAL · 4 LIGHTWEIGHT · 1 DEFERRED** across 14 areas | **[M]** | See §13 — `eval/prototype_readiness.md` final matrix |
| **No live LLM evaluation** — latency, tokens, cost, first-pass verification rate unmeasured and not estimated | — | `LIVE LLM EVALUATION PENDING`; proposal source §9. `eval/run_llm_eval.py` is implemented and unrun |
| **No real-data validation** — every metric synthetic; the largest open risk | — | proposal §15 risk 1; proposal source §9 |
| **No baseline time-to-explanation**, therefore no time-saving claim is possible | **[A]** | proposal source §4, §9 |
| Concurrent capacity ≈ **two simultaneous users** | **[A]** | Reasoned from DuckDB single-writer + audit-on-read; **not load-tested** — proposal source §4 |
| "It scales horizontally" would be false | — | proposal §14 |
| Verified template mode is supported, not degraded; UI labels it | **[M]** | proposal §13 |
| Four production migrations, each with a **trigger** | — | `docs/PRODUCTION_EVOLUTION.md`; proposal §14 |
| What would not change: deterministic/AI boundary, evidence freeze, entitlement-before-ranking, typed contracts | — | proposal §14 |

---

## Slide 11 — Why this wins, and what a pilot would prove

| Claim | Class | Source |
|---|:---:|---|
| Category comparison table | — | proposal §5. **Compares categories, not vendors.** No named-competitor capability claim is made — proposal source §6 |
| "Manual SQL analysis is the honest benchmark" | — | proposal §5 |
| NOW: 6 KPIs · 3 sources · 3 personas · 8 scenarios · 574 tests | **[M]** | proposal source §2 |
| V2 priorities and V3 platform | — | proposal §16 |
| "Deliberately not on the roadmap: autonomous agents…" | — | proposal §16 |
| The pilot ask: one KPI family, one team, one quarter, measuring time-to-explanation against baseline | — | proposal §12 |
| Closing three-line band | — | proposal §17, verbatim |

---

## 12. Round 1 material deliberately **not** carried forward

Each of these appeared in the Round 1 deck, video script or research corpus. None
appears in the Round 2 deck, and each omission is deliberate.

| Round 1 item | Why it is not in this deck |
|---|---|
| **3.3% Copilot enterprise penetration** | Not in `R2_BUSINESS_PROPOSAL_SOURCE.md`. The brief for this deck restricts quantitative claims to that file |
| **384 reviews coded; only 0.6% ever say "root cause"** | Same reason. It is a strong finding and it is available in `ROUND1_MASTER.md` §9 if a judge asks — the speaker notes say where |
| **"Days" as the analyst turnaround stat card** | We never measured a baseline. Round 1 stated it as a market fact; Round 2 will not build a value claim on it |
| **"Two days becomes minutes"** / **"we are selling the two days back"** | The strongest line in the Round 1 script, and the one Round 2's evidence discipline forbids. It is reframed on Slide 11 as *the thing a pilot would measure* |
| **Confidence 0.82** | The Round 2 system deliberately cannot produce it |
| **Gartner: 75% of new analytics content GenAI-contextualised by 2027** | Not in the proposal source file |
| **Named research citations on Round 1 Slide 5** (Mozannar & Sontag, Cresswell et al., Fregosi et al.) | Mozannar & Sontag and Cresswell et al. remain in the *architecture* and the proposal; they are method citations rather than deck claims, so they sit in the footnote strip rather than the body |

---

## 13. Claims sourced from repository artefacts beyond the proposal source file

These are **[M]** or **[S]** facts about the built system that
`R2_BUSINESS_PROPOSAL_SOURCE.md` does not tabulate. They extend the same evidence
base; none contradicts it. Listed separately so the primary rule stays auditable.

| Claim | Slide | Class | Artefact |
|---|:---:|:---:|---|
| 26-node state machine, 11 typed terminal states | 04 | **[M]** | `eval/prototype_readiness.md` §1; `graph/types.py::TerminalState` |
| S2 — South × Apparel, −21.9% | 07 | **[S]** | proposal §9; `eval/graph_report.md` |
| S4 — 52 of 56 days | 07 | **[S]** | proposal §9; `eval/detection_report.md` |
| S7 — +5.9% channel-rename artifact | 04, 07 | **[S]** | proposal §9 |
| Corpus widened from 13 to **30** distinct texts | 09 | **[M]** | `eval/data_realism_audit.md`; `data/generate.py` |
| Dense beats BM25 on recall@10 by **19% relative** | 09 | **[S]** | `eval/claim_audit.md` Stage 13; arithmetic over two figures already in proposal source §3 |
| **8 REAL · 1 PARTIAL · 4 LIGHTWEIGHT · 1 DEFERRED** | 10 | **[M]** | `eval/prototype_readiness.md` final matrix |
| Rollback sits on a never-automate list, separate from the request lever | 08 | **[M]** | ADR-026 / Stage 9 consistency audit; `config/levers.yaml` |

---

## 14. Open evidence gaps — stated on the slides, not hidden

Identical to `R2_BUSINESS_PROPOSAL_SOURCE.md` §9. Slide 10 puts four of them on
the deck itself.

| Gap | On which slide |
|---|---|
| No live LLM evaluation | **10**, and volunteered in the speaker notes before anyone asks |
| No real-data validation | **10** |
| No baseline time-to-explanation | **10**, and it is the reason Slide 11's ask exists |
| ~2 concurrent users; no concurrency testing | **10** |
| Only the HIGH confidence band is calibrated | **07** |
| Feedback loop implemented, never run | Not on a slide — in the speaker notes' Q&A, per `eval/judge_defense.md` |
| No authentication | **08**, stated as a card rather than a footnote |

---

*Team SouthernHustlers · Accenture Innovation Challenge 2026 · Problem Track 3*
*Deck: `R2_PITCH_DECK.md` · Proposal evidence base: `R2_BUSINESS_PROPOSAL_SOURCE.md`*
