# BusinessIntelligence.ai
### KPI intelligence-to-action engine — Round 2 Business Proposal

**Accenture Innovation Challenge 2026 · Problem Track 3 · Team SouthernHustlers**

---

> **A note on evidence.** Every number in this proposal carries a label:
> **[M]** measured on this system · **[S]** synthetic evaluation · **[R]** research-sourced with citation · **[A]** stated assumption · **[I]** illustrative.
> No customer savings, ROI, adoption or productivity figure appears anywhere, because this project has no deployment to measure. Full mapping: `R2_BUSINESS_PROPOSAL_SOURCE.md`.

---

## 1. Executive summary

**Business leaders do not need another dashboard telling them what moved. They need a system that investigates why it moved, shows the evidence, recommends what to do — and knows when it does not have enough evidence to answer.**

**The problem.** A dashboard reports that West revenue fell 25%. Everything after that — is it real, what caused it, does it matter, who should act — falls to an analyst and takes days. Meanwhile 73% of BI implementations are reported to fail on diagnostic gaps rather than technology, and only ~21% of employees actively use deployed BI tools; when a dashboard cannot answer "why", people revert to spreadsheets. **[R]**

**Why the obvious fix fails.** Pointing an LLM at the warehouse produces confident prose with no accountability. A 2026 fidelity audit found an LLM **inverted the risk direction on three of four factors** in a credit-risk narrative — its priors overrode the supplied evidence, under constrained prompting. **[R]** And the models best at multi-step causal reasoning are measurably *worse* at admitting uncertainty: reasoning-tuned models abstain **24% worse** than non-reasoning counterparts. **[R]** The capability you want for root-cause analysis actively works against the humility you need.

**What we built.** A decision workspace that runs a five-stage pipeline — **Detect → Attribute → Explain → Recommend → Verify** — where every number is computed by SQL, statistics or a business rule, and the language model writes *only the sentence*, inside a schema, against a frozen evidence bundle, with no database access and no tools.

**What is technically different.** Three things, each enforced by a test rather than a prompt:

1. **The model cannot reach data.** The narration request carries no `tools` key — absent, not empty. A model that cannot query cannot fabricate a query result.
2. **Nothing ships unverified.** Ten deterministic checks run against a hashed, frozen evidence bundle before delivery. **0 false acceptances across 10 hand-built corrupt narratives** — and the gate blocked our *own* fallback template when a bug produced two unresolvable citations. **[S][M]**
3. **Causal language is licensed, not asserted.** A difference-in-differences test with a parallel-trend check decides whether the system may say "caused". On one demo scenario the licence is **denied** and the wording degrades to "association only". **[M]**

**Why abstention is the product, not a limitation.** Across eight demonstration scenarios the system automates 4, routes 2 to a human, and **declines 2**. **[M]** A system that always answers cannot be trusted on the answer it gives. Gartner's own framing for autonomous analytics names "agent drift" as the risk and guardian layers as the mitigation **[R]** — abstention and human routing are that layer.

**What the prototype demonstrates.** A working system, not a mockup: 574 automated tests passing, 8 executable scenarios running end to end, a verified entitlement chain, per-run telemetry and lineage, and a real human-in-the-loop pause that resumes on the same evidence hash. **[M]**

**Expected business value.** The repository contains **no** validated enterprise ROI, and none is claimed. Value is presented in Section 12 as four mechanisms — operational, decision, risk and governance — with every quantification stated as a labelled assumption a pilot would test. The honest position: we can evidence that the system *works and knows its limits*; we cannot yet evidence what it *saves*.

---

## 2. The problem

### What happens today

A KPI moves. What follows is a manual investigation:

| Step | Who | Typical friction |
|---|---|---|
| Notice the movement | Dashboard | No signal on whether it is noise |
| Decide if it matters | Analyst | Statistical vs business significance conflated |
| Find the cause | Analyst | Structured metrics in the warehouse, evidence in tickets/CRM/deploy logs |
| Check it is not coincidence | Rarely done | Correlation accepted as cause |
| Decide what to do | Business lead | Days after the movement |

