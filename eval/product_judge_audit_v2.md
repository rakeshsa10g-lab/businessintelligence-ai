# Second-pass adversarial judge audit — BusinessIntelligence.ai

**Companion to, not a replacement for, `eval/product_judge_audit.md`.** That
audit scored 74/100 and concluded the product was materially stronger than the
pitch carrying it. This pass re-evaluates the current state independently, then
compares.

**Method.** Current pitch artefacts inspected as rendered images. The Streamlit
app started and driven live (S2 read end to end in the browser; S1 read from the
regenerated walkthrough output). Deck HTML, hero assets and pixel dimensions
checked directly. Source read for every claim this document disputes. No code
was modified.

**Standing correction applied throughout.** Where this audit lowers a score
against the previous one, it is stated explicitly whether the *product got
worse* or *my information got better*. In every case below it is the second.
The code that produced the findings in §11 was identical on the day of the first
audit; I had not run the system under concurrency and had not read
`eval/technical_competition_audit.md`, which did not yet exist.

**On the missing API key.** As instructed, nothing here penalises the absence of
live-model performance figures. `LIVE LLM EVALUATION PENDING` is treated as a
correctly-labelled gap, not an overclaim. Where R2-MPE-10 is mentioned it is as
a neutral statement of coverage.

---

# Part 1 — Blind first impression

Simulated cold: deck opened at slide 01, read forward, no documentation, no
previous audit in mind.

| Question | Answer within 30–60s | Verdict |
|---|---|---|
| **1. What does this product do?** | Detects a material KPI movement, decomposes it, gathers evidence, states how reliable it is, and recommends a bounded action. Slide 03 now shows the entire screen across two panels with the flow banner *"what changed → why → evidence → how reliable → what to do, in the order a business user asks."* | **Strong.** Answerable from slide 03 alone |
| **2. Who is it for?** | Still weak. "Meera · Analytics Lead" appears in the screenshot masthead at small type. Personas arrive at slide 08. Slide 01 is still a market-statistics slide with no named human | **Unchanged from the previous audit** |
| **3. What is different?** | **Now answerable at slide 03.** A red-bordered card sits beside the product screenshot: *"…and when the evidence conflicts, this screen does not appear at all — On S2 two explanations are equally supported and imply different owners. The system stops and asks a person instead of picking."* | **Materially improved.** This was the single biggest failure of the previous audit and it is closed |
| **4. Why should I care?** | Slide 01's four statistics and the `Day 1 → Day 2 → window has closed` flow, unchanged and still strong. Slide 11 now adds four named value mechanisms with *"No ROI figure is claimed anywhere in this project"* in the kicker | **Improved** |
| **5. Why should I trust it?** | Slide 03 shows a real screenshot end to end; slide 06 shows a gate that blocked the team's own template and states plainly *"verification mechanism tested ≠ live LLM reliability measured"*; slide 09 leads with **0 false positives across 48 clean slices** rather than 1.000/1.000 | **Materially improved** |

### The one thing a cold read still gets wrong

The slide 03 card ends with a pointer: **"Slide 05."** Slide 05 is *Every number
is computed, never generated*. The abstention slide is **07**. A judge who
follows the deck's only cross-reference lands on the wrong slide. Verified:
`grep -oE "Slide [0-9]+" submission/deck/slides/*.html` returns exactly one
match, in `slide-03.html`, and `grep -l "abstention is the product"` returns
`slide-07.html`.

### Comparison with the previous first impression

Previously two of six zero-context answers required reading past slide 03, and
one of them was the differentiator. **Now one remains** — *who is it for* — and
it is the least consequential of the six. The deck front-loads the thing that
makes the product uncopyable instead of burying it at slide seven. That is the
largest single improvement in the submission.

---

# Part 2 — Current score /100

Same fourteen categories, same weights, so the comparison is exact.
Weights: 4 · 6 · 4 · 12 · 8 · 9 · 9 · 8 · 7 · 7 · 10 · 3 · 5 · 8 = 100.

| # | Category | Prev | Now | Δ | Evidence for the delta |
|---|---|:---:|:---:|:---:|---|
| 1 | Problem importance | 8 | **8** | 0 | Slide 01 unchanged, including its two dead-space bands. Correctly left alone — it was already the strongest problem framing in the deck |
| 2 | Problem clarity | 9 | **9** | 0 | Unchanged |
| 3 | User pain | 7 | **7** | 0 | No persona named on slide 01. The cheapest unclaimed improvement in the deck, and it was not taken |
| 4 | Product differentiation | 8 | **9** | **+1** | Slide 03 red card; demo reaches the refusal at 1:30 rather than 2:15; the causal licence is now visible **in the product** — S2's hypothesis block renders *"Association only — the counterfactual test did not license a causal claim"* on the default screen. Held back from 10 by the stale hero (§3) and the broken cross-reference |
| 5 | User value | 6 | **7** | **+1** | Evidence items now render on the workspace, not just a count; a KPI time-series chart with the PELT changepoint and comparison window; four value mechanisms on slide 11. Capped by the interactivity gap: `ui/state.py:132` hardcodes `kpi_id="net_revenue"` and the scenario list is eight pre-baked runs imported from the eval harness |
| 6 | Technical credibility | 9 | **8** | **−1** | **Information, not regression.** `eval/technical_competition_audit.md` §7.1 measured cross-principal result leakage under two threads; I verified the cause is unfixed — `semantic/gateway.py` still holds one module-global `_conn`, `_lock` guards creation only, and `guarded_query` calls `con.execute(sql)` on the shared handle. Offsetting this: the retrieval contradiction, corpus size and test counts are all now consistent, which was a real P0 and is genuinely closed |
| 7 | Responsible / controlled AI | 10 | **9** | **−1** | **Information, not regression.** Two items. (a) `graph/nodes.py:325` still returns a constant `terminal_reason`; an infrastructure crash is still narrated as *"a movement is real but nothing corroborates an explanation"* — a false statement that a search occurred, in a product whose thesis is honest failure. (b) `grep -rn "from feedback\|import feedback"` across `graph/`, `ui/` and `app.py` returns **nothing**, while `eval/judge_defense.md:353` and `R2_BUSINESS_PROPOSAL.md:585` both say the loop is *"implemented and wired"*. The mechanisms remain outstanding; the claim is now demonstrably a half-step ahead of the code |
| 8 | UX quality | 7 | **8** | **+1** | Evidence cards with source, date, retrieval method and excerpt — contradicting evidence leading, which is the right call. KPI series gated on `DetectionOutcome` so S7 renders unannotated. Colour rule stated inline: *"Red pushed the KPI down · green pushed it up."* `UNCALIBRATED` now glossed: *"The signal is strong, but its track record is not established."* Held back by three small defects in §12 |
| 9 | Business value | 5 | **7** | **+2** | Four mechanism cards on slide 11 — faster diagnosis, safer decisions, governed action, auditability — each tied to something built, with the no-ROI statement at the point of use. Still no measured number, correctly |
| 10 | Prototype quality | 8 | **8** | 0 | Three real UI additions raise it; the newly-evidenced concurrency defect and the unchanged access problem (no video, no hosted URL, ~2.5 GB build) hold it level |
| 11 | Demo memorability | 6 | **7** | **+1** | Refusal at 1:30; the setup line *"Every tool in this category will pick one and write you a confident paragraph. Watch what this one does instead"* is better tension-building than the cold open I suggested. Capped: still no recording, and the script has no sub-90-second fallback cut |
| 12 | Scalability / production credibility | 6 | **6** | 0 | The condition-triggered migration framing remains excellent. Offset by a newly-visible misframing: the submission describes concurrency as a *capacity* limit ("roughly two simultaneous users", "a storage migration") when the measured failure at two users is *correctness and entitlement*, not throughput |
| 13 | Competitive defensibility | 7 | **7** | 0 | The moat is unchanged in substance. The interactivity gap is now better understood as a live threat rather than a theoretical one |
| 14 | Judge comprehension | 6 | **8** | **+2** | The largest gain. Slide 03 shows the whole product; slide 06 removed the misleading 0% stat outright rather than caveating it; slide 09 leads with the number a generator cannot rig; slide 11 answers "so what" in four cards. Held back by residual dead space on 05, 06 and 09 |

