# BusinessIntelligence.ai — Round 2 Pitch Deck

**Accenture Innovation Challenge 2026 · Problem Track 3 · Team SouthernHustlers · IIT Madras**

---

## How to read this file

This is a **build spec for the deck**, not a document to be read aloud. It maps
one section to one slide, in the same row-by-row format that produced the Round 1
slides, so the deck can be rebuilt in the existing design system without a
second round of design decisions.

- Talk track: `R2_PITCH_SPEAKER_NOTES.md`
- Every number's provenance: `R2_PITCH_DECK_SOURCE.md`
- Live product demo (if the format allows one): `eval/final_demo_script.md` — **that file is authoritative for the demo**; this deck does not restate its beats.

**Central thesis, one sentence:**

> BusinessIntelligence.ai does not just tell a business leader what moved. It
> investigates why it moved, shows the evidence, recommends what to do, and
> knows when it should not answer.

---

## Continuity with Round 1

Round 1 was submitted as `SouthernHustlers_BusinessIntelligence.ai.pptx` — 6 slides,
2 of them content, built as 1600×900 HTML in the `case-deck-design-system` repo
(`theme-accenture`), exported to PNG and placed into the official Accenture template.

### What carries forward unchanged

| Element | Round 1 | Status |
|---|---|---|
| **Product name** | BusinessIntelligence.ai | Unchanged |
| **Team** | SouthernHustlers · IIT Madras | Unchanged |
| **Typeface** | Arial only (template mandate) | Unchanged |
| **Canvas** | 1600×900, dense evidence-first "consulting poster" | Unchanged |
| **Title grammar** | `01  \|  The Problem: dashboards show what moved, never why` — numeral, pipe, **claim not label**, colon not dash | Unchanged |
| **Palette** | `#A100FF` primary · `#460073` deep · `#F4EAFF` tint · `#1B1B25` ink · `#5F6070` grey · `#C0245C` danger · `#0B7B5C` success · `#2E1046` dark plate · `#FFC53D` gold accent | Unchanged |
| **Sourcing discipline** | Every slide ends in a sources strip | Unchanged — and now stricter |
| **Five stages** | Detect → Attribute → Explain → Recommend → Verify | Unchanged |
| **"One engine, from a number to a decision"** | Slide 4 title | Reused verbatim as Slide 03 |
| **"Two gates, not one"** | Solution slide | Unchanged |
| **"The model never gets the last word"** | Video script | Unchanged |
| **"Escalation is a cost rule, not a threshold"** | Closing band | Unchanged |

### What Round 2 deliberately changes, and why

These are places where the built system contradicts something Round 1 promised.
The recognisable identity is preserved; the substance is corrected. **Slide 04
puts this on the record rather than quietly dropping it.**

| Round 1 said | Round 2 ships | Why the change |
|---|---|---|
| "Confidence, zero point eight two" | A calibrated **band** with a track record: *High reliability · correct in 12 of 12 similar past cases* | A single decimal implies a precision we cannot support. The `Narrative` type now has **no** `confidence` field — there is nowhere to write one. Bands below 10 observed cases report `UNCALIBRATED` |
| "CUSUM watches live; Bayesian online detection covers slow drift" | STL decomposition + robust MAD z-score + PELT changepoint | CUSUM and Bayesian online detection were **not built**. Claiming them would be the exact failure this project exists to prevent |
| "Conformal prediction returns two or three ranked hypotheses" | Ranked hypotheses with coverage, plus **cost-sensitive deferral** for the automate/defer decision | Conformal prediction was not implemented. The deferral rule *was* — it is the Round 1 promise that survived |
| "Driver tree: Revenue = Volume × Price × Conversion" | **LMDI** index decomposition — residual-free, closes to 0.000000000% | Same idea, rigorous version. An exact identity, not an approximation |
| "Revenue dropped 8% in the West region" | West × Web/Mobile App, **−25.0%**, 12 Jul → 26 Jul 2026 | Round 1's figure was illustrative. Round 2 quotes the movement the detector actually measured |
| "Two days becomes minutes" / "we are selling the two days back" | The pipeline completes in **4–50 s**. **No time-saving claim is made** | We never measured a baseline investigation time, so we cannot claim a reduction. Slide 11 states this as the pilot's job |