### Four structural problems

**1. Dashboards are descriptive, not diagnostic.** They are built to show *what*. The moment the question becomes *why*, the user is chasing numbers across tools. **[R]**

**2. Alert fatigue is measurable.** Roughly 70% of analyst time is spent investigating alerts that turn out to be legitimate, and analysts reviewing 30+ alerts a day show a 22% decline in detection accuracy. **[R]** A system that fires on every fluctuation trains people to ignore it.

**3. Evidence is fragmented across formats.** The reason for a conversion drop is rarely in the warehouse — it is in support tickets, a deploy changelog, a CRM note, a competitor's promotion. Structured analysis alone cannot reach it.

**4. Correlation is routinely presented as causation.** Two series moving together is not evidence one caused the other, but a narrative layer will happily say it did.

### The risk of the obvious solution

Connecting an LLM to the warehouse addresses none of the above and adds a new failure mode: fluent, confident, unverifiable prose. The credit-risk audit **[R]** is the concrete version — the model's priors overrode supplied evidence, in exactly the domain where being wrong is expensive.

---

## 3. Users

Three personas are implemented, with genuinely different data access and decision rights — not cosmetic labels.

### Analytics Lead — *Meera*

| | |
|---|---|
| **Pain** | Spends days reconstructing why a metric moved; asked to defend the method |
| **Decision** | Is this explanation defensible enough to circulate? |
| **Needs** | Method, contribution, counterfactual result, lineage |
| **Output** | Ranked hypotheses with evidence, decomposition, verification record, full audit trail |
| **Value** | Investigation becomes review. **[A]** |

### Regional / Operations Lead — *Priya*

| | |
|---|---|
| **Pain** | Owns a region, sees the number late, cannot tell if it is her problem |
| **Decision** | Do I escalate, and to whom? |
| **Needs** | What moved in *her* region, whether it is material, who owns the fix |
| **Output** | Region-scoped analysis, named owner, monitoring metric, a request she is entitled to raise |
| **Value** | Escalation with evidence attached rather than a hunch. **[A]** |

**Entitlement is real for this persona:** she is denied `crm_notes`, and the system tells her *how many* items were withheld rather than silently showing a shorter list.

### Finance Director — *Arjun*

| | |
|---|---|
| **Pain** | Must explain quarter movements to stakeholders; cannot audit the explanation |
| **Decision** | Is this material to the quarter, and is the explanation sound? |
| **Needs** | Financial magnitude, reliability, what the system does *not* know |
| **Output** | Impact range with its basis named, calibrated reliability, explicit uncertainty |
| **Value** | An explanation that survives being questioned. **[A]** |

**His economics differ:** a wrong call at director scope carries a higher configured decision value, so the same evidence can route differently. **[A]**

---

## 4. The product

### Five stages, one screen

```
DETECT  →  ATTRIBUTE  →  EXPLAIN  →  RECOMMEND  →  VERIFY
  ↓           ↓             ↓            ↓            ↓
Is it real  What drove   What does    What should  Can every
and does    it, and      the evidence  happen, and  claim be
it matter?  where?       support?      who acts?    checked?
```

### What the user actually sees

The default screen answers five questions in one scroll, in the order a business user asks them — **not** in the order the system computes them:

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

### It is a decision workspace, not a chatbot

There is no chat box. A conversational interface would invite the user to ask the model questions it must not answer from data it must not reach. Instead the product presents a **decision** — with the evidence behind it one click away, the method two clicks away, and the full audit trail three.

---

## 5. Why existing tools are insufficient

Positioning against categories, not vendors. No competitor capability claims are made.