### Weighted

| # | Category | Now | Weight | Weighted |
|---|---|---:|---:|---:|
| 1 | Problem importance | 8 | 4 | 32 |
| 2 | Problem clarity | 9 | 6 | 54 |
| 3 | User pain | 7 | 4 | 28 |
| 4 | Product differentiation | 9 | 12 | 108 |
| 5 | User value | 7 | 8 | 56 |
| 6 | Technical credibility | 8 | 9 | 72 |
| 7 | Responsible / controlled AI | 9 | 9 | 81 |
| 8 | UX quality | 8 | 8 | 64 |
| 9 | Business value | 7 | 7 | 49 |
| 10 | Prototype quality | 8 | 7 | 56 |
| 11 | Demo memorability | 7 | 10 | 70 |
| 12 | Scalability / production credibility | 6 | 3 | 18 |
| 13 | Competitive defensibility | 7 | 5 | 35 |
| 14 | Judge comprehension | 8 | 8 | 64 |
| | **Total** | | **100** | **787** |

### CURRENT OVERALL SCORE: **79 / 100**

### PREVIOUS SCORE: **74 / 100**

### NET CHANGE: **+5**

**Why not more.** The transmission pass earned **+7** across six categories and
did so honestly — three claims were made *smaller*, one was found false in the
team's own UX audit. Two categories then gave back **−2** on evidence that did
not exist at the time of the first audit. The product improved; my picture of
the code also sharpened, and the two moved in opposite directions.

**What is capping the score.** Every remaining point is held by one of four
things: the deck still shows a pre-improvement screenshot (§3), no recording
exists, three measured technical defects are unfixed, and no value figure can be
produced without a pilot. Only the first two are inside the submission window.

---

# Part 3 — Did the improvements actually work?

| Improvement | Did it work? | Competitive impact | Remaining issue |
|---|---|---|---|
| **KPI time-series chart** | **Yes, in the app. No, in the deck.** `ui/components/kpi_series.py` reads `decomposition.dates/observed/trend` and `changepoint_dates` straight off `DetectionResult` — nothing computed in the UI. Live S2 renders *"Dashed line: changepoint detected by PELT (02 Jun 2026, 17 Jun 2026). Shaded band: the window compared against baseline."* | **High.** Closes a genuine BI-literacy gap: a BI audience expects the series before it accepts a decomposition of the series | **The deck hero does not contain it** — see below. Also: gating annotations on `DetectionOutcome` so S7 renders unannotated is the single best design decision in this pass |
| **Evidence visible on Workspace** | **Yes, in the app. No, in the deck.** Live S2 renders `8 supporting · 1 contradicting`, then a CONTRADICTS card, two SUPPORTS cards — each with source type, date, `via hybrid`, and an excerpt — then *"6 further items in the Evidence tab."* Contradicting leading is the right choice | **Very high.** This was the sharpest gap the previous audit found: a product arguing "don't take it on trust" was showing a count | Two defects. (1) The **deck hero still shows only `8 supporting`** and jumps to the reliability block. (2) `ui/components/evidence.py:221` uses `getattr(item,'title','') or 'Evidence'`, so CRM notes render a card whose title is the literal word **"Evidence"**, inside a section headed EVIDENCE. Visible on both S1 and S2 |
| **Earlier abstention / trust messaging** | **Yes.** Slide 03's red card, and the demo reaching the refusal at 1:30 | **Very high.** The previous audit's #1 rejection risk — *"I read three slides and could not tell what makes this different"* — is closed | The card's cross-reference points to **Slide 05**; the abstention slide is **07** |
| **Hero screenshot fix** | **Partially — and this is the headline finding.** The crop is gone: slide 03 now shows the product across two panels, top and bottom, including 109.9%, the evidence count, the reliability block, the recovery range and the "Raise the request" button. But the panels are a **split of the 24 Aug capture, not a re-capture** | **Was very high; now capped** | Verified by pixel arithmetic: `hero_s1_workspace.png` is 1400×3118 (24 Aug 18:22); `hero_s1_top.png` 1400×1560 and `hero_s1_bottom.png` 1400×1598 (26 Aug 00:32) — 1560+1598 = 3158, a 40px overlap that also explains the duplicated *"Show 1 smaller driver(s)"* at the panel seam. **The screenshot therefore predates `kpi_series.py` (00:10), `evidence.py` (00:12) and `drivers.py` (00:13).** All three of this pass's UI improvements are absent from the deck |
| **Pitch claim corrections** | **Yes, and better than recommended.** The "0% verification failure" stat was **removed** rather than caveated — the right call, since the figure measured the deterministic template against a gate written for it. Replaced with 3/3 injected corruption classes and 10/10 corrupted narratives blocked, plus a *"Caveat, stated"* panel: *"the verification mechanism has been tested; live LLM reliability has not"* | **High.** Removes the sharpest credibility attack available | Slide 06's gate-flow row still carries ~55% dead space |
| **Retrieval metric corrections** | **Yes, fully, and more thoroughly than the previous audit asked.** Slide 09 now states: *"What they do **not** support: that fusion beats dense — RRF recall@10 is 0.697, between the two. Hybrid stays as a robustness mechanism, not as a measured win."* The stale `final_evaluation_report.md` §3 is corrected. The fix went into the **generator** (`eval/run_retrieval_eval.py`), not the generated file | **Medium-high.** Removes a non-sequitur a technical judge would have found in ten seconds | None. The team also caught an inversion in `R2_BUSINESS_PROPOSAL_SOURCE.md` that the previous audit missed, and the MRR-as-proof framing — both correctly handled |
| **Detection framing** | **Yes.** The synthetic table's highlighted top row is now **"False positives, 48 clean slices → 0"**. Precision is dropped entirely; recall appears second as *"Injected-event recall (events built to be detectable by this method) → 1.000"*, with the limitation inside the row label | **Medium-high, and yes — this is the better communication choice.** 0-FP-on-48-clean-slices is the half a generator cannot rig, and it moves the attackable number out of large type without hiding it | None |
| **Business-value framing** | **Yes.** Four mechanism cards, each tied to something built, under a kicker stating *"No ROI figure is claimed anywhere in this project"* | **High.** Converts the lowest-scoring category from apologetic to confident with no new claim | The pilot ask is unchanged and still does not name a buyer |
| **Growth.Design colour semantics** | **Yes, and resolved the right way.** The audit's own claim (red reserved for contradicting evidence only) was false and the driver chart disproved it. Resolved in favour of the chart — red = adverse, green = favourable — with the rule stated inline beneath the bars | **Low competitively, high for internal integrity.** A team that finds a false claim in its own UX audit and corrects the document rather than the product is doing the harder thing | None |
| **Demo restructuring** | **Yes.** Refusal at 1:30, evidence beat now shows evidence rather than touring a tab, S4's chart callout added | **High** | Two gaps: no recording exists, and there is no sub-90-second fallback cut. If the slot is shortened — common at scale — the differentiator is the first thing lost |