**The last row is the important one.** Round 1's closing line was a value claim.
Round 2 has the working system and *less* licence to make that claim, because it
now knows exactly what it has and has not measured.

---

# The slides

**11 core content slides**, plus the template's title, team-details, video and
thank-you slides.

---

## Slide 01 — `01  |  The gap has not moved: dashboards show what moved, never why`

*Purpose: establish that the Round 1 problem is real, unfixed, and expensive.*

**Row 1 — four stat cards**

| 73% | ~21% | ~70% | 22% |
|---|---|---|---|
| of BI implementations fail on the diagnostic gap, not on technology | of employees actively use the dashboards that cannot answer "why" | of analyst time spent investigating alerts that turn out to be legitimate | decline in detection accuracy for analysts reviewing 30+ alerts a day |

**Row 2 — split-32: three structural reasons | verified market voice**

*Three reasons the gap persists*
- **Detection is not explanation.** Tools flag that a number moved. The mechanism stays a manual investigation.
- **Evidence lives in two worlds.** Metrics sit in the warehouse; causes sit in support tickets, CRM notes, deploy changelogs and news.
- **Confidence is unpriced.** No tool states how sure it is, so a leader cannot separate a real finding from a fluent-sounding guess.

*Real reviews, scraped and coded in Round 1*
- "Dashboards are great at telling you what's happening, but the moment you ask why…" — ThoughtSpot
- "…correlations that aren't actually meaningful without manual review." — Tellius user, G2
- "Sales Ops deletes columns in Salesforce. Marketing changes the definition of a lead bucket." — r/BusinessIntelligence

**Row 3 — flow: THE PATH A LEADER LIVES TODAY**

`Dashboard flags a drop` → `Analyst pulls data across four or more tools` → `Cross-references tickets, CRM notes, changelogs` → `Writes a plausible, unranked narrative` → `The decision window has already closed`

**Closing band (dark):** Every category in this market produces an explanation. None of them declines to produce one.

**Sources:** sranalytics.io BI failure study · Gartner 2025 · G2 & Capterra verified reviews · r/BusinessIntelligence

---

## Slide 02 — `02  |  The obvious fix is the dangerous one`

*Purpose: kill "just point an LLM at the warehouse" before a judge suggests it.*

**Row 1 — thesis banner**

> "The capability you want for root-cause analysis actively works against the humility you need."

**Row 2 — three cards, escalating**

| A model that reasons | A model that will not stop | An industry that has named it |
|---|---|---|
| A 2026 fidelity audit found an LLM **inverted the risk direction on 3 of 4 factors** in a credit-risk narrative. Its priors overrode the supplied evidence — under *constrained* prompting | Reasoning-tuned models abstain **24% worse** than their non-reasoning counterparts (AbstentionBench). The better it reasons, the less it admits it cannot | Gartner names **"agent drift"** as the risk in autonomous analytics and prescribes **guardian layers** as the mitigation |

**Row 3 — the inference, as a band (accent)**

If the default behaviour of a capable model is to answer confidently, then abstention is not a feature you add later. It is an architecture you start from.

**Row 4 — what that means for the build (4 chevrons)**

`The model may not reach data` → `The model may not produce a number` → `The model may not choose what happens next` → `The model may not have the last word`

**Sources:** arXiv 2026 narrative-fidelity audit · AbstentionBench, Kirichenko et al. 2025 (arXiv:2506.09038) · Gartner

---

## Slide 03 — `03  |  Our Solution: one engine, from a number to a decision`

*Purpose: the product, on one screen. Reuses the Round 1 slide title verbatim.*

**Row 1 — five-stage flow, each with the question it answers**