| | Answers *what* | Answers *why* | Shows evidence | Says when it doesn't know | Bounded action |
|---|:---:|:---:|:---:|:---:|:---:|
| **Dashboards** | ✅ | ✕ | ✕ | ✕ | ✕ |
| **Threshold alerting** | ✅ | ✕ | ✕ | ✕ | ✕ |
| **Manual SQL analysis** | ✅ | ✅ | ✅ | depends on the analyst | ✕ |
| **Generic BI copilots** | ✅ | prose | ✕ | ✕ | ✕ |
| **Generic RAG assistants** | ✕ | prose | citations | ✕ | ✕ |
| **BusinessIntelligence.ai** | ✅ | ✅ | ✅ | ✅ | ✅ |

**The gap is the last two columns.** Several categories produce an explanation. What none of them does is *decline* — and produce a bounded, owned action when it does answer.

**Manual SQL analysis is the honest benchmark.** A good analyst does everything in this table. What they cannot do is run in 15 seconds, apply the same materiality rule every time, or leave an audit trail that survives their absence. This product is not competing with a spreadsheet; it is competing with *how long the spreadsheet takes*.

---

## 6. Technical innovation

### 6.1 A deterministic analytical core

Every quantitative claim is produced before any language model is involved.

| Stage | Method | Why this one |
|---|---|---|
| **Decompose** | STL | Remove trend and seasonality *first*, then detect breaks in the residual — the seasonality-first ordering is a named finding in the monitoring literature **[R]** |
| **Score** | Robust MAD z-score | Median absolute deviation is not dragged by the outlier it is trying to find |
| **Locate** | PELT changepoint | Finds *when* the level shifted, not just that a threshold was crossed |
| **Gate** | Materiality rule | Statistical significance **and** business effect — an 8% move in a volatile metric may be noise; 2% in a stable one may be real **[R]** |

The materiality gate is the alert-fatigue answer. One demo scenario is a **+5.9% movement that is statistically real and deliberately produces no alert**, because it fails the business leg.

### 6.2 Attribution that separates contribution from cause