### The pattern

Nine of ten improvements worked, several better than the previous audit
specified. The failure is narrow and specific: **the two best UI improvements
exist in the product and not in the artefact that carries the product to a
judge.** That is the same class of error as the original crop, recurring one
level down — and it is invisible unless someone opens the app and the deck side
by side, which is exactly what this pass did.
---

# Part 4 — Competitive differentiation, re-run

Same eight constructed archetypes. No competing submission was inspected; these
remain a risk model, not intelligence.

| # | Archetype | Position vs previous | Why |
|---|---|:---:|---|
| 1 | **Generic BI chatbot** | **Improved** | The gap was comprehension speed. Slide 03 now closes most of it, and the KPI chart gives a BI audience the exhibit they expect. They still beat us on *asking a second question* — see below |
| 2 | **RAG analytics copilot** | **Improved materially** | Their advantage was that citations look like evidence and read instantly. We now render source, date, retrieval method and excerpt on the default screen, with contradicting evidence first — which no RAG copilot does, because surfacing a document that argues against your answer is not a feature anyone builds by accident |
| 3 | **Multi-agent analyst** | **Unchanged** | Different axis. They win demo theatre; we win reproducibility. Slide 11's "deliberately not on the roadmap" line remains stronger than most teams will have |
| 4 | **ML anomaly detector + LLM** | **Improved** | Slide 09's reframing means our headline detection number is now the one they cannot rig either, and the KPI chart puts us on their visual territory |
| 5 | **Enterprise BI copilot** | **Improved, with one new exposure** | Better on evidence, governance and honest gaps. But `technical_competition_audit.md` §7.1 means a two-tab demo can break the entitlement guarantee — the one thing an enterprise archetype is *expected* to have right. Unfixed, this converts a strength into the sharpest available attack |
| 6 | **Consulting-style solution** | **Improved materially** | Slide 11's four mechanisms give a business judge something to write in the impact column without inventing a number. The gap that remains is a *measured* one, and it cannot be closed without a pilot |
| 7 | **UX-first winner** | **Improved most** | This was the archetype most likely to beat us, purely on the first 60 seconds. Slide 03 and the 1:30 demo close most of that gap. They still win on one thing: they will have a video |
| 8 | **Research-heavy technical** | **Unchanged** | We remain broad; a specialist beats us on any single axis. Correct trade |

### What could still beat us

1. **A team with a recording and a hosted URL.** Unchanged from the previous audit and still the largest accessible threat. Our prototype is stronger and less visible.
2. **A team whose product answers a question the judge invents.** `ui/state.py:132` hardcodes `kpi_id="net_revenue"`; the eight scenarios are a fixed list imported from `eval.run_recommendation_eval`. A judge who asks *"can I look at refund rate for East?"* gets a dropdown of pre-baked runs. Every layer beneath already accepts a `kpi_id`, a `Window` and a `slice_filter` — so this reads as a product decision, not a capability limit, which is worse.
3. **A team that produces one real measured number.** Unchanged.
4. **A team using public real data.** Unchanged, and still not worth chasing.
5. **A team that survives a two-tab stress test.** New. Most competitors will not be probed this way; if we are, §7.1 fires.

### What we are now clearly better at

- **Showing evidence rather than asserting it**, with contradicting evidence leading — genuinely rare.
- **Declining, visibly and early** — slide 03, demo 1:30, and three distinct refusal screens.
- **Causal restraint that a user can see** — S2's default screen carries *"Association only — the counterfactual test did not license a causal claim"*, and the review panel adds *"Where causal language is not licensed, the finding stands but the wording stays associative."*
- **Correcting our own claims downward under scrutiny** — three claims weakened in one pass, one self-audit found false. No archetype does this.
- **Naming what has not been measured** at the point of use rather than in an appendix.

### Which parts remain easy to copy

Unchanged from the previous audit: the five-stage flow, the four-tab layout, the
"no chat box" position, STL+MAD+PELT, the retrieval stack, the persona dropdown,
the materiality chip, the quieter non-event screen. **Newly copyable:** the KPI
time-series chart with changepoint annotation — a weekend, and now that it is on
a slide, an idea handed over freely.

### Which combination is actually defensible

Unchanged, and it is still the right answer:

> **abstention + verification + evidence freeze + decision rights.**

Any three are impressive; all four together mean the system can be *wrong*
without being *dangerous*. What this pass added is that three of the four are now
**visible to a judge** rather than inferable from documentation — which converts
a moat that had to be explained into one that can be seen.

The caveat that must be stated: `technical_competition_audit.md` §7.1 puts the
*entitlement* pillar — which sits underneath "decision rights" — at measured
risk under concurrency. The moat is intact in design and breachable in
deployment at two users.

---