| 1 DETECT | 2 ATTRIBUTE | 3 EXPLAIN | 4 RECOMMEND | 5 VERIFY |
|---|---|---|---|---|
| Is it real, and does it matter? | What drove it, and where? | What does the evidence support? | What should happen, and who acts? | Can every claim be checked? |

**Row 2 — split-21: the actual screen | what is in it**

*The default view — real rendered output, S1*

```
Net Revenue · West × Web/Mobile App
↓ 25.0%                              MATERIAL MOVEMENT
12 Jul → 26 Jul 2026

WHY DID IT MOVE?
Conversion rate is the largest contributor, accounting for more than
the whole movement (109.9%) — other factors moved the opposite way
and partly offset it.

EVIDENCE            7 supporting

HOW RELIABLE IS THIS?
High reliability · Correct in 12 of 12 similar past cases.
These cases come from a synthetic evaluation set, not production history.

RECOMMENDED ACTION
Escalate payment gateway to Engineering
Owner · Engineering Lead    Monitor · Checkout Conversion Rate, 2 days
Expected recovery 622,121 – 799,870 INR
                                          [ Raise the request ]
```

*Five questions, in the order a business user asks them*
- **What changed?** The movement is the largest thing on the page.
- **Why?** Ranked drivers, with the arithmetic explained rather than hidden.
- **What is the evidence?** Documents, counted, one click away.
- **How reliable?** A track record with its caveat *inline*, never in a footnote.
- **What do I do?** An owner, a monitoring metric, a bounded action.

**Row 3 — a decision workspace, not a chatbot (band, outline)**

There is no chat box, by design. A conversational surface invites the user to ask the model questions it must not answer, from data it must not reach.

**Footer:** Internally the system runs Detect → Attribute → Retrieve → Verify → Recommend. The user never sees that order. It appears only in the Method tab.

---

## Slide 04 — `04  |  Round 1 promised this. Round 2 runs it, and corrects it.`

*Purpose: continuity, and the credibility that comes from naming your own changes.*

**Row 1 — band (dark)**

Round 1 was a concept. Round 2 is 574 passing tests, 8 executable scenarios and a list of things we said we would build and then did not.

**Row 2 — split-32: kept | changed**

*Kept, and now running*

| Round 1 promise | Round 2 evidence |
|---|---|
| Five stages, one engine | 26-node state machine, 11 typed terminals, 8/8 scenarios end to end |
| Materiality gate — statistical **and** business | S7: a channel rename looks like +5.9% growth. Statistically real, business-immaterial, **no alert** |
| Two gates, not one | Gate 1 sufficiency, Gate 2 ten deterministic checks against a frozen hashed bundle |
| "Escalation is a cost rule, not a threshold" | Cost-sensitive deferral, implemented; it is what routes S2 to a human |
| The LLM narrates only what was already verified | The narration request carries **no `tools` key** — absent, not empty |

*Changed, and why*

| Round 1 said | Round 2 ships |
|---|---|
| Confidence 0.82 | A calibrated band and a track record. `Narrative` has no `confidence` field |
| CUSUM, Bayesian online detection | STL + robust MAD + PELT. **The other two were not built** |
| Conformal prediction | Ranked hypotheses + cost-sensitive deferral |
| Driver tree | **LMDI** — residual-free, closes to 0.000000000% |
| "Two days becomes minutes" | 4–50 s measured. **No time-saving claim**, because no baseline was measured |

**Row 3 — closing band (accent)**

Four of five changes made the claim *smaller*. That is what having a working system does to a pitch.

---

## Slide 05 — `05  |  Every number is computed, never generated`

*Purpose: the central technical claim, stated as something testable.*

**Row 1 — thesis**

> "The model writes the sentence. It does not compute, retrieve, or decide."

**Row 2 — the boundary, as two columns**