| Layer | Method | Question answered |
|---|---|---|
| **Identity** | LMDI | Which *factor*? Sessions × conversion × AOV × realisation — closes to **0.000000000%** residual **[M]** |
| **Dimensions** | Adtributor | Which *slice*? (Bhagwan et al., NSDI '14) **[R]** |
| **Stability** | Moving-block bootstrap | Would the ranking survive resampling? **STRONG — 100% of 300 resamples** **[S]** |
| **Causality** | Difference-in-differences | May we say "caused"? |

**LMDI's value is exactness.** It is residual-free by construction, so the decomposition cannot quietly absorb what it fails to explain. When our first implementation closed to only 94.8%, that was treated as a defect and traced to a population mismatch — not tuned away.

**DiD produces a licence, not a score.** Parallel-trend test, specificity floor, temporal precedence. If it fails, the wording stays associative and the verification gate enforces that.

### 6.3 Evidence from both worlds

- **Hybrid retrieval** — BM25 for rare exact tokens (`PG-504`), dense embeddings for paraphrase, fused by reciprocal rank fusion.
- **Cohort evidence** — not "here are 34 tickets" but "35 documents in the event window against none in the preceding 8 weeks".
- **Contradiction is surfaced, never suppressed** — the UI shows contradicting evidence *first*, because it is what a reader is most likely to skip and most needs to see.

**A measurement we are keeping because it is honest:** on our first corpus, hybrid retrieval did *not* beat BM25. A realism audit found the corpus held only 13 distinct document texts across 895 records — there were no paraphrases for dense retrieval to catch. After widening it, every score fell **and dense recall@10 (0.778) overtook BM25 (0.654)**. **[S]** The weaker numbers are the truthful ones.

### 6.4 The trust layer

| Control | Mechanism |
|---|---|
| **EvidenceBundle** | Frozen and hashed before generation. If a fact is not in it, it does not exist to the narrative |
| **Verification gate** | 10 deterministic checks: numeric allowlist, driver membership, citation validity, causal licence, lever membership |
| **Bounded retry** | Exactly one, enforced in two places |
| **Deterministic fallback** | A template narrative, itself verified |
| **Abstention** | Six typed states, each with a different remedy |
| **Human review** | A real workflow interrupt on a durable checkpoint |

### 6.5 What the LLM does — and does not

| The LLM **does** | The LLM **does not** |
|---|---|
| Write the sentence, in a fixed schema | Produce, adjust or infer **any number** |
| Choose emphasis for a persona | Decide materiality, confidence or the action |
| Phrase an approved lever | Invent a lever — an unknown id is rejected |
| — | Choose a route — **no routing predicate reads model output** |
| — | Access the warehouse — **no tools, no handle** |
| — | Assert causality — the wording is licensed upstream |

Three structural guarantees make this checkable rather than aspirational: the request has **no `tools` key**; `Narrative` has **no `confidence` field**; and routing predicates are asserted against their own **source code**, so one that started reading model output fails even if its behaviour looked correct.

---

## 7. Architecture

```
                          USER
                            │
                    ┌───────▼────────┐
                    │   Streamlit    │  presentation only — computes nothing
                    └───────┬────────┘
                    ┌───────▼────────┐
                    │   LangGraph    │  workflow runtime — 26 nodes, 11 terminals
                    └───────┬────────┘
                    ┌───────▼────────┐
                    │ Semantic +     │  KPI contracts · row/column/source policy
                    │ Entitlement    │  ◄── THE ONLY DATABASE CALLER
                    └───────┬────────┘
              ┌─────────────┼─────────────┐
        ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼──────┐
        │ Detection │ │Attribution│ │ Retrieval  │
        │ STL·MAD·  │ │LMDI·Adtri-│ │BM25+dense  │
        │ PELT      │ │butor·DiD  │ │+RRF        │
        └─────┬─────┘ └─────┬─────┘ └─────┬──────┘
              └─────────────┼─────────────┘
                    ┌───────▼────────┐
                    │ EvidenceBundle │  ══ FROZEN + HASHED ══
                    └───────┬────────┘
                    ┌───────▼────────┐
                    │  Verification  │  10 deterministic checks
                    └───────┬────────┘
                    ┌───────▼────────┐
                    │      LLM       │  wording only · no tools · optional
                    └───────┬────────┘
                    ┌───────▼────────┐
                    │ Recommendation │  levers · calibration · expected-loss rule
                    │ + Deferral     │
                    └───────┬────────┘
              ┌─────────────┴─────────────┐
        ┌─────▼─────┐               ┌─────▼─────┐
        │  DELIVER  │               │  HUMAN    │
        └───────────┘               └───────────┘
```

### Four responsibilities, four different mechanisms

| Responsibility | Owned by | Never touched by |
|---|---|---|
| **Quantitative truth** | SQL, statistics, business rules | the LLM |
| **Evidence** | Hybrid retrieval, entitlement-filtered | the LLM |
| **Narrative** | The LLM, schema-constrained | — |
| **Decision escalation** | Business rules + human | the LLM |

---

## 8. Trust and responsible AI

This is the section we would most like to be questioned on.

| # | Control | How it is enforced | Evidence |
|---|---|---|---|
| 1 | **No LLM warehouse access** | No tools key; no database handle in the module | Asserted against the recorded request **[M]** |
| 2 | **No LLM-generated numbers** | Numeric allowlist derived from the frozen bundle | 0 false acceptances / 10 corrupt narratives **[S]** |
| 3 | **No model-selected routing** | Predicates asserted against their own source | **[M]** |
| 4 | **Entitlement before retrieval** | Candidates filtered *before* ranking | 9-test chain across 6 stages **[M]** |
| 5 | **Evidence freeze** | Hashed bundle; nothing added after | Hash identical across a human pause **[M]** |
| 6 | **Deterministic verification** | 10 checks, no model involved | **[M]** |
| 7 | **Causal-language gate** | DiD licence, enforced per hypothesis | Denied on S3 **[M]** |
| 8 | **Uncertainty** | Banded confidence with a track record | **[S]** |
| 9 | **Abstention** | Six typed states | 2 of 8 scenarios **[M]** |
| 10 | **Human review** | Real interrupt, resumable | 4 typed outcomes **[M]** |
| 11 | **Audit and lineage** | Row per read incl. denials; 15 lineage records/run | **[M]** |

### Why filter-before-rank matters

Filtering restricted documents *after* ranking still lets them influence the scores of everything around them — which leaks information about their existence and content even when they are dropped. The ordering is asserted by test, not assumed.

### Calibration is reported honestly

Of four confidence bands, only **HIGH** has enough observed cases to quote a rate. MEDIUM and LOW report **UNCALIBRATED** — the system says it does not know how often it has been right, because it does not. And 12-of-12 is deliberately **not** treated as 100%: fed raw into the deferral rule it collapsed to "always automate", so the arithmetic uses a smoothed 0.93 while the display shows the honest raw counts.

### The strongest evidence that the gate is real

**It blocked our own fallback template.** A bug caused the template to cite two evidence ids the bundle did not contain, and verification refused it. A gate that only ever passes what you produce is not a gate.

---

## 9. Demonstrated scenarios

Eight executable scenarios, all running end to end. Five are worth a judge's attention.

### S1 — Strong evidence → recommendation
West revenue −25%. Conversion rate identified as driver, localised to Web/Mobile App × West, 7 corroborating documents, HIGH reliability, action: escalate to Engineering.
**Proves:** the full pipeline produces a bounded, owned action.

### S2 — Conflicting evidence → human review
South × Apparel −21.9%. Two explanations equally supported — competitive pressure and stock availability — **implying different owners**. The system stops and asks.
**Proves:** it does not guess when guessing sends the wrong team.

### S4 — Sparse history → abstention
A new category with 52 of the 56 days a seasonal baseline needs. It refuses to extrapolate and says how long to wait.
**Proves:** a decline is actionable when it says *what would change it*.

### S6 — Entitlement restriction → evidence withheld
Same event as S1, read by an operations lead denied CRM notes. One item withheld, **and the count is shown**.
**Proves:** access control that is visible rather than silent.

### S7 — Non-material artifact → no false alert
A channel rename (`marketplace` → `Marketplace`) looks like +5.9% growth. Statistically real, business-immaterial. **No alert, no recommendation, no invented cause.**
**Proves:** the alert-fatigue answer. **[R]**

### Why these five prove the product is different

Three of the five end in the system **not** producing a recommendation. A demo built to impress would show five variations of S1. These scenarios exist because the hard part of this problem is not explaining a movement — it is knowing which movements to explain.

---

## 10. Prototype evaluation

> **All figures below are measured on a generated dataset** — seed `20260821`, 535 days, 6 injected events. Their ground truth is known by construction. **These are not production accuracy and do not predict performance on real business data.**

### Detection **[S]**

| Metric | Value | What was measured |
|---|---:|---|
| Precision | 1.000 | 64 slices scanned, 16 true positives |
| Recall | 1.000 | Every *injected* event found |
| False positives | **0** | Across the 48 slices with no injected event |

**The honest reading:** recall of 1.000 means every event *we injected* was found, and those events were built to be detectable by this method's assumptions. The figure that is *not* guaranteed by construction — and therefore the meaningful one — is **0 false positives on 48 clean slices**.

### Attribution **[M][S]**

| Metric | Value |
|---|---|
| LMDI identity closure | **0.000000000%** residual **[M]** |
| Ranking robustness | Top driver held in **100% of 300 resamples** **[S]** |
| Causal licence | Granted on S1, **denied on S3** **[M]** |

### Retrieval **[S]**

| Method | precision@5 | recall@10 | MRR |
|---|---:|---:|---:|
| BM25 | 0.552 | 0.654 | 0.833 |
| **Dense** | 0.567 | **0.778** | 0.817 |
| RRF (hybrid) | 0.552 | 0.697 | **0.838** |

Measured after a realism audit widened the corpus. Earlier, easier numbers (BM25 p@5 0.810) are not reported as current.

### Verification **[S]**

| Metric | Value |
|---|---:|
| False acceptance | **0** of 10 corrupt narratives |
| False rejection | **0** of 6 valid narratives |
| Injected violations caught by expected code | **9 / 9** |

### System **[M]**

| Metric | Value |
|---|---:|
| Automated tests | **574 passing, 0 failures** |
| Scenarios end to end | **8 / 8** |
| Graph vs direct-module agreement | **8 / 8** — orchestration changed no decision |
| Security tests | **32**, incl. a 6-stage leak chain |
| Restricted items reaching any stage | **0** |

### Outcomes and telemetry **[M]**

| | |
|---|---:|
| Automation rate | 50% (4/8) |
| Review rate | 25% (2/8) |
| **Abstention rate** | **25% (2/8)** |
| Verification failure rate | 0% |
| Runtime | 4–50 s per scenario |
| Orchestration overhead | 13–42 ms (0.08–0.80%) |

These rates describe *the demonstration set*, which was built to exercise every terminal. A production mix would be dominated by "no material event".

### What is not measured

**`LIVE LLM EVALUATION PENDING`** — no API key is available in this environment. Model latency, token usage, cost and first-pass verification rate are **unmeasured and not estimated**. The system runs in verified-template mode, which the UI labels explicitly.

---

## 11. Product design

The interface was designed against published UX research (Growth.Design case studies) and then **audited against rendered output** — three principles failed on first render and were fixed.

### The journey

**What changed → Why → Evidence → Confidence → Action**

That is the order a business user asks. The system's internal order is Detect → Attribute → Retrieve → Verify → Recommend — the order it was *built* in, which appears only in the Method tab.

### Five decisions and what they came from

| Principle | Decision |
|---|---|
| **Uncertainty markers** | Reliability always carries its qualifier *inline* — "12 of 12" never appears without "synthetic evaluation set" beside it |
| **Recognition over recollection** | The movement is the largest element on the page; nothing competes with it |
| **Habituation through irrelevance** | A non-event renders a *visibly quieter* screen — no chart, no action. Showing less when the system knows less is the point |
| **Paradox of choice** | 3 drivers and 2–3 hypotheses by default, with explicit drill-down |
| **Show the work honestly** | The loading panel lists the *real* stages in business language; nothing is padded to look substantial |

### Five epistemic classes, visually distinct

A reader must never confuse a measured number with a generated sentence:

`OBSERVED FACT` · `ANALYTICAL RESULT` · `RETRIEVED EVIDENCE` · `HYPOTHESIS` · `RECOMMENDATION`

### Progressive disclosure

| Level | Content |
|---|---|
| **1 — Decision** | What happened, what to do |
| **2 — Explanation** | Drivers, contribution, affected slice |
| **3 — Evidence** | Supporting and contradicting sources |
| **4 — Method** | STL, LMDI, DiD, RRF, verification checks |
| **5 — Audit** | Lineage, graph path, entitlement, telemetry |

A business user never leaves level 1–2. A judge can reach level 5 in three clicks.

---

## 12. Business value

**This repository contains no validated enterprise ROI, and none is claimed.** What follows is the *mechanism* of value, with any quantification labelled as an assumption a pilot would test.

### Operational value — less manual investigation

Today a material movement triggers a manual investigation across warehouse, tickets, deploy logs and CRM. The system produces a ranked, evidenced explanation in **4–50 seconds** **[M]**.

**What we can evidence:** the pipeline completes and its output is verified.
**What we cannot:** how much analyst time that displaces. That depends on baseline investigation time, which we have not measured. **[A]**

### Decision value — shorter signal-to-action

Every finding carries an owner, a monitoring metric and a bounded action. The route from signal to action is compressed from *movement → analyst → meeting → decision* to *movement → decision, with the analysis attached*.

**What we can evidence:** actions are lever-bound, owner-named, monitoring-attached, and scoped. **[M]**
**What we cannot:** cycle-time reduction in a real organisation. **[A]**

### Risk value — fewer unsupported conclusions

This is the most defensible value line, because it is the one we measured.

| Risk | Control | Evidence |
|---|---|---|
| Fabricated numbers | Numeric allowlist against a frozen bundle | 0 false acceptances **[S]** |
| Unsupported causal claims | DiD licence + verification | Denied on S3 **[M]** |
| Acting on ambiguous evidence | Cost-sensitive deferral | 25% abstention **[M]** |
| Alert fatigue | Materiality gate | S7 produces no alert **[M]** |
| Over-broad automation | Scope separation + never-automate list | Request ≠ execute **[M]** |

**The counterfactual worth naming:** the alternative to abstention is a system that always answers. Given that reasoning-tuned models abstain 24% worse than non-reasoning ones **[R]**, "always answers" is the default outcome unless something is built to prevent it.

### Governance value — traceability and entitlement

Every read is audited including denials, correlated to the run the user saw. Every run carries 15 lineage records answering: which contract, which policy, which method, which counterfactual, which documents, which bundle hash, which model. **[M]**

**What we can evidence:** the trail exists and is complete.
**What we cannot:** that it satisfies any particular regulatory regime. No compliance assessment has been done. **[A]**

### A note on what we deliberately did not write

A proposal of this kind usually contains a value table with hours saved and rupees recovered. We could construct one from the assumptions above. We have not, because this project's central claim is that it distinguishes what it knows from what it assumes — and a fabricated ROI table in *this* document would undermine every measured claim in Section 10.

**What we would propose instead:** a pilot on one KPI family, measuring time-to-explanation against the current baseline, over one quarter. That converts an argument into a data point.

---

## 13. Implementation

### What runs today

| Layer | Technology | Note |
|---|---|---|
| Frontend | Streamlit | Presentation only; enforced by test |
| Orchestration | LangGraph | 26 nodes, durable checkpoints |
| Analytics | statsmodels, ruptures, scipy, numpy | In-process |
| Warehouse | DuckDB, single file | One guarded query path |
| Retrieval | sentence-transformers + numpy | 1,336 documents in memory |
| Workflow state | SQLite | Survives restart |
| Narration | Anthropic API | **Optional** |

```bash
pip install -r requirements.txt
python -m data.generate && python -m retrieval.build_index
streamlit run app.py
```

**Running without an API key is a supported mode, not a degraded one.** Everything except the sentence construction is identical; the UI labels it *Verified template mode* and states that no model reviewed the text.

**This is a prototype, and we describe it as one.** One process, one user, no authentication, no cloud. Section 14 says what changes and when.

---

## 14. Production path

From `docs/PRODUCTION_EVOLUTION.md`. Each migration has a **trigger** — an observable condition — rather than a volume.

| Migration | Trigger |
|---|---|
| DuckDB → enterprise warehouse | Data exceeds one machine, a second writer is needed, or the data already lives in a warehouse |
| In-memory index → managed vector search | **Security, before scale** — the first customer with data-isolation requirements |
| SQLite → durable workflow state | The app runs on more than one process |
| Streamlit → embedded frontend | Insights must appear where analysts already work, or >~10 concurrent users |
| **Dropdown → enterprise IAM** | **Before any real data.** Not a scale trigger — a correctness one |
| Direct SDK → model gateway | Key rotation, per-tenant quota or cost attribution required |
| Run telemetry → observability platform | Someone must answer "what happened last Tuesday" after a restart |
| One process → horizontal workers | A second concurrent user |

### The honest constraint

The binding limit is **not CPU**. DuckDB permits a single writer and the audit log is written on every read, so concurrency is a *storage* migration, not a worker-count change. Concurrent capacity today is roughly **two simultaneous users**. Saying "it scales horizontally" would be false.

### What would not change

The deterministic/AI boundary, the evidence freeze, entitlement-before-ranking, and the typed module contracts. These are the parts that were expensive to get right, and none is a prototype convenience.

---

## 15. Risks and mitigations

| # | Risk | Mitigation | Residual limitation |
|---|---|---|---|
| 1 | **Synthetic data** — all evaluation is on generated data | Every report labels it; a realism audit widened the corpus and *lowered* the scores | No validation on real business data. The largest open risk |
| 2 | **Limited calibration** — 64 synthetic cases | Bands below 10 cases report `UNCALIBRATED`; smoothing prevents 12/12 reading as certainty | Only one band calibrated. `p_human` is seeded, not measured |
| 3 | **LLM availability** | Verified template mode; one bounded retry; graph terminates correctly under a permanently failing narrator | Live latency, token and cost figures unmeasured |
| 4 | **Retrieval quality** | Hybrid retrieval; contradiction surfaced; withheld items counted | Corpus diversity 3.4% — far below a real ticket stream |
| 5 | **Causal inference limits** | DiD with parallel-trend test and specificity floor; licence denied when it fails | DiD assumes no unobserved confounder affecting only the treated slice. **It licenses wording, not truth** |
| 6 | **Model hallucination** | No tools, frozen bundle, 10 checks, fail-closed to template | Verified against corrupt narratives *we* wrote. How often a real model trips them is unmeasured |
| 7 | **Data access** | Row/column/source entitlement before ranking; audited | **No authentication** — persona is a dropdown. Authorisation is real; identity is not |
| 8 | **Feedback loop unvalidated** | Five typed outcomes; two update live | Zero real cycles. Implemented and wired, **not validated** |

---

## 16. Roadmap

### Now — Round 2 prototype ✅
Working system: 6 KPIs, 3 sources, 3 personas, 8 scenarios, 574 tests, verified entitlement, human review, full audit trail. Single process, synthetic data, no authentication.

### V2 — Enterprise pilot
**Goal: replace assumptions with measurements.**

| Priority | Item | Why |
|---|---|---|
| 1 | **Enterprise IAM** | Before any real data. Every existing entitlement test survives unchanged |
| 2 | **One real KPI family, one team** | Converts synthetic evaluation into measurement |
| 3 | **Real calibration** | Replace 64 synthetic cases with observed outcomes; the loop exists and has never run |
| 4 | **Live LLM evaluation** | Latency, tokens, cost, first-pass verification rate |
| 5 | **Baseline time-to-explanation** | The one measurement that would let us make a value claim |

### V3 — Production platform
Enterprise warehouse; per-tenant retrieval; durable workflow state and workers; embedded frontend; model gateway; observability with retention.

**Deliberately not on the roadmap:** autonomous agents, agent swarms, or letting the model query the warehouse. Those are not deferred features — they are the architecture this system exists to avoid.

---

## 17. Conclusion

The differentiator is **not** that BusinessIntelligence.ai uses a language model.

The differentiator is that it combines **deterministic analytics**, **evidence retrieval**, **controlled LLM narration**, **mechanical verification** and **calibrated abstention** into a decision-support system that knows when it should and should not act.

Three things follow from that, and each is testable rather than asserted:

**Every number is computed, never generated.** The model cannot reach data, cannot produce a figure, and cannot choose what happens next. This is architecture, not instruction.

**Nothing is delivered unverified.** Ten deterministic checks run against a frozen, hashed evidence bundle before any narrative reaches a user — and the gate has demonstrably blocked our own output.

**It declines.** Two of eight scenarios end without a recommendation. The system says *why*, says *what would change its mind*, and routes to a human when two explanations imply different owners.

A dashboard tells you what moved. An LLM will tell you why, confidently, whether or not it knows. This system tells you why, shows the evidence, recommends what to do — **and tells you when it cannot.**

That last capability is the hardest to build, the easiest to skip, and the only one that makes the other three safe to rely on.

---

*Team SouthernHustlers · Accenture Innovation Challenge 2026 · Problem Track 3*
*Evidence mapping: `R2_BUSINESS_PROPOSAL_SOURCE.md` · Prototype: 574 tests passing*