# Part 5 — The three-second test

### The hero slide (03)

A judge looking away after three seconds retains:

> **A big black ↓ 25.0%, a purple five-step chevron banner, and the impression of
> a dense real screenshot.**

**Is that what we want them to remember?** **Partly — and it is the weakest link
in an otherwise fixed slide.**

Three seconds buys one object. Right now that object is `↓ 25.0%`, which is the
*dashboard* half of the story — the thing slide 01 spends four statistics
attacking. The differentiating object on that slide is the red-bordered card
reading *"…and when the evidence conflicts, this screen does not appear at
all"* — and it sits bottom-right, in body type, below two large screenshots.

**What should dominate visually.** Not a new element; a re-weighting of one that
already exists. The red card's headline should be the second-largest text on the
slide after the slide title — large enough to be read at the same glance as the
`25.0%`, so the three-second impression is *"a system that produces this, and
sometimes refuses to"* rather than *"a big number"*. Everything needed is
already on the slide.

### The product's first screen

Three seconds on the live app retains: **`↓ 25.0%` and the `MATERIAL MOVEMENT`
chip.** That is correct here — the product is answering a user who already knows
why they opened it. The three-second problem is a *pitch* problem, not a product
problem, and the two should not be conflated.

---

# Part 6 — The 30-second test

Can a judge, with no documentation, identify what changed, why, evidence,
reliability and action within 30 seconds?

| | Previous audit | Now | What changed |
|---|---|---|---|
| **What changed** | ✅ instantly | ✅ instantly | Unchanged — and now supported by the KPI series in the app |
| **Why** | ✅ | ✅✅ | The chart plus the analytical block plus the inline colour rule. In the app, S2 adds the causal qualifier in the same block |
| **Evidence** | ⚠ **a count only** | ✅ **in the app** / ⚠ **in the deck** | The default screen now renders real items with source, date, method and excerpt. **The deck hero still shows only `8 supporting`** |
| **Reliability** | ✅ | ✅✅ | `UNCALIBRATED` now glossed — *"The signal is strong, but its track record is not established"* — which removes the "something is broken" misread the previous audit flagged |
| **Action** | ✅ | ✅ | Unchanged and still strong: owner, authority, monitoring metric, range with basis, and a button whose text is the scope |

### Exactly what improved

1. **Evidence moved from a number to evidence** — the single most important fix in the pass, because the product's whole argument is that it does not ask to be taken on trust.
2. **The series is shown before the decomposition of the series** — a BI audience will not accept the second without the first.
3. **Uncertainty stopped leaking implementation vocabulary.**
4. **Causal restraint became visible on the default screen**, not only on S3 and not only in a log.

### What still fails the 30-second test

**Only in the deck, and only because of the stale hero.** A judge reading the PDF
gets four of five; a judge watching the app gets five of five. The gap between
those two experiences is one screenshot re-capture.

---

# Part 7 — The "why not a generic AI copilot?" test

*Judge: "This looks like an LLM-powered BI assistant. Why is this different?"*

Answered using only what the current prototype puts on screen, in the order it
appears:

1. **"The model did not produce any number you are looking at."** The analytical block says conversion rate accounts for 109.9% of the movement and explains why a share exceeds the whole. No language model writes a self-explaining over-100% share; an exact identity decomposition does.
2. **"It is showing you the documents, including one that argues against it."** The evidence block leads with `CONTRADICTS — Rival launches festive discounting early`. A copilot surfaces support; this surfaces dissent first.
3. **"It will not say *caused*."** S2's hypothesis block reads *"Association only — the counterfactual test did not license a causal claim."* That is a difference-in-differences result gating a word, enforced by a verifier — not a prompt instruction.
4. **"It refuses."** S2 ends in `AWAITING YOUR DECISION` with a real question, three ranked competing explanations each labelled `CONFLICTED ASSOCIATION ONLY` with supporting and contradicting counts, and four typed actions.
5. **"It knows why it cannot automate."** The review panel states: *"confidence is UNCALIBRATED: without an observed hit rate there is no p_model to put in the comparison, so the arithmetic that would justify automating is unavailable."*
6. **"The button says raise the request, not roll back."**

That is six answers a generic copilot cannot give, five of which are visible
without leaving the default screen.

### Is the differentiation visible enough?

| Surface | Verdict |
|---|---|
| **UI** | **Yes — and this is now the strongest surface.** All six answers above were read off a live session, not from documentation. This is a reversal: at the previous audit the UI was the surface where differentiation was *least* visible |
| **Deck** | **Mostly.** Slide 03's red card, slide 06's caveat panel, slide 07's outcome split, slide 09's label system, slide 11's comparison table. The gap is that the hero screenshot — the deck's only picture of the product — shows the *pre-improvement* screen, so answers 2 and 3 are invisible there |
| **Demo** | **Yes, from 1:30.** Before 1:30 the script is deliberately legible as a competent BI copilot; it says so and explains why. The residual risk is a shortened slot |

### Where differentiation exists technically but is still not visible

- **Entitlement before ranking.** Still a footnote on slide 08 and a withheld-count in the UI. The underlying insight — that a restricted document reaching the ranker has already influenced what you see — remains the most sophisticated idea in the security design and the least communicated.
- **The evidence freeze surviving the pause.** Still expressed as a hash rather than as a consequence.
- **Scope separation.** Visible on the button, but the *sentence* that makes it land ("an enterprise buyer's real fear is not a wrong explanation, it is a correct explanation wired to the wrong action") still waits until slide 08.

---

# Part 8 — Trust test

| Mechanism | Technically real? | Visible? | Understandable? | Memorable? | Change since previous audit |
|---|:---:|:---:|:---:|:---:|---|
| **Deterministic quantitative truth** | ✅ | ✅✅ | ✅ | ✅✅ | 109.9% now visible in the deck hero *and* on slide 05's split panel |
| **Entitlement-before-ranking** | ✅ but see §11 | ⚠ | ✅ once explained | ❌ | **Unchanged.** Still the biggest visibility gap, and now carries a measured concurrency risk |
| **Evidence freeze** | ✅ | ❌ | ❌ | ❌ | **Unchanged.** Still a hash in the Audit tab and one line on slide 07 |
| **Verification** | ✅ | ⚠ | ✅ | ✅✅ | **Improved.** Slide 06's misleading stat removed; *"verification mechanism tested ≠ live LLM reliability measured"* stated plainly. Still invisible in the product |
| **Causal-language control** | ✅ | ✅✅ | ✅✅ | ✅ | **The largest single improvement in this table.** Previously ❌ visible. Now renders on the S2 default screen and in the review panel. Closes the previous audit's top under-communicated item |
| **Uncertainty** | ✅ | ✅✅ | ✅✅ | ✅ | **Improved.** The `UNCALIBRATED` gloss removes the "broken" misread |
| **Abstention** | ✅ | ✅✅ | ✅✅ | ✅✅ | **Improved in placement**: slide 03 and demo 1:30 rather than slide 07 and demo 2:15 |
| **Human review** | ✅ | ✅✅ | ✅✅ | ✅✅ | **Improved.** Three ranked competing explanations with per-hypothesis support and contradiction counts, the reason review was triggered stated in plain language, four typed actions with descriptions and an optional note. This is the best screen in the product |
| **Bounded automation** | ✅ | ✅ | ✅✅ | ✅ | Unchanged. *"The system can raise this request automatically. It will not perform the technical fix — that stays with the owning team."* |