| Deterministic — everything the user acts on | The model — one job, inside a schema |
|---|---|
| Detection: STL + robust MAD z-score + PELT changepoint | Writes prose, into a typed schema |
| Materiality: a statistical leg **and** a business leg | Sees a frozen, hashed evidence bundle |
| Attribution: **LMDI**, residual-free | Has **no** database access |
| Localisation: **Adtributor** — explanatory power, surprise, succinctness | Has **no** tools key in the request |
| Causal test: difference-in-differences with a parallel-trend check | Has **no** field to write a confidence into |
| Routing: pure predicates over deterministic state | Cannot choose what happens next |

**Row 3 — the number that proves it (split-12)**

*109.9%*

> Conversion rate accounts for **more than the whole movement**, because sessions rose and partly offset it.

An exact identity decomposition closes to **0.000000000%** residual, so a share above 100% is arithmetically correct and the system explains why rather than clipping it. **No language model would generate a self-explaining over-100% share.** It is the cheapest available proof that the figure was computed.

**Row 4 — enforced by test, not by prompt**

- `test_the_client_never_offers_tools` — asserted against the **recorded request**, not the code that builds it
- `test_no_routing_predicate_reads_a_narrative` — asserted against the predicate **source**. A predicate that started consulting model output would pass every behavioural test and still fail this one
- Top driver held in **100% of 300 bootstrap resamples**

**Sources:** LMDI index decomposition · Adtributor, Bhagwan et al., NSDI '14 · Li et al. 2019 (decompose before detecting)

---

## Slide 06 — `06  |  Nothing ships unverified, and the model never gets the last word`

*Purpose: the trust layer — Round 1's differentiator, now measured.*

**Row 1 — the two gates (flow)**

`Gate 1 · sufficiency` → `evidence bundle frozen and hashed` → `narration` → `Gate 2 · ten deterministic checks` → `pass, or one retry, or a verified deterministic template`

**Row 2 — what Gate 2 measured (4 stat cards)**

| 0 of 10 | 0 of 6 | 9 / 9 | 0% |
|---|---|---|---|
| false acceptances across hand-built corrupt narratives | false rejections across valid narratives | injected violations caught by the expected check | verification failure rate across the demonstration set |

*Caveat carried on the slide:* none of **those** ten got through. That is not the same as saying none could.

**Row 3 — the strongest evidence, as a card (danger tint)**

**The gate blocked our own fallback template.**

During the final audit, a bug made the deterministic template cite two evidence
ids the frozen bundle no longer held. Gate 2 rejected it. We had documented that
template as "cannot fail by construction" — it was unfailable by *luck*. Both the
builder and the docstring were corrected.

> A gate that only ever passes what we produce is not a gate.

**Row 4 — causal language is licensed, not asserted**

- A difference-in-differences test with a parallel-trend check decides whether the system may use the word *caused*.
- On scenario **S3 the licence is denied** and the wording degrades to **"association only"** — in the UI, not just in a log.
- Gate 2 rejects causal wording that the licence did not grant.
- **Stated limitation:** DiD licenses *wording*, not *truth*. It assumes no unobserved confounder affecting only the treated slice.

**Sources:** Gate 2 check suite · `eval/verification_report.md` · `eval/data_realism_audit.md`

---

## Slide 07 — `07  |  It declines: abstention is the product, not a limitation`

*Purpose: the beat that separates this from every competitor. Land it slowly.*

**Row 1 — the outcome split (3 stat cards, dark plate)**

| 50% | 25% | **25%** |
|---|---|---|
| automated — 4 of 8 scenarios | routed to a human — 2 of 8 | **declined — 2 of 8** |

*These describe the demonstration set, which was built to exercise every terminal. A production mix would be dominated by "no material event."*

**Row 2 — three ways it stops, three different reasons (cols-3)**

| **S2 · Conflicting evidence** | **S4 · Sparse history** | **S7 · Immaterial artifact** |
|---|---|---|
| South × Apparel, −21.9%. Two explanations equally supported — competitive pressure and stock availability — **implying different owners**. One is a pricing problem; one is a supply problem | A new category with **52 of the 56 days** a seasonal baseline needs. It refuses to extrapolate and says how long to wait | A channel rename (`marketplace` → `Marketplace`) reads as **+5.9% growth**. Statistically real, business-immaterial |
| *Stops, states the question, hands it to a person* | *Declines, and says what would change its mind* | *No alert, no recommendation, no invented cause* |

**Row 3 — the pause is real, not a message (card, tint)**

The graph **interrupts on a durable checkpoint**. Resuming produces the same run
with an **identical evidence bundle hash**, so the analyst's decision attaches to
exactly what they reviewed — not to a re-computed approximation of it.

**Row 4 — and it limits its own claims**

Only the HIGH band has ≥10 observed cases. MEDIUM and LOW report **`UNCALIBRATED`** rather than quoting a rate they cannot support. On S2 that means the cost arithmetic which would justify automating **is not available** — it could not automate that case even if it wanted to.

**Closing band (dark):** A system that always answers cannot be trusted on the answer it gives.

---

## Slide 08 — `08  |  Who may see what, and who may do what`

*Purpose: the two questions an enterprise buyer actually asks.*

**Row 1 — three personas, genuinely different (cols-3)**

| **Meera · Analytics Lead** | **Priya · Regional Ops Lead** | **Arjun · Finance Director** |
|---|---|---|
| *Is this defensible enough to circulate?* | *Do I escalate, and to whom?* | *Is this material to the quarter?* |
| Gets method, contribution, counterfactual result, full lineage | Gets region-scoped analysis, a named owner, a request she is entitled to raise | Gets an impact range with its basis named, and an explicit statement of what is unknown |
| Investigation becomes review | **Denied `crm_notes`** — and told *how many* items were withheld | A higher configured decision value, so the **same evidence can route differently** |

**Row 2 — scope separation, as the band that matters (accent)**

The button says **"Raise the request."** It does not say "roll back."

**Row 3 — split-21: why that distinction is the product | how access is enforced**

*Automating a request is not automating a remediation*

The persona holds **request rights** on this lever, not approval rights. What gets
automated is *raising an engineering request*. Executing a rollback is a different
lever, no persona in this system can approve it, and it sits on a **never-automate
list**. An enterprise buyer's real fear is not a wrong explanation — it is a
correct explanation wired to the wrong action.

*Entitlement is applied before ranking, not after*

| | |
|---|---|
| **32** security tests | row filters, column masks, source denials |
| **6-stage** leak chain | SQL → ranking → bundle → payload → UI, with a **non-vacuity control** |
| **0** | restricted items reaching any stage |
| Every read audited | including denials, correlated to the run the user saw |

**Filtering before ranking matters:** a restricted document that reaches the ranker has already influenced what the user sees, even if it is stripped from the final list.

**Row 4 — the gap we do not paper over (card, danger tint)**

**There is no authentication.** Persona is a dropdown. Authorisation is real and
tested end to end; identity is not. This is correct for a local single-user
prototype and unacceptable with real data — which is why enterprise IAM is
**priority 1** on the V2 roadmap, triggered by *"before any real data"* rather
than by a user count.

---

## Slide 09 — `09  |  What we measured, and what we refuse to claim`

*Purpose: the evidence-discipline slide. This is the one that survives cross-examination.*

**Row 1 — the label system (band, outline)**

Every number in this deck carries a class: **[M]** measured on this system · **[S]** synthetic evaluation · **[R]** research-sourced · **[A]** stated assumption · **[I]** illustrative.

**Row 2 — split-32: measured | synthetic evaluation**

*Measured on this system* **[M]**

| | |
|---|---:|
| Automated tests passing | **574**, 0 failures |
| Scenarios end to end | **8 / 8** |
| Graph vs direct-module agreement | **8 / 8** — orchestration changed no decision |
| LMDI identity closure | **0.000000000%** residual |
| Lineage records per run | **15** |
| Runtime per scenario | **4–50 s** |
| Orchestration overhead | 13–42 ms (**0.08–0.80%**) |
| Restricted items reaching any stage | **0** |

*Synthetic evaluation* **[S]** — seed `20260821`, 535 days, 6 injected events