### Where the trust story now stands

Seven of nine mechanisms are visible and understandable, against five of nine at
the previous audit. The two that remain invisible — **evidence freeze** and
**entitlement-before-ranking** — are the two that are hardest to render and the
two that a technical judge is most likely to be impressed by. Neither needs
building. Both need one sentence in the UI and one line moved forward in the
deck.

---

# Part 9 — Demo reassessment

Against the current `eval/final_demo_script.md`.

| | Moment | Assessment |
|---|---|---|
| **Strongest** | **Beat 5 → 6, the setup and the refusal (1:30–2:30).** *"Every tool in this category will pick one and write you a confident paragraph about it. Watch what this one does instead."* | Better than the cold open the previous audit proposed. A cold open shows the refusal; this one makes the judge *predict* the wrong behaviour first and then watch it not happen. That is a stronger memory formation than showing the answer up front |
| **Weakest** | **Beat 7 (2:30–3:00), three options with no default.** Entitlement, audit trail, or sparse history | The script says pick one and does not say which. Under time pressure a presenter picks the one they are most comfortable with, which is usually the audit trail — the least memorable of the three. **S4's "wait four days" is the most memorable sentence in the product** and is again the optional beat |
| **Most memorable** | **The refusal, and specifically *"they imply different owners — one is a pricing problem, one is a supply problem. Guessing doesn't just risk a wrong answer; it sends the wrong team."*** | The consequence framing is new in this cut and it is what makes abstention land as a business argument rather than a safety feature |
| **Most technically impressive** | **Beat 2's 109.9%** | Unchanged, still the cheapest proof that numbers are computed |
| **Most likely judge confusion** | **The 14-second S2 run in the middle of beat 5** | The script says "talk through it". Fourteen seconds of live silence sits directly before the most important moment in the demo. Pre-running S2 in a second tab removes the risk at zero cost, and the script does not say to |

### Does the demo communicate the trust differentiator before the judge loses interest?

**Yes — in a full three-minute slot.** 1:30 of 3:00 is inside the window, the
preceding beats now carry real evidence rather than a tour, and the setup line
earns the moment.

**No — in a shortened slot, and the script has no answer for that.** There is no
60- or 90-second cut. At a booth, in a corridor, or when a session runs late,
the first thing lost is everything after 1:30 — which is the entire
differentiator. The previous audit's 30-second and 90-second cuts were not
adopted, and their absence is the one remaining structural weakness in an
otherwise well-restructured script.

---

# Part 10 — Business value reassessment

| Question | Answered? | Evidence |
|---|---|---|
| **Who benefits?** | **Yes.** Three personas with different entitlement, decision rights and decision values | `config/personas.yaml`; slide 08; S5a vs S5b |
| **What decision improves?** | **Yes, and specifically.** Whether to alert at all (S7), which of two owners to page (S2), whether to escalate and under whose authority (S1) | Rendered on screen, not asserted |
| **What workflow changes?** | **Yes.** Slide 11's four mechanisms name it: evidence gathering and structured RCA automated in one pass; unsupported explanations blocked before delivery; recommendations constrained to approved levers with named owners; every conclusion carrying evidence, lineage and decision state | Each tied to something built |
| **Why would a company care?** | **Improved but still the weakest.** The governance answer is strong — 15 lineage records per run, every read audited including denials. The operational answer still rests on a mechanism rather than a measurement | Proposal §12 |
| **What should a pilot measure?** | **Yes.** One KPI family, one team, one quarter, measuring time-to-explanation against the current baseline | Slide 11 ask |

### Does avoiding unsupported ROI improve credibility?

**Yes — and after this pass it does so without costing anything.**

Previously the refusal was a net negative in scoring terms: a judge comparing
600 proposals found a blank where every competitor had a number, and the
surrounding prose was *concessive* ("what we can evidence… what we cannot…").
The blank is still there and it is still correct. What changed is that slide 11
now fills the space with four mechanisms and states the refusal as a *policy* —
*"No ROI figure is claimed anywhere in this project"* — in the kicker, at the
point of use.

That inverts the reading. A stated policy of not inventing numbers, on a slide
that nonetheless explains where value comes from, is read as discipline. A blank
with an apology beside it is read as a gap. Same facts, and it is now the
stronger of the two.

**The one thing still missing:** the proposal names three *users* and no
*buyer*. "Who pays" remains unanswered, and it is the first question a business
judge asks. One line — a Head of Analytics or CDO with a BI budget and an
alert-fatigue complaint — would close it without a claim.
---

# Part 11 — Technical credibility

Only material findings. Each was verified in the current source, not taken from
a report.

| Area | Status | Verification |
|---|---|---|
| **Concurrency correctness** | ❌ **Unfixed, and material** | `semantic/gateway.py` still holds `_conn: duckdb.DuckDBPyConnection \| None = None` as a module global; `_lock` is taken only inside `connect()` around creation. `guarded_query` does `con = connect(db_path)` then `con.execute(sql).df()` on the shared handle. `technical_competition_audit.md` §7.1 measured the consequence: a `region='West'`-filtered `ops_lead` principal received a 916-row result set spanning East, North, South and West. The verified fix — a per-thread cursor inside `connect()`/`guarded_query` — was not applied |
| **System-error semantics** | ❌ **Unfixed, and material** | `graph/nodes.py:325` `abstain_insufficient_evidence` returns a constant `terminal_reason`: *"a movement is real but nothing corroborates an explanation; naming the missing source would close the gap"*. It never inspects `state["error"]`, and `graph/routing.py` maps both `"insufficient"` and `"error"` to that node. An infrastructure failure is therefore narrated as a completed-and-empty search |
| **Feedback persistence** | ❌ **Unfixed, and it contradicts a live claim** | `grep -rn "from feedback\|import feedback"` across `graph/`, `ui/` and `app.py` returns **nothing**. `feedback/store.py` is imported by tests only. Meanwhile `eval/judge_defense.md:353` and `R2_BUSINESS_PROPOSAL.md:585` both state the loop is *"implemented and wired"* |
| **Confidence calibration honesty** | ✅ **Strong** | Only HIGH clears the ten-case floor; MEDIUM and LOW report `UNCALIBRATED`; Laplace smoothing to 0.929 for the arithmetic while raw counts display; the review panel explains that no `p_model` means no automation arithmetic. Now glossed in plain language too |
| **Retrieval evaluation** | ✅ **Fixed, thoroughly** | Fusion is no longer claimed to beat dense; RRF 0.697 is stated as sitting between BM25 and dense; hybrid is retained explicitly as a robustness mechanism. The correction went into the generator so it cannot be erased on the next run |
| **Attribution methodology** | ✅ **Strong** | LMDI closes to 0.000000000%; the over-100% share is explained rather than clipped; Adtributor's surprise floor is documented as ADR-019; a contribution-only strawman exists and picks a different driver |
| **Causal gate** | ✅ **Strong, and now visible** | DiD with a parallel-trend check, denied on S2/S3, rendered as *"Association only"* on the default screen and reinforced in the review panel. Gate 2 enforces it per hypothesis |
| **Security chain** | ✅ **in design / ⚠ in deployment** | The six-stage leak chain with a non-vacuity control is real and remains one of the best-engineered parts of the project. Every one of the 32 security tests is single-threaded, which is why the concurrency defect above was never caught by them |

### Remaining technical issues serious enough for a judge to challenge

**Three, and only three.** Everything else that could be raised is either already
disclosed, already correct, or too small to matter.

**1. Concurrency breaks the entitlement guarantee at two users.** This is the
most serious item in either audit. It is reproducible by opening two browser
tabs — a plausible accident during a booth demo, not an adversarial probe. It
converts the project's most defensible pillar into its sharpest attack. Two
aggravating details: the fix is small and already verified by the in-repo
technical audit, and the submission currently describes concurrency as a
*capacity* limit (*"roughly two simultaneous users"*, *"a storage migration"*)
when the measured failure is *correctness*. That framing is not dishonest — it
was written before the finding existed — but it is now inaccurate, and a judge
who reads `eval/technical_competition_audit.md` (which ships in the repository)
will see both statements.

**2. An infrastructure crash is delivered as an analytical conclusion.** Unplug
the network mid-run and the user is told a search was performed and found
nothing. For a submission whose thesis is *"it knows when it should not
answer"*, this is the precise inversion of the central claim. It is a one-node
fix.

**3. "Implemented and wired" is not true of the feedback loop.** The gap is one
word, and it is the one word a judge can disprove with a ten-second grep. Every
other claim in this project survives that test — which is exactly why this one
costs more than its size suggests.

### What is not a problem, and should not be treated as one

- The missing live-LLM evaluation. Correctly labelled everywhere, and excluded from scoring here as instructed.
- Synthetic data. Disclosed, audited, and the audit made the numbers worse.
- ~2 concurrent users as a *capacity* statement. Honest and correctly reasoned.
- No authentication. Disclosed on slide 08 as a credibility asset.
- The bootstrap's runtime cost. `technical_competition_audit.md` §6 shows the real cost is 288 per-cell STL decompositions, not the bootstrap — a useful correction, but a performance question, not a credibility one.

---

# Part 12 — Remaining gaps

Top ten, ordered by **severity × probability of affecting a shortlist decision**.

| # | Weakness | Class | Sev. | Prob. | Evidence | Recommended action |
|---|---|---|:---:|:---:|---|---|
| **1** | **The deck hero is a pre-improvement screenshot.** All three UI improvements from this pass — KPI chart, evidence cards, colour rule — are absent from the only picture of the product a judge sees | **Pitch** | **High** | **High** | `hero_s1_workspace.png` 1400×3118 (24 Aug); top 1400×1560 + bottom 1400×1598 = 3158 (26 Aug), a 40px overlap. Content confirms: no chart, no evidence cards, no colour caption. The 40px overlap also duplicates *"Show 1 smaller driver(s)"* across the panel seam | Re-run `submission/deck/render/_capture_hero.py`, re-split, re-render |
| **2** | **Concurrency breaks entitlement at two users** | **Technical** | **High** | Medium | `semantic/gateway.py` shared `_conn`; §7.1 measured cross-principal leakage; 32 security tests all single-threaded | Apply the per-thread cursor fix already verified in the technical audit |
| **3** | **No demo recording, no hosted URL** | **Product / Pitch** | **High** | **High** | ~2.5 GB install, 130 MB model download, two fixture builds. Unchanged since the previous audit | Record the 90-second cut. Do not attempt hosting |
| **4** | **An infrastructure crash is narrated as an abstention** | **Technical** | **High** | Low–Medium | `graph/nodes.py:325` constant `terminal_reason`; routing maps `error` and `insufficient` to the same node | Read `state["error"]` and emit a distinct terminal reason |
| **5** | **"Implemented and wired" is false of the feedback loop** | **Evidence / Technical** | Medium | Medium | `grep` finds no `feedback` import outside `tests/`; claim live in `judge_defense.md:353` and proposal §585 | Change the word, or wire it. The word is five minutes and safe |
| **6** | **No sub-90-second demo cut** | **Pitch** | Medium | Medium | `eval/final_demo_script.md` has one 3:00 cut. Differentiator at 1:30 | Add a 60s and a 90s cut using existing beats |
| **7** | **Eight pre-baked scenarios; `kpi_id` hardcoded** | **Product** | Medium | Medium | `ui/state.py:132`; scenarios imported from `eval.run_recommendation_eval`. Every layer beneath already takes `kpi_id`, `Window`, `slice_filter` | **Do not build this now.** Prepare the verbal answer: it is a demo-surface decision, and name the three parameters that already flow through |
| **8** | **Slide 03's only cross-reference points to the wrong slide** | **Pitch** | Low | Medium | `grep -oE "Slide [0-9]+"` returns one match, `slide-03.html` → "Slide 05"; abstention is `slide-07.html` | One-character class of fix; bundle with #1's re-render |
| **9** | **Evidence cards titled with the literal word "Evidence"** | **UX** | Low | Medium | `ui/components/evidence.py:221`: `getattr(item,'title','') or 'Evidence'`. CRM notes have no title, so the card head reads "Evidence" inside a section headed EVIDENCE. Visible on S1 and S2 | Fall back to source type and date, or to the first clause of the body |
| **10** | **Residual dead space on slides 05, 06, 09; evidence block duplicated on S2** | **UX / Pitch** | Low | Low | Slide 05's thesis banner ~70% empty and its three bottom cards ~50%; slide 06's gate row ~55%; slide 09's card ~45%. In the app, S2 renders the same three evidence cards twice — once under EVIDENCE, once under WHAT THE EVIDENCE SAYS | Cosmetic. Only if items 1–6 are complete |