| | |
|---|---:|
| Detection precision / recall | 1.000 / 1.000 |
| **False positives on 48 clean slices** | **0** |
| Ranking robustness | 100% of 300 resamples |
| Retrieval — dense recall@10 | 0.778 |
| Retrieval — RRF MRR | 0.838 |
| Calibration, HIGH band | 12 of 12 |

**The honest reading of 1.000/1.000:** recall of 1.000 means every event *we
injected* was found, and those events were built to be detectable by this
method's assumptions. **The meaningful figure is the 0 false positives**, because
that one is not guaranteed by construction.

**Row 3 — the result we are proudest of is a set of numbers that got worse (card, tint)**

A realism audit found the document corpus held only **13 distinct texts** across
895 records — retrieval was closer to a lookup than to search. We widened it to 30.

| | Before | After |
|---|---:|---:|
| BM25 precision@5 | 0.810 | **0.552** |
| BM25 recall@10 | 0.957 | **0.654** |
| Dense recall@10 | 0.933 | **0.778** |
| RRF MRR | 0.964 | **0.838** |

Every score fell. **The lower numbers are the ones we report** — and they are the
first measured evidence that the hybrid retriever earns its place, because dense
recall now beats BM25 by 19% relative where before it did not.

**Row 4 — searched for, and absent from the entire repository (band, dark)**

No customer savings · no enterprise ROI · no adoption numbers · no market share · no productivity gain · no unqualified "accuracy" · no "production-ready" · no "real-time" · no "autonomous" except as a negation

**Sources:** `eval/claim_audit.md` · `eval/data_realism_audit.md` · `R2_BUSINESS_PROPOSAL_SOURCE.md`

---

## Slide 10 — `10  |  Prototype readiness, with the gaps named first`

*Purpose: pre-empt every "but is it real?" question in one slide.*

**Row 1 — the 14-area matrix (4 stat cards)**

| 8 REAL | 1 PARTIAL | 4 LIGHTWEIGHT | 1 DEFERRED |
|---|---|---|---|
| design, architecture, frontend, backend, storage, security, error handling, testing | auth — authorisation real, **authentication absent** | hosting, CI/CD, caching, monitoring | scaling, with named triggers |

*An area marked LIGHTWEIGHT or DEFERRED is a decision we can defend in a question, not a gap we missed.*

**Row 2 — four gaps we state before a judge finds them (cols-4, danger tint)**

| **No live LLM evaluation** | **No real-data validation** | **No baseline measurement** | **~2 concurrent users** |
|---|---|---|---|
| No API key in this environment. Latency, tokens, cost and first-pass verification rate are **unmeasured and not estimated**. The harness is written and unrun | Every metric is synthetic. The largest open risk in the project | Without a baseline investigation time, **no time-saving claim is possible** | DuckDB permits one writer and the audit log writes on every read. Concurrency is a *storage* migration, not a worker count. "It scales horizontally" would be false |

**Row 3 — running without a model is a supported mode, not a degraded one (band, outline)**

Everything except sentence construction is identical. The UI labels it **Verified template mode** and states that no model reviewed the text. The numbers, the evidence and the decision are the same either way.

**Row 4 — the production path is triggered by conditions, not volumes (flow)**

`Dropdown → enterprise IAM` **before any real data** · `In-memory index → managed vector search` **at the first data-isolation requirement, i.e. security before scale** · `SQLite → durable workflow state` **when it runs on more than one process** · `DuckDB → enterprise warehouse` **when a second writer is needed**

**Footer:** What would *not* change: the deterministic/AI boundary, the evidence freeze, entitlement-before-ranking, the typed module contracts. None of those is a prototype convenience.

---

## Slide 11 — `11  |  Why this wins, and what a pilot would prove`

*Purpose: close. The category gap, then the ask.*

**Row 1 — the category table**