### By class

**Product weakness** — #3 (accessibility), #7 (interactivity).
**UX weakness** — #9, #10.
**Pitch weakness** — #1, #3, #6, #8.
**Technical weakness** — #2, #4.
**Evidence / evaluation weakness** — #5.

### The shape of the remaining risk has changed

At the previous audit, nine of the top ten weaknesses were transmission. Now
**four of the top five are split evenly between transmission and correctness** —
because the transmission work landed and because a technical teardown has since
been done. Items #2 and #4 are the first genuinely *technical* findings to reach
the top of either list.

---

# Part 13 — Build vs communicate

### BUILD NOW

| Item | Why it clears the bar this close to submission |
|---|---|
| **#2 — per-thread DuckDB cursor** | ~5 lines, inside `connect()`/`guarded_query`, touching nothing else. The fix is already verified working by the in-repo technical audit, which reported it as *faster* as well as correct. It protects the pillar the whole pitch rests on. **This is the only technical change worth the risk** |
| **#4 — abstention node reads `state["error"]`** | One node, one field. Converts the sharpest available inversion of the central claim into another proof of it |
| **#3 — record the 90-second demo** | Not a feature; a recording. Still the largest deliverable gap |

### CHANGE UX

| Item | Note |
|---|---|
| **#1 — re-capture and re-split the hero** | Highest-leverage single action in this audit. The product already does this; only the picture is stale |
| **#8 — fix the "Slide 05" cross-reference** | Bundle with #1 |
| **#9 — evidence card title fallback** | Small, in a newly high-visibility component |
| **#10 — dead space, duplicated S2 evidence block** | Only after everything above |

### PITCH BETTER

- **#5 — say "implemented, not wired"** if the loop is not wired before submission. Safer than wiring it late, and consistent with a project whose credibility comes from claims being exact.
- **#6 — add a 60s and 90s demo cut.**
- **Entitlement-before-ranking and the evidence freeze** — the two trust mechanisms still invisible (Part 8). One sentence each; no build.
- **Name a buyer** — one line in proposal §3 and slide 11.
- **Reframe concurrency** from a capacity statement to a correctness statement *once #2 is fixed*. Fixing it converts a liability into a story: *"a concurrency probe found cross-session leakage in our shared connection; we found it, fixed it, and the security tests are now threaded."* That is exactly the move that made slide 06 the strongest trust slide in the deck.

### EVALUATE

- **Live LLM run**, whenever a key exists. Excluded from scoring here, but it remains the only thing that closes MPE-10's token/cost/model-call fields and the only way to measure Gate 2 against real model output.
- **A threaded security test.** One test that runs two principals concurrently would have caught #2 and would prevent its return. Worth adding *with* the fix, not instead of it.

### V2

Interactivity (#7 — free KPI/slice selection) · enterprise IAM · real calibration for MEDIUM and LOW · drift detection · the learning half of the feedback loop · the STL cube performance work identified in `technical_competition_audit.md` §6 · durable workflow state · corpus diversity.

### IGNORE

Market-event headline diversity · `is_test_account` · bootstrap resample count (the technical audit showed it is not the bottleneck) · slide 01's dead space · anything requiring a dataset change · anything requiring an architecture change.

**The discipline that matters here:** two code changes, both small, both fixing a
measured defect in something the pitch claims. Everything else on the list is a
picture, a sentence, or a recording.

---

# Part 14 — Winner test

> **If I were a judge selecting the top 10% of 600+ submissions — roughly the
> top 60 — would I shortlist BusinessIntelligence.ai?**

## **YES.**

**Why, precisely.**

**1. The substance is top-decile and now legible.** ~19.6k lines of production
code against ~8.4k of tests, 574 passing on a clean runner, 32 ADRs, an exact
identity decomposition, a verification gate that caught its own team's bug, a
causal licence that gets denied and says so on screen, eleven typed terminal
states each with a designed screen. At the previous audit I had to dig for most
of that. A judge now sees it from slide 03 and from thirty seconds in the app.

**2. It does the one thing nothing else in the category does, and shows it
early.** The refusal is on slide 03, in the demo at 1:30, and rendered three
different ways in the product with three different remedies. A judge does not
have to be told this is different; they watch it happen.

**3. The evidence discipline survives an adversarial read — which is rare, and
this pass proved it.** Three claims were made *smaller* under scrutiny. A
misleading stat was deleted rather than caveated. A UX audit's own assertion was
found false and the *document* was corrected rather than the product bent to fit
it. A retrieval conclusion was corrected in the generator so it could not be
silently reverted. Very few submissions in a 600-team field will hold up under
this; almost none will have run the audit on themselves first.

**4. The remaining defects are real but do not disqualify.** The concurrency bug
is serious and I have weighted it heavily — but it is a shared-connection
defect, not an authorisation defect; the policy layer is correct, the fix is
five lines, and it is already documented in the repository with a verified
remedy. A judge who finds it finds a team that found it first and wrote it down.
That is a different signal from a team that never looked.

**What would move this from YES to BORDERLINE:** a live demo in which two
sessions are open and the entitlement guarantee visibly fails, with the deck
still claiming *"0 restricted items reaching any stage"*. That is the one
scenario where a strength inverts in front of the judge. It is also entirely
preventable before submission.

**What would move it from YES to a winning position:** the hero re-capture and
the recording. Both are hours, not days, and both are about showing what already
exists.

---

# Part 15 — Top 5 final moves

| Rank | Action | Expected impact | Effort | Risk | Class |
|:---:|---|---|---|---|---|
| **1** | **Re-run `_capture_hero.py`, re-split, re-render the deck** — and fix the "Slide 05" cross-reference in the same pass | **Highest.** The deck currently shows a product three improvements out of date. Restores the KPI chart, the evidence cards and the colour rule to the only picture a judge sees, and makes slide 03 answer all five questions it claims to | ~45 min | **None** — re-runs an existing script and an existing render pipeline | **UX** |
| **2** | **Apply the per-thread DuckDB cursor fix** and add one threaded security test | **Highest severity avoided.** Protects the entitlement pillar; removes the only scenario in which a strength inverts during a live demo. Also lets the concurrency story be told as a found-and-fixed defect, which is this project's strongest rhetorical move | ~1 h | **Low** — scoped to `connect()`/`guarded_query`; the fix is already verified working and measured *faster*. Re-run the full suite after | **BUILD** |
| **3** | **Record the 90-second demo** | **High.** Converts the prototype from described to seen, and lets the refusal be placed where a shortened live slot cannot cut it. Unchanged from the previous audit and still unaddressed | 2–3 h | Low. Do not attempt hosting | **BUILD** (recording) |
| **4** | **Make `abstain_insufficient_evidence` read `state["error"]`** | Medium-high. Closes the one failure mode that inverts the central claim, and a judge can trigger it by unplugging the wifi | ~45 min | **Low** — one node, one field, existing terminal taxonomy | **BUILD** |
| **5** | **Correct "implemented and wired" to "implemented, not wired"; add a 60s and 90s demo cut; add the two invisible trust sentences** (entitlement-before-ranking, evidence freeze as a consequence) | Medium. Removes the only claim in the project a grep disproves, protects the differentiator against a shortened slot, and surfaces the last two trust mechanisms that exist but cannot be seen | ~1 h total | **None** | **PITCH** |

**Total: under one working day**, of which roughly ninety minutes is code and
the rest is pictures, sentences and a recording.

**Explicitly not recommended:** free KPI/slice selection, wiring the feedback
loop, the STL cube performance work, any dataset change, any architecture
change. All are legitimate; none is worth destabilising a working submission for.

---

# Part 16 — What to protect

Freeze these. Each is now both real and visible, and each is load-bearing for
something else.

| Aspect | Status | Why it must not change |
|---|---|---|
| **Deterministic / AI boundary** | **Freeze absolutely** | No `tools` key, no `confidence` field, no routing predicate reading model output. Every differentiator in Part 4 is downstream of it. Most likely to be eroded by a well-meant late change — a chat box, an agent, a confidence number |
| **EvidenceBundle freeze** | **Freeze** | Identical hash across interrupt and resume is verified and it is what makes the human-review beat true rather than decorative |
| **Entitlement-before-ranking** | **Freeze the design; fix the connection** | The design is right and the insight is genuinely sophisticated. The *plumbing beneath it* needs move #2. Those are different things and only one should change |
| **Abstention** | **Freeze, including its placement** | Six typed states, three distinct screens, now on slide 03 and at demo 1:30. Do not add a sixth abstention, do not soften the wording, do not move it back |
| **Verification** | **Freeze** | Gate 2, the numeric allowlist over a frozen bundle, failing closed to a verified template — and the story of it blocking the team's own fallback, which is the best credibility artefact in the submission |
| **Bounded automation** | **Freeze** | *"Raise the request"*, the never-automate list, and the sentence beneath the button. Do not extend scope to look more capable |
| **Self-critical evidence discipline** | **Freeze, and protect it hardest** | Three claims weakened in one pass; a stat deleted rather than caveated; a self-audit's own claim found false and the document corrected; a retrieval fix put in the generator so it could not silently revert. **This is the project's actual moat.** It is also the easiest thing to lose under deadline pressure, because every instance of it makes a number look worse |
| **Current UX / product story** | **Freeze the structure; finish the pictures** | The five-question order, the four question-named tabs, the quieter non-event screen, contradicting evidence leading, the inline colour rule, the `UNCALIBRATED` gloss. The remaining work is capturing what exists, not changing it |

**One thing explicitly worth *unfreezing*:** the framing of concurrency as a
capacity limit. Once move #2 lands, that sentence should be rewritten — not to
hide the old state, but because "we probed it, found cross-session leakage,
fixed it, and added a threaded test" is a stronger sentence than "roughly two
simultaneous users", and it is the same move that made slide 06 work.

---

# Part 17 — Final comparison

| Dimension | Previous | Current | Change |
|---|---:|---:|---:|
| Product | 8 | 8 | 0 |
| UX | 7 | 8 | +1 |
| Technical | 9 | 8 | −1 |
| Trust | 10 | 9 | −1 |
| Differentiation | 8 | 9 | +1 |
| Business | 5 | 7 | +2 |
| Demo | 6 | 7 | +1 |
| Judge comprehension | 6 | 8 | +2 |
| **Overall** | **74** | **79** | **+5** |

### Current verdict

**79 / 100 — Strong contender, at the upper edge of that band.** The
transmission gap that defined the previous audit is substantially closed. What
holds it below 80 is no longer *how the product is explained* but three measured
technical defects, one stale screenshot, and one missing recording.

### Previous verdict

**74 / 100 — Strong contender.** The product was a full band better than the
pitch carrying it.

### What changed the score most

**Judge comprehension (+2) and business value (+2)** — but the honest answer is
narrower than that. The single largest contributor is **slide 03**: uncropped,
showing the whole product, with the differentiator beside it. One slide moved
the first-impression test from two unanswered questions to one, and carried
differentiation, comprehension and demo memorability with it.

**Working against that, −2 across technical credibility and responsible AI** —
and this must be read correctly. **The product did not regress.** The code that
produced those findings was identical on the day of the first audit. My
information improved, principally through `eval/technical_competition_audit.md`,
which the team commissioned on itself. A submission that pays to have its own
concurrency broken is doing the right thing; the score reflects that the defects
are real and unfixed, not that the team hid them.

### Biggest remaining threat

**A live demo with two sessions open.** The entitlement guarantee — one of the
four moat pillars, and the one an enterprise judge is most likely to probe — is
measurably breakable at two concurrent users, while the deck states *"0
restricted items reaching any stage"*. It is the only remaining scenario where a
stated strength inverts in front of the audience. It is also a five-line fix that
has already been verified to work.

**Runner-up:** the deck showing a product three improvements out of date, so the
two best UX changes in this pass reach no judge who does not run the app.

### Highest-leverage next action

**Re-capture the hero screenshot and re-render the deck.** Forty-five minutes, no
risk, no code, and it puts the KPI chart, the evidence cards and the colour rule
in front of every judge who will only ever see the PDF. The product already does
all three; only the picture is stale.

### Would you shortlist it?

**Yes.** Top 10% of 600, without hesitation and without hedging.

The system is genuinely top-decile, the pitch now carries it, and the trust story
is not a claim but a set of behaviours a judge can watch. The remaining defects
are real, I have scored them, and none is disqualifying — because every one of
them is documented in this team's own repository, found by an audit they ran on
themselves, with the remedy written down beside it.

That last property is worth more than any of the individual fixes, and it is the
thing I would tell the other judges about.

---

*Second-pass audit performed against the repository state of 2026-08-26,
commit `79abd7d`. The Streamlit app was started and driven live; deck slides
were inspected as rendered images; every disputed claim was verified in source.
No code was modified. Supersedes nothing in `eval/product_judge_audit.md` — that
document's findings are either closed here or restated with current evidence.*