| | Answers *what* | Answers *why* | Shows evidence | Says when it doesn't know | Bounded action |
|---|:---:|:---:|:---:|:---:|:---:|
| Dashboards | ✅ | ✕ | ✕ | ✕ | ✕ |
| Threshold alerting | ✅ | ✕ | ✕ | ✕ | ✕ |
| Manual SQL analysis | ✅ | ✅ | ✅ | depends on the analyst | ✕ |
| Generic BI copilots | ✅ | prose | ✕ | ✕ | ✕ |
| Generic RAG assistants | ✕ | prose | citations | ✕ | ✕ |
| **BusinessIntelligence.ai** | ✅ | ✅ | ✅ | **✅** | **✅** |

**The gap is the last two columns.** Several categories produce an explanation.
None of them *declines* — and none produces a bounded, owned action when it does answer.

**Row 2 — the honest benchmark (card, tint)**

**A good analyst does everything in that table.** What they cannot do is run in
fifteen seconds, apply the same materiality rule every time, or leave an audit
trail that survives their absence. This product does not compete with a
spreadsheet. It competes with *how long the spreadsheet takes*.

**Row 3 — roadmap (chevrons)**

`NOW — Round 2 prototype` 6 KPIs · 3 sources · 3 personas · 8 scenarios · 574 tests
→ `V2 — Enterprise pilot` **replace assumptions with measurements**: enterprise IAM, one real KPI family, real calibration, live LLM evaluation, **baseline time-to-explanation**
→ `V3 — Production platform` enterprise warehouse · per-tenant retrieval · durable workers · embedded frontend · model gateway · observability

**Deliberately not on the roadmap:** autonomous agents, agent swarms, or letting the model query the warehouse. Those are not deferred features. They are the architecture this system exists to avoid.

**Row 4 — the ask (band, accent)**

One KPI family, one team, one quarter — measuring time-to-explanation against the current baseline. That converts our strongest argument into a data point.

**Closing band (dark):**

> A dashboard tells you what moved. An LLM will tell you why, confidently, whether or not it knows.
> This system tells you why, shows the evidence, recommends what to do — **and tells you when it cannot.**
>
> That last capability is the hardest to build, the easiest to skip, and the only one that makes the other three safe to rely on.

---

# Build notes

## Rendering the deck

**No scripted `.pptx` workflow is configured in this repository**, and none was
used in Round 1. The Round 1 deck was produced by this path, which is the one to
reuse:

1. Build each slide as a `<section class="slide">` at 1600×900 in
   `05_Design_System/case-deck-design-system`, using `theme-accenture`.
2. **Compose from existing classes; never write new CSS.** That rule is what kept
   the Round 1 slides looking like one deck.
3. Export each slide to PNG (`03_Slide_Artwork/` holds the Round 1 exports).
4. Place the PNGs into the official Accenture AIC template, which supplies the
   title, team-details, video and thank-you slides and mandates Arial.
5. Export to PDF. Name it `SouthernHustlers_BusinessIntelligence.ai.pptx` /
   `.pdf`, matching the Round 1 naming convention.

`python-pptx` is present in the local environment but is **not** a project
dependency and no build script exists. Adding one would be a new workflow, not a
continuation of the Round 1 one.

## Slide-count guidance

Eleven content slides is the full set. If the format caps the deck lower, cut in
this order — the thesis survives all three cuts:

| Cut first | Slide | Why it is cuttable |
|---|---|---|
| 1 | **10 — Readiness** | Fold the four named gaps into Slide 09's closing band |
| 2 | **04 — Round 1 → Round 2** | Only lands with judges who saw Round 1. Move to the appendix and raise it if asked |
| 3 | **08 — Personas and scope** | Keep only the "Raise the request, not roll back" band, folded into Slide 07 |

**Never cut:** 05 (numbers are computed), 06 (nothing ships unverified),
07 (it declines). Those three *are* the pitch — the same three the Round 1 video
script protected.

---

*Team SouthernHustlers · Accenture Innovation Challenge 2026 · Problem Track 3*
*Evidence mapping: `R2_PITCH_DECK_SOURCE.md` · Talk track: `R2_PITCH_SPEAKER_NOTES.md` · Live demo: `eval/final_demo_script.md`*
