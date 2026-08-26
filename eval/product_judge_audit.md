# Product / UX / Judge audit — adversarial

**Question this document answers:** would a strong but time-constrained judge
shortlist BusinessIntelligence.ai out of 600+ submissions? If not, why not, and
what changes materially improve the odds?

**Method.** Read in judge order — pitch deck first, rendered slide PNGs
inspected as images, proposal, then eval reports, then code. No code was
modified. Where this audit disagrees with an existing eval document, the
disagreement is stated and the evidence is named.

**Standing.** This is a product-selection audit. Architecture quality matters
here only insofar as a judge can perceive it. A correct system that a judge
cannot see does not score.

---

# Part 1 — Zero-context judge test

Simulated: 60 seconds with `submission/R2_BUSINESSINTELLIGENCE_PITCH.pdf`, no
prior knowledge, no documentation. Slides 01–03 only, because that is what a
skim actually covers.

| Question | Answer after 60s | Verdict |
|---|---|---|
| **1. What problem does this solve?** | Dashboards tell you *what* moved, never *why*. Unambiguous — it is the slide title, the closing band, and the five-step "path a leader lives today". | **Strong.** Best-answered question in the deck. |
| **2. Who is it for?** | Not stated. "BI implementations", "employees", "analysts", "a leader" all appear on slide 01 as statistics about a market, not as a named user. Slide 03 shows `Meera · Analytics Lead` in a screenshot masthead — small type, inside a cropped image. The three personas do not arrive until **slide 08**. | **Weak.** Requires reading further. |
| **3. Why does the problem matter?** | 73% / ~21% / ~70% / 22%, plus `Day 1 → Day 2 → the window has already closed`. The flow row is the strongest single element on slide 01. | **Strong.** |
| **4. What is different about it?** | After 60s the honest answer is: *"a five-stage pipeline and a screenshot"*. Slide 02 argues against naive LLM use well, but that is a **problem-space** argument, not a product difference. The actual differentiator — *it declines* — is **slide 07 of 11**. | **Weak, and this is the single biggest first-impression failure.** |
| **5. Why should I believe it works?** | Slide 03 embeds a real screenshot of the running app. But the embedded image is **cropped to its top ~35%** (finding P0-1), so a judge sees a big number and a hypothesis. Everything the right-hand column promises — evidence, reliability, action — is below the crop line. The "574 tests" proof arrives on slide 04. | **Weak at 60s, strong at 4 minutes.** |
| **6. What would make me remember it?** | Nothing in the first 60s. The three genuinely memorable objects — *"it declines"*, *109.9% self-explaining*, *"the gate blocked our own template"* — sit on slides 05, 06 and 07. | **Weak.** Memorability is back-loaded. |

### First-impression verdict

The deck is built like an evidence dossier: problem, counter-argument,
solution, continuity, then five slides of proof. That structure rewards a judge
who reads all eleven slides carefully. It punishes a judge who reads three.

**Two of the six zero-context answers require reading past slide 03, and one of
them (question 4) is the differentiator itself.** By this project's own
standard — *"if any answer requires reading documentation, that is a pitch
weakness"* — the pitch has a real, fixable structural problem.

**What already works and must not be touched:** the problem framing on slide 01
is better than most consulting decks. The `Day 1 → Day 2 → window closed` flow
does more work in one row than three paragraphs would.

---

# Part 2 — Shortlist scorecard

## Weighting, declared

Weighted for *selection from a large field*, not for engineering merit. In a
600-submission field, the marginal value of a judge understanding you quickly
exceeds the marginal value of being 10% more rigorous than the next team.

| Category | Weight | Rationale for the weight |
|---|---:|---|
| Product differentiation | 12 | The primary selection filter at scale |
| Demo memorability | 10 | What survives to the shortlist meeting |
| Technical credibility | 9 | Track 3 is explicitly a technical brief |
| Responsible / controlled AI | 9 | Named in the brief's own emphasis paragraph |
| User value | 8 | "Intelligence-to-action" is the case's own phrase |
| UX quality | 8 | R2-DEL-2 asks for a working prototype |
| Judge comprehension | 8 | Comprehension gates every other score |
| Business value | 7 | R2-DEL-1 is a business proposal |
| Prototype quality | 7 | Hard deliverable |
| Problem clarity | 6 | Cheap to get right, costly to get wrong |
| Competitive defensibility | 5 | Judges rarely test this directly |
| Problem importance | 4 | Fixed by the track; little differentiation available |
| User pain | 4 | Same |
| Scalability story | 3 | Explicitly de-emphasised by the brief |
| **Total** | **100** | |

## Scores

### 1. Problem importance — 8/10 · weight 4
- **Evidence:** slide 01's four research-sourced stats; the diagnostic gap is a real, named, unfixed category problem.
- **Weakness:** every team on Track 3 has the same problem. Importance is a floor, not a differentiator.
- **Strongest improvement:** none available. Do not spend more slides here.

### 2. Problem clarity — 9/10 · weight 6
- **Evidence:** *"dashboards show what moved, never why"* is stated as a claim, not a label. The five-step path is concrete and time-stamped.
- **Weakness:** three structural reasons + three market quotes + four stats + a five-step flow is four separate arguments for one point.
- **Strongest improvement:** cut "Three reasons the gap persists" to two bullets and give the space to the flow row.

### 3. User pain — 7/10 · weight 4
- **Evidence:** verified G2/Reddit quotes; the `Day 1 / Day 2` stamps make the pain temporal rather than abstract.
- **Weakness:** the pain is described from a market-research altitude. No single named person is shown in pain until slide 08.
- **Strongest improvement:** name a persona in slide 01's flow row — *"Priya's dashboard flags a drop"*. Costs zero space.

### 4. Product differentiation — 8/10 · weight 12
- **Evidence:** abstention is genuinely differentiated (2 of 8 scenarios decline, three distinct reasons, three distinct screens); the causal-language licence is rarer; scope separation (`request` ≠ `rollback`) is rarer again.
- **Weakness:** **the differentiator is invisible for the first six slides.** Slides 01–04 are indistinguishable from a competent generic BI-copilot pitch. Slide 03's cropped hero actively shows the *undifferentiated* half of the product.
- **Strongest improvement:** put one line of abstention on slide 03. Not a slide — a line.

### 5. User value — 6/10 · weight 8
- **Evidence:** every terminal state ends in a named next step; owner, monitoring metric, bounded button. S4's *"about 4 more days"* is real user value delivered by a refusal.
- **Weakness:** value is asserted structurally and never quantified. The refusal to quantify is defensible, but a judge comparing submissions is left with no number to hold.
- **Strongest improvement:** Part 10 — reframe the missing baseline as an instrument already built, not as a hole.

### 6. Technical credibility — 9/10 · weight 9
- **Evidence:** ~19.6k LOC production plus ~8.4k LOC tests; 11 typed terminal states verified directly in `graph/types.py`; 32 ADRs; LMDI closing to exact zero; a six-stage leak chain with a non-vacuity control. This is a real system, not a demo harness.
- **Weakness:** the strongest technical evidence lives in `eval/` files a judge will never open — and one of those files (`eval/final_evaluation_report.md` §3) **contradicts the deck** on retrieval.
- **Strongest improvement:** fix the contradiction (P0-4). One stale table can cost more credibility than 574 tests earn.

### 7. Responsible / controlled AI — 10/10 · weight 9
- **Evidence:** no `tools` key, asserted against the recorded request; `Narrative` has no `confidence` field; no routing predicate reads model output, asserted against predicate *source*; Gate 2 blocked the team's own fallback template. That last item is the best single piece of trust evidence in the project.
- **Weakness:** none on substance. The weakness is entirely visibility — see Part 9.
- **Strongest improvement:** nothing to build. Move it earlier in the narrative.

### 8. UX quality — 7/10 · weight 8
- **Evidence:** the real product screen (`submission/deck/assets/hero_s1_workspace.png`, inspected full size) answers all five user questions in one scroll, with proportional zero-anchored driver bars and the calibration caveat inline. It is genuinely well designed.
- **Weakness:** the deck shows only its top third. Slides 07 and 11 carry 40–60% dead space despite the `.body.fill` fix that `eval/pitch_deck_visual_qa.md` records as resolved — **this audit independently disagrees with those two "Pass" verdicts**. Separately, the driver chart renders the negative bar in **red**, contradicting the colour discipline `eval/growth_design_ux_mapping.md` claims ("red reserved for contradicting evidence and hard verification violations only").
- **Strongest improvement:** P0-1, uncrop the hero.

### 9. Business value — 5/10 · weight 7
- **Evidence:** proposal §12 is the most intellectually honest business section in this submission. Risk value is measured; everything else is labelled `[A]`.
- **Weakness:** *honesty is not scoring*. A judge comparing 600 proposals has nothing to write in the impact column. The one quantified value figure (622,121–799,870 INR) is labelled `[I]` and lives on a cropped screenshot.
- **Strongest improvement:** Part 10's "instrument already built" reframe. Do **not** invent ROI.

### 10. Prototype quality — 8/10 · weight 7
- **Evidence:** 8 scenarios end to end; 574/574 on a clean CI runner; a real LangGraph `interrupt()` with an identical bundle hash across resume; independent browser QA.
- **Weakness:** **a judge cannot run it.** ~2.5 GB of dependencies, a 130 MB model download, two fixture builds, a 13-minute suite. No hosted URL, no recorded video. If the judging format does not guarantee a live demo slot, the prototype scores as a screenshot.
- **Strongest improvement:** P0-3 — record a 90-second screen capture.

### 11. Demo memorability — 6/10 · weight 10
- **Evidence:** `eval/final_demo_script.md` is excellent — disciplined, timed, with explicit "do not do this" rules. Beat 6 (S2 refusal) is a strong moment.
- **Weakness:** the wow arrives at **2:15 of 3:00**. Two-thirds of the demo passes before the differentiator appears. And it is all contingent on a live session that may not happen.
- **Strongest improvement:** Part 8's restructured demos; move the refusal forward.

### 12. Scalability story — 6/10 · weight 3
- **Evidence:** migrations triggered by *conditions* rather than volumes ("before any real data", "at the first data-isolation requirement") is a genuinely sophisticated framing.
- **Weakness:** "~2 concurrent users" is stated plainly on slide 10. Correct — and it will read badly to an enterprise-minded judge who does not read the reasoning beside it.
- **Strongest improvement:** keep the honesty, shift the emphasis from the number to the trigger.

### 13. Competitive defensibility — 7/10 · weight 5
- **Evidence:** the composite is hard to assemble (Part 14). No single component is.
- **Weakness:** slide 11's category table compares against *categories* — correct discipline, but it reads as a self-scored checklist whose last row is all green.
- **Strongest improvement:** lift one row of that table onto slide 03 as a two-column "them / us".

### 14. Judge comprehension — 6/10 · weight 8
- **Evidence:** tabs named for questions, not modules; internal pipeline order hidden; five epistemic classes.
- **Weakness:** dense consulting-poster format. Slide 09 alone carries roughly twenty numbers. A judge on submission 340 of 600 does not parse that. The evidence discipline that makes the project trustworthy is the same thing that makes it slow to read.
- **Strongest improvement:** nothing needs removing from the *product*. Each slide needs one clear thesis line, larger, above its evidence.

## Weighted total

| # | Category | Score | Weight | Weighted |
|---|---|---:|---:|---:|
| 1 | Problem importance | 8 | 4 | 32 |
| 2 | Problem clarity | 9 | 6 | 54 |
| 3 | User pain | 7 | 4 | 28 |
| 4 | Product differentiation | 8 | 12 | 96 |
| 5 | User value | 6 | 8 | 48 |
| 6 | Technical credibility | 9 | 9 | 81 |
| 7 | Responsible / controlled AI | 10 | 9 | 90 |
| 8 | UX quality | 7 | 8 | 56 |
| 9 | Business value | 5 | 7 | 35 |
| 10 | Prototype quality | 8 | 7 | 56 |
| 11 | Demo memorability | 6 | 10 | 60 |
| 12 | Scalability story | 6 | 3 | 18 |
| 13 | Competitive defensibility | 7 | 5 | 35 |
| 14 | Judge comprehension | 6 | 8 | 48 |
| | **Total** | | **100** | **737** |

## Overall: **74 / 100**

**Reading of the score.** Every category scoring 8 or above is a *substance*
category. Every category below 7 is a *transmission* category. The system is
roughly a full band better than its pitch. That is an unusually good problem to
have this close to a deadline, because transmission is cheaper to fix than
substance — but it is still the thing that decides shortlisting.

**If every P0 in Part 15 is executed, the realistic ceiling is ~82.** The
remaining points are gated on things that cannot be fixed before submission:
real-data validation, a measured baseline, and a live LLM evaluation.
---

# Part 3 — The 600-competitor test

No competing submission was inspected and none could be. What follows are
**constructed archetypes**, not observations. Each is a plausible shape a strong
team takes on this brief. Read them as a risk model, not as intelligence.

## Matrix

| # | Archetype | Where they beat us | Where we beat them | Copyable in one weekend | Meaningful engineering to reproduce | Learn from them | Do **not** copy |
|---|---|---|---|---|---|---|---|
| **1** | **Generic BI chatbot** (LLM + SQL + dashboard) | Instant comprehension. A judge understands a chat box in 3 seconds. Feels usable. Answers arbitrary questions; we answer one. | Their numbers come from LLM-authored SQL and cannot be verified. No abstention. No entitlement before retrieval. No causal control. | Our five-stage flow diagram; the persona dropdown; the "material movement" chip | LMDI exact identity; Gate 2 numeric allowlist; the evidence freeze | **Speed to comprehension.** They are understood before we finish slide 01 | The chat box. Slide 03's "no chat box, by design" is correct and should stay |
| **2** | **RAG analytics copilot** (docs + embeddings + LLM) | Citations look like evidence and read instantly. Corpus size sounds impressive. | They answer *why* from documents only — they cannot decompose a KPI, cannot localise a slice, cannot tell a schema rename from growth. Their citations support the sentence, not the number. | Our evidence cards; the cohort panel; the source-type chips | Detection → LMDI → Adtributor → DiD chain; entitlement-before-ranking | Citation UX is more legible than ours. Our default screen shows "8 supporting" — a *count*, not evidence | Treating retrieval as the explanation. Our S1 tickets deliberately name no cause |
| **3** | **Multi-agent analyst** (agents investigating KPIs) | Demo theatre. Watching agents debate is memorable. Reads as "advanced". Judges reward visible autonomy. | Non-determinism; no reproducible bundle hash; no bounded action; agent drift is the exact failure Gartner names on our slide 02 | Nothing of ours; they are on a different axis | The whole deterministic core; the routing predicates that never read model output | Their *legibility of process*. Our pipeline is invisible by design; theirs is the show | Agents. Slide 11's "deliberately not on the roadmap" is right, and is a stronger line than most teams will have |
| **4** | **ML anomaly detector** (stat/ML detection + LLM explanation) | Cleaner metric story. ROC curves, F1, a held-out set. Feels scientific. Their accuracy numbers will look more rigorous than ours. | Detection without attribution, evidence, entitlement, decision rights or abstention. They stop where we start. | Our STL/MAD/PELT stack — genuinely a weekend | Everything downstream of detection | **Evaluation presentation.** They will show a curve; we show a table. A curve reads faster | Optimising the detection number. Our 1.000/1.000 is already a liability, not an asset (Part 12) |
| **5** | **Enterprise BI copilot** (polished dashboard + assistant) | Looks like a product a company would buy. Enterprise-grade visual language. Probably has SSO mocked. | No verification gate; no abstention; entitlement will be cosmetic (a role dropdown filtering a chart, not filtering before ranking) | Our persona selector; the four-tab layout; the audit trail *view* | The six-stage leak chain with a non-vacuity control; scope separation | Visual polish and enterprise cues. Our UI is clean but plain, and reads as a research tool | Faking auth. Our "there is no authentication" card on slide 08 is a credibility asset — most teams will bluff it |
| **6** | **Consulting-style analytics solution** (strong story, moderate depth) | Business narrative, ROI table, market sizing, a clean phased plan. Reads well to a business judge. Will out-score us on the impact column. | Their ROI is invented and a technical judge will find it. We measured what we could and labelled the rest. | Our slide 01 and slide 11 | Everything in `eval/` | **Value articulation.** They will have a number in the impact column; we have a principled blank | Inventing ROI. Proposal §12's refusal is right — but it must be *reframed*, not just held (Part 10) |
| **7** | **UX-first winner** (excellent polish, shallow backend) | Wins the first 60 seconds outright, which is when most shortlisting happens. Screenshots that sell themselves. | Nothing survives a technical question. No verification, no abstention, no lineage. | Our entire UI in a weekend, and better-looking | Nothing they would attempt | **Front-loading.** They put the wow first. We put it seventh | Decoration. `eval/growth_design_ux_mapping.md`'s "deliberately not adopted" list is correct discipline |
| **8** | **Research-heavy technical** (deep algorithms, poor product) | May out-depth us on a single method — proper conformal prediction, a real causal graph, learned calibration. | We have depth *and* a working product with a decision workflow. They have a notebook. | Nothing | Nothing they need | Their willingness to go deeper on one thing. We are broad; a specialist will beat us on any single axis | Adding a ninth algorithm. `eval/complexity_audit.md` is right that nothing should be added |

## The two archetypes that actually threaten us

**#7 (UX-first) and #6 (consulting-style)** are the real risks, not #3 or #8.
Both beat us on the axis where shortlisting is decided: how much a judge
understands and remembers per second spent. We beat both on any axis a judge
has time to test — and in a 600-team field, that time may not exist.

**The correct response is not to become them.** It is to spend the first 60
seconds the way they do while keeping everything behind it.

---

# Part 4 — "Why us?"

### The single most memorable thing

**It declines — and says exactly what would change its mind.**

Not "it abstains" as a bullet. The concrete artefact: S4 renders
*"52 days of history are available. A seasonal baseline needs 56 … about 4 more
days of observations. The system will start explaining this slice on its own
once the baseline exists — no action is needed now."*

That is a refusal that is *more useful* than most products' answers. No
competitor archetype produces it, and it is very hard to fake, because faking it
requires knowing precisely why you cannot answer.

### The second most memorable thing

**109.9%.** A contribution share above 100%, rendered with its own explanation
("other factors moved the opposite way and partly offset it"), backed by an
identity that closes to 0.000000000%.

It is the cheapest possible proof that a number was computed rather than
generated — and it doubles as a proof of the LMDI implementation being exact.
It is one number that carries two claims.

**Runner-up, and arguably the strongest with a technical judge:** *the gate
blocked our own fallback template.* A team that reports their own safety
mechanism catching their own bug is doing something no polished submission does.

### Genuinely difficult to reproduce quickly

Not any single component. The difficult thing is the **chain**, specifically:

> a frozen, hashed evidence bundle → a narrator with no tools and no confidence
> field → ten deterministic checks whose numeric allowlist derives from that
> bundle → a causal-language licence issued by a DiD test that can be *denied* →
> a typed terminal state with a designed screen for each of eleven outcomes →
> entitlement resolved before ranking → the same bundle hash surviving a human
> pause and resume.

Each link is a day or two. The chain, wired, tested (574 tests) and consistent
across a UI, is weeks. A competitor who sees the demo can copy the *idea* in a
weekend; they cannot copy the *property* that every link holds.

### Technically impressive but NOT a meaningful differentiator

| Capability | Real? | Differentiating? | Verdict |
|---|---|---|---|
| **LangGraph** | Yes, and correctly scoped to orchestration | **No.** Expect a large fraction of 600 teams to name it. Saying "we use LangGraph" is signalling parity, not advantage | Mention once, as a *constraint* ("orchestration only, not an agent framework"). Never as a feature |
| **Embeddings** | Yes | **No.** Table stakes in 2026 | Do not pitch |
| **Hybrid retrieval (BM25 + dense + RRF)** | Yes | **No — and weaker than claimed.** On the held-out eval split, RRF recall@10 is **0.697**, *below* pure dense at **0.778**. The claim "dense beats BM25, therefore hybrid earns its place" is a non-sequitur: it justifies *dense*, not *fusion* | Downgrade the claim (P1-7). A technical judge who opens `eval/retrieval_report.md` will find this |
| **Adtributor** | Yes, with a documented correction (ADR-019) | **Marginally.** Its entire user-visible output is one line: *"Most affected slice…"*. The surprise/JS-divergence machinery is invisible | Keep in the system, keep out of the pitch. `eval/complexity_audit.md` already reached this conclusion — follow it |
| **LMDI** | Yes | **Yes**, because it produces 109.9% and the exact-zero closure | Lead with the *number*, not the acronym |
| **DiD** | Yes | **Yes, strongly** — because it can be *denied*, and is, on S3 | **Under-communicated.** Not in the 3-minute demo at all |
| **EvidenceBundle** | Yes | **Yes**, specifically the freeze + hash surviving the human pause | **Under-communicated.** One line on slide 07 |
| **Deterministic verification (Gate 2)** | Yes | **Yes, strongly.** This is the answer to "how do I know the model isn't making it up" | Visible on slide 06; invisible in the product's default screen |
| **Abstention** | Yes | **Yes — the single strongest differentiator** | Arrives at slide 07 and demo beat 6. Both too late |
| **Deferral (cost-sensitive)** | Yes | **Yes, moderately.** "Escalation is a cost rule, not a threshold" is a good line | The arithmetic behind it rests on `p_human`, which is seeded. Pitch the *principle*, not the numbers |
| **Entitlement-aware retrieval** | Yes | **Yes, strongly** — filter-before-rank is a distinction most teams will not have thought of | **Under-communicated.** It is a sub-row on slide 08 |
| **Decision workspace (no chat)** | Yes | **Yes**, as a *position*, not a feature | Good line, well placed on slide 03 |

**The pattern:** everything the team is proudest of building (LangGraph,
hybrid retrieval, Adtributor, bootstrap) is either parity or invisible.
Everything that differentiates (abstention, verification, causal licence,
evidence freeze, filter-before-rank, scope separation) is under-communicated or
arrives late.

---

# Part 5 — The "so what?" test

| Feature | Technical capability | User value | Judge value | Differentiation |
|---|---|---|---|---|
| **STL + MAD + PELT detection** | Seasonal decomposition, robust z-score, changepoint | "This is real, not noise" — but the user never asked | Medium — expected competence | **Low.** Every archetype has detection |
| **Materiality gate (statistical + business)** | Two-leg rule; S7 fires no alert on a +5.9% schema artefact | **High** — fewer false alarms is the pain named on slide 01 | **High** — S7 is a memorable non-event | **Medium-high.** Most teams have a threshold, not two legs |
| **LMDI attribution** | Exact multiplicative identity, residual-free | **High** — "conversion rate, and here is why it exceeds 100%" | **High** — 109.9% is the proof object | **Medium.** Driver trees are common; *exact* ones are not |
| **Adtributor localisation** | Explanatory power + surprise + succinctness | Medium — one line: "most affected slice" | **Low** — invisible | **Low** |
| **Bootstrap robustness (300–400 resamples)** | Top-driver stability | **Low** — never shown on the default screen | Low — one number on slide 05 | **Low.** And it costs 13.5 s of a 53 s run |
| **Hybrid retrieval** | BM25 + dense + RRF | Medium — finds corroborating documents | Low | **Low**, and see Part 4 |
| **EvidenceBundle freeze + hash** | Immutable, hashed, survives interrupt/resume | Medium — "my decision attaches to what I reviewed" | **High** once explained | **High** |
| **Gate 2 verification** | Ten deterministic checks, numeric allowlist | **High** (indirect) — nothing false reaches them | **Very high** | **Very high** |
| **Causal-language licence (DiD)** | Parallel-trend test gates the word "caused" | **High** — "association only" is honest wording they can forward | **Very high** | **Very high** |
| **Abstention (6 typed states)** | Distinct remedies per state | **Very high** — a refusal that tells you what to do next | **Very high** | **Very high** |
| **Cost-sensitive deferral** | Expected-loss comparison | Medium — "why am I being asked?" | High | **Medium-high** |
| **Calibrated bands + UNCALIBRATED** | Laplace-smoothed, 10-case floor | **High** — reliability with its own caveat | **High** | **High** |
| **Entitlement before ranking** | Row/column/source filters pre-retrieval | Medium — "1 item withheld" | **High** once explained | **High** |
| **Scope separation (request ≠ execute)** | `AutomationScope`, never-automate list | **Very high** for a buyer | **Very high** | **Very high** |
| **Persona differentiation** | Different entitlement + decision value; identical analysis | **Low as demonstrated** — a name in the masthead and a withheld count | Medium | **Low as demonstrated** |
| **Lineage (15 records/run)** | Accumulated during the run | Low for a business user; high for governance | Medium | Medium |
| **Telemetry** | Per-node latency, retries, terminal | Low | **Medium — and currently a liability** (MPE-10 is ⚠) | Low |
| **Feedback loop (5 typed outcomes)** | Routed to named artifacts; 2 update live | Low — zero cycles run | **Low, and risky** — OBJ-7 is ⚠ | Low |
| **LangGraph orchestration** | 26 nodes, checkpoints, interrupt | Low (invisible) | Low (parity) | **Low** |

### Where technical effort >> user/judge value — overengineering candidates

1. **Moving-block bootstrap (300–400 resamples).** Costs 13.5 s of a 53 s S1 run — the largest single latency contributor — to produce one line on one slide that no user sees. **Do not remove it** (it is cheap insurance against a wrong top driver), but *do* consider reducing resamples for the demo path, and stop pitching it.
2. **Adtributor's full output.** Already correctly hidden. Keep hidden; do not pitch.
3. **Feedback loop.** Fully built, typed and routed — and it has run zero cycles. The build cost is real; the judge value is currently *negative*, because it converts a ✅ into a ⚠ on the traceability matrix. Pitch it as **wiring**, never as **learning**.
4. **Telemetry infrastructure.** Complete plumbing, and the three fields the brief explicitly names (tokens, model calls, cost) all read 0. Highest effort-to-visible-value ratio in the project — fixable in an hour with an API key (P0-6).
5. **Hybrid retrieval fusion.** RRF is measurably *worse* than pure dense on the eval split. The fusion layer is engineering that currently costs accuracy.

---

# Part 6 — User workflow comparison

## Before

A realistic path for Priya, a regional ops lead, on a Monday morning:

| Step | Tool | Elapsed | What actually happens |
|---|---|---|---|
| 1 | Dashboard | 0 min | Net revenue tile is red. No cause, no confidence, no next step |
| 2 | Dashboard drill-down | 10–30 min | Slice by region, channel, segment by hand. Finds West × Web/Mobile |
| 3 | SQL / warehouse | 30–90 min | Is it volume or conversion or price? Needs a decomposition nobody has written |
| 4 | Support desk | 20–60 min | Search tickets. Hundreds. Monday spike makes counts misleading |
| 5 | CRM | 15–45 min | Any account notes? Are they even allowed to read them? |
| 6 | Deploy log / changelog | 10–30 min | Was anything shipped? Ask engineering on Slack; wait |
| 7 | News / market | 10–20 min | Competitor pricing? Usually inconclusive |
| 8 | Hypothesis | 20–40 min | Write a plausible, unranked narrative |
| 9 | Team discussion | 1 day | Meeting to agree what it means |
| 10 | Decision | Day 2+ | Escalate — by which time the window has largely closed |

**This is `docs/ROUND1_MASTER.md` framing, not a measurement. No baseline was
ever timed.** The "Day 1 / Day 2" stamps on slide 01 are illustrative.

## With BusinessIntelligence.ai

| Step | Where | Elapsed | What happens |
|---|---|---|---|
| 1 | Request (scenario/KPI selection) | 0 s | User picks the KPI and slice |
| 2 | Detect | ~1 s | Coverage → STL → MAD → PELT → materiality. Material or not, with both legs |
| 3 | Attribute | ~13 s | LMDI identity + Adtributor localisation + bootstrap |
| 4 | Retrieve | ~2 s | Entitlement filter → BM25 + dense → RRF → cohort aggregation |
| 5 | Verify (Gate 1) | <1 s | Sufficiency; bundle frozen and hashed |
| 6 | Explain | 1–3 s | Narrative into a typed schema (template mode today) |
| 7 | Verify (Gate 2) | <1 s | Ten checks; retry once; fail closed to template |
| 8 | Recommend | <1 s | Lever, owner, monitoring metric, impact range, decision rights |
| 9 | Route | — | Automate / review / abstain, by expected-loss arithmetic |
| 10 | Deliver | — | One screen; or a stated question for a person; or a stated refusal |

**Measured: 4–50 s** (cold start ~50 s, warm ~4 s). No time-saving claim is made
because step-by-step baseline timings above were never measured.

## What actually changes

**Manual effort that disappears**
- Manual dimensional drill-down (step 2) — Adtributor does it.
- Hand-written decomposition (step 3) — LMDI does it, exactly.
- Ticket triage against a noisy background (step 4) — cohort aggregation with a baseline window handles the Monday spike.
- The "am I allowed to read this" question (step 5) — resolved before retrieval, with a count of what was withheld.
- Deciding *whether to alert at all* (implicit) — the materiality gate does it; S7 is the proof.

**What remains**
- Judgement on ambiguity. S2 hands it back deliberately.
- The actual fix. The system raises a request; engineering rolls back.
- Deciding whether the recommended lever is the right lever.
- Everything upstream: instrumentation, data quality, KPI definitions.

**What becomes faster**
- Everything in steps 2–8, compressed into one run. Whether that is 4 seconds against 3 hours or against 30 minutes is **unmeasured**.

**What becomes safer**
- No fabricated number reaches the reader (Gate 2 numeric allowlist).
- The word "caused" cannot be used without a passed counterfactual.
- A restricted document cannot influence ranking, not merely cannot be shown.
- Ambiguity produces a question, not a confident guess.
- Automation cannot exceed request scope.
- The decision attaches to a hashed bundle that cannot change after review.

**What is merely moved from one screen to another** — the honest column:
- Reading evidence. Tickets still have to be read; they moved from Zendesk to the Evidence tab. The default screen shows a *count* ("8 supporting"), not the evidence.
- Method scrutiny. Moved from the analyst's head to the Method tab. Someone still has to trust it.
- The escalation itself. "Raise the request" still creates a ticket someone must action.
- The team conversation (step 9) is not removed — S2 shows the system explicitly *creating* one, better framed.

**The honest summary:** the system removes roughly steps 2–4 and 8, makes 5–7
safe, and reframes 9. It does not remove the human from the loop, and it does
not claim to.

---

# Part 7 — UX teardown

Assessed against the real rendered product (full-size hero screenshot,
`eval/ui_walkthrough.md` raw output, `eval/antigravity_ui_qa.md`), then
independently challenged against `eval/growth_design_ux_mapping.md`.

## The default workspace

| Question | Answerable on the default screen? | Evidence |
|---|---|---|
| **What changed?** | **Yes, instantly.** `↓ 25.0%` at 3.1rem is the largest element; KPI, slice, window and materiality chip sit with it | Verified in the hero capture |
| **Why?** | **Yes.** ANALYTICAL RESULT block + a zero-anchored driver chart + "most affected slice" | Verified |
| **Evidence?** | **Partially.** The screen says `8 supporting` — a green count. No evidence item is visible without switching tabs | Verified. This is a real gap |
| **How reliable?** | **Yes, and well.** "High reliability / Correct in 12 of 12 similar past cases / *These cases come from a synthetic evaluation set*" — three lines that cannot be separated | Verified |
| **What do I do?** | **Yes.** Lever, owner, authority, monitoring metric, impact range, and a button whose text is the scope | Verified |

**Verdict: 4.5 of 5.** The evidence answer is a number where it should be a
sample. One evidence line rendered inline — *"35 payment tickets clustered in
the window; a gateway deploy on 12 Jul"* — would close it without a tab switch
and without adding a feature (the cohort panel already computes exactly this).

## Fact / evidence / hypothesis / recommendation

**Distinguishable — this is done unusually well.** The screen carries labelled,
visually distinct blocks: `HYPOTHESIS` (grey, an inference), `ANALYTICAL RESULT`
(blue, a computation), `EVIDENCE` (a count with sources behind it),
`RECOMMENDATION` (amber, an action). Five epistemic classes with distinct
colours is a design decision most teams will not have made.

**Independent challenge:** the *ordering* undercuts it. `HYPOTHESIS` appears
**above** `ANALYTICAL RESULT` on the default screen. The weakest epistemic class
is placed before the strongest. A reader who stops after two blocks has read an
inference and not the computation that supports it. Reversing them costs nothing
and strengthens the central claim.

## Uncertainty — does abstention feel trustworthy rather than broken?

**Mostly yes, and this is the product's best UX work.**

- S4 is exemplary: it names what is missing (52 of 56 days), why extrapolating would be wrong, what would change it (4 days), and that no action is needed. That is a refusal with a plan.
- S7 is correctly *quieter* — no chart, no chip, no action block. Showing less when there is less to say is the right instinct and most teams will not have it.
- S2 uses the accent colour, not the contradiction colour, and offers no dismiss control. It reads as an open task.

**Independent challenge — one word:** `Uncalibrated` is engineering vocabulary
sitting in the reliability slot where a business reader expects a verdict.
Rendered as *"Uncalibrated — only 2 comparable case(s) have been recorded"*, a
non-technical reader's most available reading is "something is broken", not "the
system is declining to quote a rate it has not earned". The mechanism is
excellent; the label leaks the implementation. A gloss — *"Not enough track
record to say"* — would preserve every ounce of the honesty and remove the
misread.

## Review — does escalation feel useful rather than like failure?

**Yes.** S2's question is a *real* question with real consequences stated
("implying different owners — one is a pricing problem, one is a supply
problem"), followed by four typed actions. The pause is a genuine LangGraph
interrupt on a durable checkpoint, and the bundle hash is identical on resume.

**Independent challenge:** the fact that makes it credible — the identical hash
— is invisible in the UI. The user is told a decision is needed; they are not
shown that their decision will attach to exactly what they reviewed. One line
under the four buttons would convert a mechanism into a perceived guarantee.

## Persona — meaningfully different, or cosmetically different?

**This is the weakest UX claim in the submission, and the gap is presentational
rather than architectural.**

What is genuinely different: entitlement (Priya is denied `crm_notes`), decision
value (Arjun's 2M INR moves the automate/defer boundary), and region scoping.
The analysis is *identical by design* and asserted as such by
`test_personas_differ_in_entitlement_not_in_analysis` — which is intellectually
the correct decision.

What a judge sees: a different name in the masthead, and one line reading
*"1 item withheld"*.

**The problem is not the design. It is that the difference is only observable by
running two scenarios and comparing.** R2-MPE-3 asks for personas receiving
different narratives or actions; the strongest available demonstration (S5a vs
S5b, same event, different economics) exists in `eval/graph_report.md` and is
never put in front of a judge — not on a slide, not in the demo script's main
path, not side by side in the UI.

## Challenging the Growth.Design mapping directly

`eval/growth_design_ux_mapping.md` is unusually rigorous — it audits application
rather than asserting it, and it records three principles that *failed* on first
render. That is the right method. Three places where this audit disagrees:

1. **Colour discipline is claimed but not held.** The mapping states red is "reserved for contradicting evidence and hard verification violations only". The S1 driver chart renders the negative conversion-rate bar in **red** and the positive sessions bar in **green** — an ordinary financial convention, but a direct contradiction of the stated rule, on the single most-viewed chart in the product. Either the rule or the chart should change; today the document describes a discipline the product does not follow.

2. **"Show the work honestly" is unverified where it matters most.** The mapping marks the progress panel "Yes, qualified", and `eval/ui_walkthrough.md` concedes the ticking was "checked structurally, not observed mid-flight". On a 50-second cold run, the loading panel is what a judge stares at for the longest continuous stretch of the demo. It is the least-verified component with the most exposure.

3. **Progressive disclosure has been applied one level too aggressively on evidence.** The mapping treats "documents, counted, one click away" as a success. Measured against the product's own thesis — *evidence is the differentiator* — putting all of it behind a click means the default screen makes an unevidenced assertion followed by a number. The COVID-dashboard principle the mapping invokes argues the *opposite* here: the qualifier belongs with the claim.

**The mapping's own strongest move should be reused in the pitch:** it names the
three principles that failed on first render and were fixed. That is the same
rhetorical move as "the gate blocked our own template", and it is the most
persuasive thing this project does. Neither appears in the first six slides.
---

# Part 8 — Demo memorability

Assessed against `eval/final_demo_script.md`.

| | Moment | Why |
|---|---|---|
| **Strongest** | **Beat 6 — S2 refuses.** "Two explanations, equally supported, implying different owners. The system doesn't pick." | It is the only beat no competitor archetype can produce, and it is emotionally legible without any technical background |
| **Weakest** | **Beat 3 — Evidence.** Twelve seconds in a tab, described rather than shown | The narration does the work ("no ticket says the gateway caused a revenue decline") while the screen shows a list. The best line in the demo is attached to the least visual moment |
| **Most technical, most forgettable** | Beat 2's method framing if it drifts to LMDI/Adtributor; the Method and Audit tabs generally | The script already forbids opening them unprompted. Correct |
| **Most memorable product behaviour** | **S4's "about 4 more days."** Optional beat 7, may never be shown | A refusal that hands back a plan. Currently the most memorable thing in the product is optional |
| **Should be the wow** | **The refusal — S2, and S4 as its punchline** | It already is the wow. The problem is entirely placement: it arrives at 2:15 of 3:00 |

### The structural problem

The demo is arranged as the *product's* logic — detect, attribute, evidence,
explain, recommend, then refuse. That is a correct narrative arc and a poor
attention curve. A judge's attention is highest in the first 30 seconds, and the
first 30 seconds show a number and a chip: the thing slide 01 spends four
statistics attacking.

**Additional risk the script names but does not solve:** the S2 run in beat 6
costs ~14 seconds of live silence in the middle of the strongest beat. The
script says "talk through it". Pre-running S2 in a second browser tab removes
the risk entirely and costs nothing.

## The 30-second demo

*Use when there is a booth, a corridor, or a judge with no time. Both scenarios
pre-run in two tabs. Zero waiting.*

1. **(0:00–0:08)** Tab 1, S1 already rendered, scrolled to show the action block.
   > "Net revenue fell 25% in West. It found the driver, gathered eight documents, and it wants to escalate to Engineering — and the button says *raise the request*, not *roll back*, because that is the only authority this role has."
2. **(0:08–0:22)** Switch to Tab 2, S2 already rendered on the review block.
   > "Same engine, different event. Here it found two explanations equally supported that imply different owners — a pricing problem or a supply problem. So it stops, states the question, and hands it to a person."
3. **(0:22–0:30)**
   > "A dashboard always answers. An LLM always answers. This declines on two of eight scenarios, and it tells you what would change its mind."

**Why this order:** the differentiator lands at 0:08, not 2:15.

## The 90-second demo

*The default for a judging table. Everything pre-run.*

| Time | Beat | Line |
|---|---|---|
| 0:00–0:15 | **S1 whole screen, one scroll** | "One screen: what moved, why, the evidence, how reliable, what to do. Five questions, in the order a business user asks them." |
| 0:15–0:35 | **109.9%** | "Conversion rate accounts for *more than the whole movement* — because sessions rose and partly offset it. That is an exact identity decomposition; it closes to zero. No language model produces a self-explaining over-100% share. It is the cheapest proof the number was computed." |
| 0:35–0:50 | **Reliability** | "Not a confidence score — a track record, with the caveat that those twelve cases are synthetic *in the same block*. And its medium and low bands say `uncalibrated`, because they have fewer than ten cases." |
| 0:50–1:05 | **The button** | "Owner named, monitoring metric named. And read the button: *raise the request*. Rolling back is a different lever no persona here can approve. An enterprise buyer's real fear isn't a wrong explanation — it's a correct explanation wired to the wrong action." |
| 1:05–1:30 | **S2 refusal** | The beat-6 script, verbatim. Land the "different owners" point and stop talking. |

**Cut relative to the 3-minute script:** the Evidence tab visit, the detection
method, the Adtributor localisation line.

## The 3-minute demo — revised

Keep the existing script's content and discipline. Three changes, no new
functionality:

1. **Add a 15-second cold open before beat 1.** Show S2's review block first, say one sentence — *"I want you to see the thing this system does that nothing else in this category does, before I show you how it works"* — then go to S1 and run the arc. The wow moves from 2:15 to 0:10 and the arc is preserved.
2. **Swap beat 3.** Instead of visiting the Evidence tab, stay on the Workspace and read the cohort line aloud (*"35 payment tickets in the window, none in the eight-week baseline"*). Same point, no tab switch, no dead visual.
3. **Make beat 7 non-optional and make it S4.** The four-days line is the most memorable sentence in the product and it is currently the first thing cut for time. Cut ten seconds from beats 1 and 2 to pay for it.

**Do not add:** anything not already built. Every beat above uses existing
rendered output.

---

# Part 9 — Trust / responsible AI visibility

The question is not whether the trust mechanisms are real — they are, and this
audit verified several directly in source. The question is whether a judge
*sees* them.

| Mechanism | Technically real? | Visible? | Understandable? | Differentiated? | Verdict |
|---|:---:|:---:|:---:|:---:|---|
| **Deterministic quantitative truth** | ✅ verified (`test_the_client_never_offers_tools`, no `confidence` field) | ✅ via 109.9% | ⚠ requires the explanation | ✅✅ | Well pitched (slide 05) |
| **Evidence freeze + hash** | ✅ | ❌ Audit tab only; one line on slide 07 | ❌ "identical bundle hash" is jargon | ✅✅ | **Under-communicated** |
| **Entitlement before retrieval** | ✅ 6-stage chain, non-vacuity control | ⚠ "1 item withheld" | ✅ once explained | ✅✅ | **Under-communicated** |
| **Verification (Gate 2)** | ✅ 0/10 false acceptance; blocked own template | ⚠ slide 06 only; invisible in product | ⚠ "ten deterministic checks" is abstract | ✅✅ | **Under-communicated in the product** |
| **Abstention** | ✅ 6 typed states, distinct screens | ✅✅ | ✅✅ | ✅✅ | **Correctly the crown jewel — but late** |
| **Confidence / reliability** | ✅ Laplace-smoothed, 10-case floor | ✅✅ inline caveat | ✅ except the word `UNCALIBRATED` | ✅ | Strong |
| **Causal-language control (DiD)** | ✅ licence *denied* on S3 | ❌ **S3 appears in no demo path** | ✅✅ "Association only" is plain English | ✅✅ | **The single most under-used asset** |
| **Human review** | ✅ real interrupt + resume | ✅✅ | ✅✅ | ✅ | Strong |
| **Bounded automation** | ✅ scope + never-automate list | ✅ the button text | ✅✅ | ✅✅ | Strong, but arrives at slide 08 |

## The five that deserve more emphasis

1. **The causal licence being denied (S3).** A system that shows the word "caused" degrading to "association only" *on screen* is demonstrating restraint, not describing it. It is plain English, it is visual, it takes eight seconds — and it appears in no demo path, no optional beat, and only as a bullet on slide 06. **Highest-value, lowest-cost visibility fix in the audit.**

2. **The evidence freeze surviving the human pause.** Reframe from hash language to consequence: *"When you come back tomorrow, you are deciding on exactly what you reviewed — not on a re-run."* That is an enterprise-legible guarantee. Today it is a hash.

3. **Entitlement resolved before ranking.** The insight — a restricted document that reaches the ranker has already influenced what you see, even if it is stripped afterwards — is genuinely sophisticated and most teams will not have had it. It sits as a footnote on slide 08.

4. **Gate 2 blocking the team's own template.** The strongest credibility artefact in the submission. It is a danger-tinted card on slide 06. It deserves to be said out loud in the pitch, in the first two minutes, in one sentence: *"our own safety gate caught our own bug, and we wrote it down."*

5. **Scope separation — "raise the request", not "roll back".** Already on the button. Move the *sentence* forward: it belongs in the 90-second demo, not on slide 08.

**A note on what not to do:** none of these needs building. All five exist. All
five are communication changes.

---

# Part 10 — Business value audit

### 1. Who pays for this?

Unanswered in the submission. The proposal names three *users* and no *buyer*.
Realistically: a Head of Analytics or a CDO with a BI budget and an alert-fatigue
complaint — or a Finance/Ops function that has been burned by a wrong
attribution. The deck never says.

**This is a real gap.** "Who pays" is the first question a business judge asks
and the proposal's §3 answers "who reads".

### 2. What workflow changes?

Answered well, and honestly, in Part 6 above and proposal §12. Steps 2–4 and 8
of the manual path are displaced; 5–7 become safe; 9 is reframed rather than
removed.

### 3. What decision becomes better / faster / safer?

- **Better:** whether to alert at all (S7), and which of two owners to page (S2).
- **Faster:** unmeasured, and correctly not claimed.
- **Safer:** measurably — no fabricated number, no unlicensed causal claim, no restricted evidence influencing ranking, no automation beyond request scope. This is the one leg with evidence behind it.

### 4. Why would the user keep using it?

Weakly answered. The proposal argues from mechanism, not from habit. The honest
retention argument is the materiality gate: a tool that stays quiet on S7 earns
the right to be believed on S1. That argument exists in the deck (habituation)
but is framed as a UX principle rather than as a retention thesis.

### 5. Why would a company integrate it?

Best-answered by the governance line — every read audited including denials,
correlated per run, with entitlement enforced before ranking. For a regulated
buyer that is a procurement checkbox. The proposal states it and then correctly
declines to claim it satisfies any specific regime.

### 6. Smallest credible pilot

The proposal's own ask is right: **one KPI family, one team, one quarter.**
It should be tightened by one degree — *one KPI family that already has an
alerting channel and a named owner*, because that is where a baseline exists to
be measured against.

### 7. What should the pilot measure?

| Metric | Class today | Why |
|---|---|---|
| Time-to-explanation vs current baseline | **The headline.** Currently unmeasurable — no baseline | The only number that converts the argument |
| False-alarm rate before vs after the materiality gate | Measurable in a pilot | Directly attacks the ~70% figure on slide 01 |
| Abstention rate and analyst agreement with each abstention | Measurable | Tests whether declining is *useful* or merely *safe* |
| First-pass Gate 2 verification rate on live model output | **Currently unmeasured — and measurable today** with an API key | See P0-6 |
| Calibration of MEDIUM and LOW bands | Needs ≥10 real cases | Converts `UNCALIBRATED` into a rate |

### Measured vs assumed vs illustrative

| Class | Content |
|---|---|
| **Measured** | Runtime 4–50 s · 574 tests · 8/8 scenario agreement · 0 restricted items across 6 stages · 15 lineage records · LMDI closure · S3 licence denied · Gate 2 caught the team's own template |
| **Synthetic evaluation** | Detection 1.000/1.000 and 0 FP/48 · retrieval scores · Gate 2 0/10 false acceptance · calibration 12/12 |
| **Assumed** | `p_human` · decision values (500k/750k/2M) · `recovery_fraction` · confidence weights · ~2 concurrent users · that analyst time is displaced at all |
| **Illustrative** | The 622,121–799,870 INR recovery range · the 74,679 INR expected-risk difference |

The classification is applied rigorously and this audit found no misclassified
claim. That is rare and should be said plainly.

### The weakest business-value argument

**"Operational value — less manual investigation."** It asserts the value
proposition of the entire product and then concedes both halves: the time
displaced is unknown and the baseline was never measured. It reads as the
product's central promise immediately withdrawn. A business judge stops there.

### The smallest change that strengthens it without an unsupported claim

**Reframe the missing baseline from a hole into a designed experiment with the
instrument already built.**

Concretely, three sentences and no new claim:

> The system measures its own time-to-explanation on every run — 4 to 50
> seconds, captured per node in the audit trail. What we have not measured is
> the number it should be compared against, because that number lives inside a
> company we do not have access to. The pilot is not an ROI study; it is one
> subtraction, and we have already built the half of it we can build.

This changes nothing factual. It converts "we cannot claim value" into "we built
the measuring instrument and are asking for the other operand" — which is a
*confident* honest position rather than an apologetic one. The current wording
concedes; this version proposes.

**Second-order improvement (optional, PITCH BETTER):** name the buyer. One line
in proposal §3 and one on slide 11.

---

# Part 11 — Synthetic data / realism

`eval/data_realism_audit.md` is the strongest self-audit in the repository, and
it did the hard thing: it found a real problem (13 distinct texts across 895
documents), fixed it, and reported numbers that got *worse*.

### Would a judge think "this was scripted to make the algorithm look good"?

**Mostly no — with one exception that is being pitched rather than buried.**

| Dimension | Assessment | Risk |
|---|---|---|
| **KPI movement realism** | Magnitudes plausible (hundreds of thousands INR daily); day-of-week seasonality present and found by STL; 3.5% null region; T+3 finance watermark | **Low** |
| **Unstructured evidence realism** | 94.6% background noise; 3 source types; register variation; rare exact tokens (`PG-504`, `ERR_TXN_TIMEOUT`) | **Low-medium** — 3.4% lexical diversity is still far from a real queue, and the audit says so |
| **Contradictory evidence** | S2 carries genuinely contradicting market events implying different owners; S3 has 1 supporting vs 1 contradicting | **Low** — this is done well |
| **Distractors** | 12 decoy tickets + 1 decoy market event, mis-timed or mis-sliced | **Low** |
| **Duplicate patterns** | Near-identical tickets cluster in the window; UI collapses with `(+N near-identical)` | **Low** — realistic, and handled |
| **Event timing** | Tickets spread across hours, not stacked; deploy changelog aligned to the changepoint | **Low** |
| **Source heterogeneity** | Daily / hourly / weekly-T+3, load-bearing rather than cosmetic | **Very low — a strength** |
| **Planted-cause obviousness** | **Genuinely good.** No document names a cause. E1 tickets are customer-voice symptoms ("card declined", "spinner never stopped"). Reaching "product or platform failure in Web/Mobile × West" requires detect → decompose → localise → retrieve cohort → correlate deploy → pass DiD | **Very low — the strongest part of the data design** |
| **Label leakage** | `planted_for` / `is_decoy` verified never read by `retrieval/` or `evidence/` | **Very low** |
| **Detection difficulty** | ⚠ **The exception.** Injected events were constructed with magnitudes that clear the materiality rule | **High as presented** |

### Does the synthetic setup still demonstrate a non-trivial business investigation?

**Yes.** The E1 chain is a genuine multi-step inference, and the S7 schema rename
(a `marketplace` → `Marketplace` change that severs the series into 164 + 65 days
and reads as +5.9% growth) is a better-designed adversarial case than most teams
will construct at all. S2's two-owner ambiguity is likewise a real analytical
dilemma, not a shrug.

### What should change — and what should not

**Should change (presentation, not data):**

The detection **1.000 / 1.000** figure is a liability being displayed as an
asset. `eval/detection_report.md`, the deck and the proposal all carry the
correct caveat — and carrying a caveat next to a perfect score invites exactly
the cross-examination the caveat is defending against. The genuinely impressive
number is **0 false positives across 48 clean slices**, which is *not*
guaranteed by construction and is the harder half.

**Recommendation:** on slide 09, promote "0 false positives on 48 clean slices"
to the primary figure and demote 1.000/1.000 to the line beneath it. Same facts,
same honesty, and the number a judge attacks is no longer the number in large
type. This is a **PITCH BETTER**, not a data change.

**Should not change:**

- Do **not** weaken the injected events for cosmetic realism. `eval/data_realism_audit.md` limitation 2 is right: it would destabilise a validated benchmark to buy an appearance.
- Do **not** regenerate the corpus again. Ground truth is byte-identical, all 8 terminals unchanged, and the last regeneration already moved the RNG stream once.
- Do **not** touch `data/ground_truth.json` or `data/scenario_manifest.json`.

**Minor, optional (P2):** market-event headlines remain 5 distinct across 112
rows — the least-improved of the three sources, selected by a deterministic
`idx % len` cycle. Low impact (market events are the smallest source and mostly
act as contradicting evidence), and not worth a regeneration this close to
submission.

---

# Part 12 — Claim / credibility audit

The claim discipline in this project is, on the whole, exceptional. `[M]/[S]/[R]/
[A]/[I]` classification is applied consistently, and this audit found **no
misclassified claim**. What follows are the claims that could still cost
credibility — ordered by how likely a sharp judge is to find them.

| # | Claim | Where | Supported? | Scope clear? | Synthetic labelled? | Would a technical judge challenge it? |
|---|---|---|---|---|---|---|
| **1** | **"0% verification failure rate across the demonstration set"** | Slide 06 stat card; `eval/final_telemetry_report.md` | Arithmetically yes | **No** | Partially | **Yes — and this is the sharpest available attack.** `eval/final_telemetry_report.md` records *"Template fallback rate: 100% of narrated runs (4/4)"*. Every narration in the demonstration set was the **deterministic template**. So Gate 2 has never gated live model output in a real run: 0% verification failure is the template passing checks written for the template. The fact that closes the loop (no API key) is on **slide 10**, four slides later. A judge who connects slide 06 to slide 10 concludes the deck's most safety-critical stat is measuring the system against itself. **Fix: one clause on the card — "all narrations were the deterministic template; no live model output has been gated."** |
| **2** | **"Dense beats BM25 → the hybrid retriever earns its place"** | Slide 09; `R2_BUSINESS_PROPOSAL_SOURCE.md` §3; `eval/data_realism_audit.md`; `judge_defense.md` B4 | The premise is true; the conclusion does not follow | No | Yes | **Yes.** Dense beating BM25 justifies **dense**, not **fusion**. On the held-out eval split RRF recall@10 is **0.697**, *below* pure dense **0.778**; RRF p@5 (0.552) merely ties BM25. RRF wins only on MRR, 0.838 vs 0.833 — a 0.005 margin over 14 queries. **Fix: claim "dense earns its place" and keep hybrid on the stated *capability* argument (BM25 catches `PG-504`, dense catches paraphrase), which is sound.** |
| **3** | **Stale retrieval table contradicting the deck** | `eval/final_evaluation_report.md` §3 | — | — | — | **Yes, if opened.** That file still reports the pre-audit numbers (BM25 p@5 0.810, recall@10 0.957, RRF MRR 0.964) **and the opposite conclusion**: *"hybrid retrieval did **not** beat BM25 on this corpus"*. The deck says the reverse. Two files in the same repository, both dated in the final push, stating contradictory findings. Also reports corpus size **1,341** where `eval/retrieval_report.md` says **1,336**. **Fix: regenerate or delete §3.** |
| **4** | **"50% automated / 25% review / 25% declined"** | Slide 07, three large stat cards | Yes | **No — the caveat is missing from the render** | No | **Yes.** `R2_PITCH_DECK.md` Slide 07 Row 1 specifies the caveat *"These describe the demonstration set, which was built to exercise every terminal. A production mix would be dominated by 'no material event.'"* — and `grep` finds no such text in `submission/deck/slides/slide-07.html`. It is the deck's largest unqualified rate, on the slide arguing that unqualified rates are the problem. Slide 06 carries an equivalent caveat; slide 07 does not. **Fix: add the line. It was already written.** |
| **5** | **Detection precision / recall 1.000 / 1.000** | Slide 09; `eval/detection_report.md` | Yes, with a caveat | Yes | Yes | **Yes, predictably** — "your events were built to be found". The caveat is correct and present. The problem is placement (Part 11). **Fix: demote below "0 FP on 48 clean slices".** |
| **6** | **"7 supporting" vs "8 supporting"** | Proposal §4 vs deck slide 03 | Both real | Documented at length in `R2_PITCH_DECK_SOURCE.md` | — | **Possibly.** A judge reading both documents sees two numbers for one screen. The source file's explanation is honest and thorough, but a judge will not read it. **Fix: make the proposal say 8.** Low effort, removes the question. |
| **7** | **571 vs 574 tests** | `round2_traceability.md`, `test_strategy.md`, `final_telemetry_report.md`, `final_evaluation_report.md` say 571; deck/proposal/checklist say 574 | Both real at different times | Explained only in `BRIGHTDECK_PROMPT.md` | — | **Possibly**, and it is the kind of small inconsistency that a judge scoring "rigour" notices. **Fix: normalise to 574 in the eval files, or add a one-line note.** |
| **8** | **"Correct in 12 of 12 similar past cases"** | Product UI, slide 03 | Yes | Yes — caveat inline | Yes | **Unlikely to be challenged**, and the handling is genuinely good (Laplace smoothing to 0.929 for the arithmetic, raw counts for display, `UNCALIBRATED` below 10 cases). Keep exactly as is |
| **9** | **"Expected recovery 622,121 – 799,870 INR"** | Product UI, slide 03 hero | Labelled `[I]` with basis inline | Yes | n/a | **Low risk in context, medium out of context.** It is the largest business number the product renders and it appears on a screenshot. If a judge quotes it back as an impact claim, the answer is on the same screen — acceptable |
| **10** | **"574 automated tests passing"** | Everywhere | Yes, on a clean CI runner | Yes | n/a | **No** — but note a judge cannot practically verify it (13-minute suite, 2.5 GB deps). It is a trust claim, not a checkable one |
| **11** | **"Enterprise-ready" / "production-ready" / "real-time" / "autonomous"** | Searched: **absent** | n/a | n/a | n/a | **No.** The absence is verified and is itself a credibility asset. `PRODUCTION_EVOLUTION.md` argues the opposite. Keep |
| **12** | **R2-MPE-10 (tokens, model calls, cost) reads 0** | Traceability ⚠ | Honest | Yes | Yes | **Yes — but as a completeness question, not a credibility one.** MPE-10 is a *hard acceptance criterion* the brief says must be demonstrable. Three of its four fields are unmeasured. See P0-6 |

### Summary

Nothing here is dishonest. Items **1, 2, 3 and 4** are the ones that could
actually cost credibility, and all four are unusual in the same way: **they are
places where the project's own standard was not applied to the project's own
pitch.** A submission whose central thesis is "we label what we know" is judged
against that standard, and these four are where a judge gets to say "you did not
do it here". They are also all fixable in under an hour, none requires code, and
none changes a single measured value.
---

# Part 13 — Judge rejection test

Fifteen reasons a judge might pass, ordered by **probability × severity**.
Probability is a judgement, not a measurement.

| # | Rejection reason | Prob. | Sev. | Evidence it could happen | Mitigation |
|---|---|:---:|:---:|---|---|
| **1** | **"I read three slides and could not tell what makes this different."** | **High** | **High** | Part 1: question 4 is unanswerable before slide 07. Slides 01–04 read as a competent generic BI-copilot pitch | Put one abstention line on slide 03. Move the "them / us" row from slide 11 to slide 03. **Cheapest high-impact fix in the audit** |
| **2** | **"The prototype is a screenshot to me."** | **High** | **High** | No hosted URL, no video, 2.5 GB install, 130 MB model download, two fixture builds. If the format has no live demo slot, nothing runs | Record a 90-second screen capture of S1 → S2 and attach it. `submission/deck/render/_capture_hero.py` already proves the Playwright path works |
| **3** | **"Too technical. I could not follow it."** | **High** | Medium | Slide 09 carries ~20 numbers; the deck is 11 dense consulting posters; the speaker notes run 6:45 | One large thesis line per slide, above the evidence. Use the deck's own cut order (10 → 04 → 08) without hesitation if the format caps slides |
| **4** | **"Weak business story — no impact number at all."** | **High** | Medium | Proposal §12 concedes both halves of its own central value claim | Part 10's reframe: the instrument is built, the pilot supplies the other operand. Name the buyer |
| **5** | **"Their safety stat measures the system against itself."** | Medium | **High** | Part 12 item 1: 0% verification failure across runs that were 100% deterministic template | One clause on the slide-06 card. Volunteering it converts an attack into a credibility beat |
| **6** | **"Synthetic data, and detection is perfect — of course it is."** | **High** | Medium | 1.000/1.000 in large type on slide 09 | Lead with 0 FP / 48 clean slices. Lead the *answer* with the realism audit that made numbers worse |
| **7** | **"A hard acceptance criterion is unmet."** | Medium | **High** | R2-MPE-10 ⚠: model calls, tokens, cost all 0. The brief says every MPE "must be demonstrable" | Run `eval/run_llm_eval.py` with a key. The harness exists. This is the only P0 requiring more than editing |
| **8** | **"Their own documents contradict each other."** | Medium | **High** | `eval/final_evaluation_report.md` §3 vs the deck on retrieval; 1,341 vs 1,336; 571 vs 574 | Regenerate or delete the stale section; normalise counts |
| **9** | **"Looks like an AI wrapper."** | **Low** | High | Genuinely not true — LLM writes prose only, and this is provable in three ways | Already well handled (slide 05). No action beyond keeping it early |
| **10** | **"Personas are cosmetic."** | Medium | Medium | Part 7: the visible difference is a masthead name and "1 item withheld". S5a vs S5b never shown to a judge | Add an S5a/S5b side-by-side row to slide 08, or one demo beat. The data already exists in `eval/graph_report.md` |
| **11** | **"The AI is not actually necessary here."** | Medium | Medium | It is a *fair* observation — the system is deliberately built so that removing the LLM changes only sentence construction. CI runs in exactly that mode | **Do not defend against this — claim it.** "The model is optional by design" is a stronger position than "the model is essential". It is already the honest architecture; make it a line, not a concession |
| **12** | **"Recommendations are not actionable enough."** | Low | Medium | The action is "raise a request" — a ticket, not a fix | Correct and deliberate. The scope-separation argument answers it, and is stronger than any expansion of scope would be |
| **13** | **"Trust mechanisms are invisible."** | Medium | Medium | Part 9: 4 of 9 mechanisms score ❌ or ⚠ on visibility | The five emphasis moves in Part 9. All communication, no build |
| **14** | **"Scalability story is weak — two concurrent users."** | Low | Medium | Stated plainly on slide 10 | The condition-triggered migration framing already answers it. Emphasise the trigger, not the number |
| **15** | **"Does not feel enterprise-relevant."** | Low | Medium | No auth; Streamlit; local single process | Slide 08's "there is no authentication" card is a credibility asset. Entitlement, audit and decision rights are genuinely enterprise-shaped. Keep both |

### The pattern in the top five

Four of the five highest-risk rejections are **transmission failures on
substance that already exists**. Only #7 requires anything to be run, and the
harness for it is already written. That is the central finding of this audit.

---

# Part 14 — Competitive moat

### Easy to copy (a weekend)

- The five-stage flow and its five user-facing questions
- The four-tab layout and the "no chat box" positioning
- STL + MAD + PELT detection
- BM25 + dense + RRF retrieval
- The persona dropdown
- The materiality chip and the quieter non-event screen
- The evidence cards and cohort panel
- LangGraph orchestration (many teams will have it already)

### Moderate (one to two weeks, with the idea handed to them)

- LMDI implemented to exact closure (the idea is easy; making the identity actually close to 0.000000000% took a population-mismatch fix, ADR-018)
- Six typed abstention states each with a distinct remedy screen
- Banded calibration with a ten-case floor and Laplace smoothing
- Cost-sensitive deferral arithmetic
- Adtributor with the degenerate-qualification floor (ADR-019)
- A real interrupt/resume with checkpoint durability

### Hard (weeks, and easy to get subtly wrong)

- **Gate 2**: ten deterministic checks whose numeric allowlist is *derived from* a frozen bundle, with dates stripped so a date cannot masquerade as a figure, failing closed to a template that is itself verified
- **The causal-language licence**: DiD + parallel-trend + specificity floor + temporal precedence, producing a boolean that Gate 2 enforces per hypothesis — and that can be **denied**
- **Entitlement resolved before ranking**, verified through six stages with a non-vacuity control
- **The evidence freeze surviving a human pause** with an identical hash on resume
- **Eleven typed terminal states, each with a designed screen** — including the states where the product says less

### System-level advantage (very hard to assemble quickly)

The thing that is actually defensible is not any row above. It is a **property
that holds across all of them simultaneously**:

> Every number the user sees is traceable to a computation over a frozen,
> entitlement-filtered evidence set; the model can neither reach the data nor
> choose the route nor write a figure nor grant itself the word "caused"; and
> when any link in that chain cannot be satisfied, the system has a designed,
> typed, user-facing way of saying so instead of a fallback that guesses.

A competitor can copy any one link after seeing the demo. Reproducing the
*property* requires them to have designed for it from the start — which is
precisely what `CLAUDE.md`'s nine architectural rules and the 32 ADRs record
them doing. It is not reproducible in the time remaining in this competition,
and that is the definition of a moat in this context.

### The strongest defensible combination

**Abstention + verification + evidence freeze + decision rights.**

Any three of those four are impressive. All four together mean the system can be
*wrong* without being *dangerous* — it cannot fabricate the number, cannot
overstate the cause, cannot exceed its authority, and stops rather than guessing.
That is the sentence to build the pitch around, and it is not "we use LangGraph".

---

# Part 15 — Prioritised improvement backlog

Every item states: current problem · why it matters to judges · user benefit ·
competitive benefit · effort · risk · files · build/change/communicate.

## P0 — Must fix before submission

### P0-1 · Slide 03's hero screenshot is cropped to its top third

- **Current problem.** `.shot-frame img { object-fit: cover; object-position: top center }` in `submission/deck/slides/slide-03.html` crops `assets/hero_s1_workspace.png` (1400×3118) to the frame's aspect ratio. The full capture contains the driver chart, 109.9%, "8 supporting", the reliability block, the recommendation and the "Raise the request" button. **The render shows none of them.** The image's own `alt` text promises "conversion rate the largest contributor at 109.9%" — invisible. The right-hand column asserts five answers; the image supports one.
- **Why it matters to judges.** This is the Solution slide. A judge sees a big number and a hypothesis — i.e. the dashboard that slide 01 spends four statistics attacking. The single best asset in the submission is amputated on the one slide where it is shown.
- **User benefit.** None (deck only).
- **Competitive benefit.** Large. Archetype #7 (UX-first) wins on exactly this axis. The full screenshot is *better* than what most teams will show.
- **Effort.** ~30 minutes. Options: (a) two stacked frames showing top and bottom halves; (b) `object-fit: contain` with a taller frame; (c) a full-height narrow column with the bullets moved beneath the flow row.
- **Risk.** None to the system. Deck re-render only.
- **Files.** `submission/deck/slides/slide-03.html`, then `python -m submission.deck.render`, then rebuild the PDF.
- **Verdict.** **CHANGE UX ONLY.**

### P0-2 · Slide 07's outcome split is rendered without its required caveat

- **Current problem.** `50% / 25% / 25%` render as three large stat cards. `R2_PITCH_DECK.md` Slide 07 Row 1 specifies the caveat *"These describe the demonstration set, which was built to exercise every terminal. A production mix would be dominated by 'no material event.'"* — and it is absent from `submission/deck/slides/slide-07.html` (verified by grep). Slide 06 carries its equivalent caveat; slide 07 does not.
- **Why it matters.** It is the deck's largest unqualified rate, on the slide whose thesis is that unqualified rates are the problem. It is the one place a judge can say "you did not apply your own standard here" — and the text was already written.
- **User benefit.** None (deck only).
- **Competitive benefit.** Protects the project's single strongest positioning.
- **Effort.** 10 minutes.
- **Risk.** None.
- **Files.** `submission/deck/slides/slide-07.html`.
- **Verdict.** **CHANGE UX ONLY.**

### P0-3 · No demo video and no judge-runnable artefact

- **Current problem.** The prototype requires cloning, ~2.5 GB of dependencies, a 130 MB model download and two fixture builds. There is no hosted URL and no recording. If the format has no guaranteed live demo, R2-DEL-2 is evaluated from screenshots.
- **Why it matters.** Highest-probability, highest-severity rejection reason after #1. A judge cannot score a prototype they never see run.
- **User benefit.** None directly.
- **Competitive benefit.** Very large. It also fixes the demo-memorability score, because a recording can be *ordered* (refusal first) in a way a live demo under time pressure cannot.
- **Effort.** 2–3 hours: pre-run S1 and S2, screen-record the 90-second script from Part 8, no narration edit required.
- **Risk.** Low. Do not attempt hosting — the model download and DuckDB single-writer make a public deployment a genuine risk this close to a deadline.
- **Files.** New asset only. Reference from `README.md` and the deck's video slide.
- **Verdict.** **BUILD NOW** (a recording, not a feature).

### P0-4 · `eval/final_evaluation_report.md` §3 contradicts the deck

- **Current problem.** That section still reports pre-realism-audit retrieval numbers (BM25 p@5 0.810, recall@10 0.957, RRF MRR 0.964) **and the opposite conclusion** — *"hybrid retrieval did not beat BM25 on this corpus"* — while the deck and proposal claim the reverse. It also states corpus size 1,341 against `eval/retrieval_report.md`'s 1,336.
- **Why it matters.** A file named *final evaluation report* contradicting the pitch is worse than either number being wrong. It undermines the evidence discipline that is this project's main credibility asset.
- **User benefit.** None.
- **Competitive benefit.** Removes the sharpest available "your own documents disagree" attack.
- **Effort.** 20 minutes — regenerate §3 from `eval/retrieval_report.md` or replace it with a pointer to that file.
- **Risk.** None.
- **Files.** `eval/final_evaluation_report.md` §3 and §11 (test count).
- **Verdict.** **CHANGE UX ONLY** (documentation correction).

### P0-5 · The differentiator does not appear until slide 07

- **Current problem.** Part 1, question 4. Slides 01–04 are archetype-generic. "It declines" is the whole thesis and it arrives at slide 07 of 11 and demo beat 6 of 7.
- **Why it matters.** Highest-probability rejection reason in Part 13.
- **User benefit.** None directly.
- **Competitive benefit.** The largest single move available. It is the difference between being remembered as "another BI copilot" and "the one that refuses".
- **Effort.** ~1 hour: one line on slide 03 (a fourth row or an extension of the "no chat box" band), and the 15-second cold open in Part 8's revised 3-minute demo.
- **Risk.** None to the system. The deck's own cut-order guidance already protects slide 07.
- **Files.** `submission/deck/slides/slide-03.html`, `eval/final_demo_script.md`.
- **Verdict.** **PITCH BETTER.**

### P0-6 · R2-MPE-10 is a hard acceptance criterion and three of its four fields read 0

- **Current problem.** Model calls, tokens and cost are all 0 because no `ANTHROPIC_API_KEY` exists. The brief states the MPEs are hard acceptance criteria that "must be demonstrable". `eval/run_llm_eval.py` is implemented, has a `--plan` cost estimator, and has never been run.
- **Why it matters.** It is the only place the submission fails a stated hard criterion. A judge working the acceptance list finds it immediately. It also converts the *second* sharpest credibility issue (P1-1, 0% verification failure on template-only runs) into a measured result.
- **User benefit.** Real: model-generated narratives are the product's intended mode.
- **Competitive benefit.** Very large. It closes MPE-10, partially closes OBJ-8, and converts "LIVE LLM EVALUATION PENDING" — which appears in five documents — into evidence.
- **Effort.** Low in wall time (`--plan` first, then a run), and the cost is trivial at this scale.
- **Risk.** **Named honestly: this is the one P0 that can return bad news.** A poor first-pass Gate 2 rate close to a deadline would be uncomfortable. But the architecture already fails closed to a verified template, so a poor rate is a *measured limitation*, not a broken product — and finding it in the Q&A instead would be far worse. Also: run against the existing scenarios only; do not change prompts to chase a number.
- **Files.** `eval/run_llm_eval.py` (run, do not edit), then `eval/final_telemetry_report.md`, `eval/round2_traceability.md`, slide 10, proposal §10.
- **Verdict.** **BUILD NOW** — in the sense of *run the harness that already exists*.

## P1 — High-leverage improvements

### P1-1 · Caveat the "0% verification failure" stat
Part 12 item 1. One clause: *"all narrations were the deterministic template — no live model output has been gated."* **Why it matters:** the deck's most safety-critical number is currently measuring the system against itself, and the disproving fact is on slide 10. **Effort:** 10 min. **Risk:** none. **Files:** `submission/deck/slides/slide-06.html`. **Verdict: CHANGE UX ONLY.** (Becomes obsolete if P0-6 runs.)

### P1-2 · Restate the hybrid-retrieval justification
Part 12 item 2. Claim "dense earns its place"; keep hybrid on the capability argument (`PG-504` vs paraphrase), which is sound. **Why it matters:** the current claim is a non-sequitur a technical judge finds in `eval/retrieval_report.md`. **Effort:** 20 min across four files. **Risk:** none. **Files:** slide 09, `R2_BUSINESS_PROPOSAL_SOURCE.md` §3, `eval/data_realism_audit.md`, `eval/judge_defense.md` B4. **Verdict: PITCH BETTER.**

### P1-3 · Put the causal-licence denial (S3) in a demo path
Part 9 item 1. "Association only — the counterfactual test did not license a causal claim" is the most legible restraint the product performs, it takes 8 seconds, and it appears in no demo beat. **Why it matters:** it is the second-strongest trust proof and it is currently unused. **User benefit:** none new. **Competitive benefit:** high — no archetype does this. **Effort:** 30 min (add as optional beat C, or swap for the Evidence-tab beat). **Risk:** none. **Files:** `eval/final_demo_script.md`. **Verdict: PITCH BETTER.**

### P1-4 · Demote 1.000/1.000; lead with 0 FP on 48 clean slices
Part 11. **Why it matters:** removes the most attackable number from large type without changing a fact. **Effort:** 15 min. **Risk:** none. **Files:** `submission/deck/slides/slide-09.html`. **Verdict: PITCH BETTER.**

### P1-5 · Show persona difference side by side
Part 7. S5a vs S5b — same event, different decision economics — exists in `eval/graph_report.md` and is never shown. **Why it matters:** R2-MPE-3 is scored on demonstrated difference, and the demonstrated difference is currently a masthead name. **Effort:** 45 min (a two-column row on slide 08). **Risk:** none. **Files:** `submission/deck/slides/slide-08.html`. **Verdict: PITCH BETTER.**

### P1-6 · Reframe the business-value section as a built instrument
Part 10. Three sentences replacing the concessive framing in proposal §12 and slide 11's ask. **Why it matters:** converts the weakest scored category from apologetic to confident with no new claim. **Effort:** 30 min. **Risk:** none — no number changes. **Files:** `submission/R2_BUSINESS_PROPOSAL.md` §12, `submission/deck/slides/slide-11.html`. **Verdict: PITCH BETTER.**

### P1-7 · Surface one line of evidence on the default screen
Part 7. The cohort panel already computes *"35 payment tickets in the window · none in the 8-week baseline"*. Rendering one such line under the `8 supporting` count answers the "what is the evidence?" question without a tab switch. **Why it matters:** evidence is the differentiator and the default screen currently shows a count. **User benefit:** direct. **Effort:** 1–2 hours. **Risk:** low but non-zero — touches `ui/components/evidence.py` and would need a rendered-output test. **Only do this if P0s are complete.** **Verdict: BUILD NOW (small), else V2.**

### P1-8 · Reorder HYPOTHESIS below ANALYTICAL RESULT
Part 7. The weakest epistemic class currently sits above the strongest. **Why it matters:** a reader who stops after two blocks reads an inference and not the computation supporting it — directly against the project's central claim. **Effort:** ~30 min plus a rendered-text test update. **Risk:** low; touches `app.py::workspace_tab` ordering only. **Verdict: CHANGE UX ONLY** (product UI).

### P1-9 · Gloss `UNCALIBRATED` in plain language
Part 7. Add *"Not enough track record to say"* beside the term. **Why it matters:** a business reader's most available reading of "uncalibrated" is "broken". **Effort:** 20 min. **Risk:** low. **Files:** `ui/components/confidence.py`. **Verdict: CHANGE UX ONLY.**

### P1-10 · Fix the residual dead space on slides 07 and 11
Part 2 §8. Independently inspected: both carry 40–60% empty area despite `eval/pitch_deck_visual_qa.md` marking them Pass. **Why it matters:** sparse slides read as unfinished, which contradicts the density of the actual work. **Effort:** 45 min. **Risk:** none. **Verdict: CHANGE UX ONLY.**

### P1-11 · Normalise 571 → 574 and 1,341 → 1,336 across `eval/`
Part 12 items 3, 7. **Effort:** 20 min. **Risk:** none. **Verdict: CHANGE UX ONLY.**

### P1-12 · Correct "7 supporting" to "8 supporting" in the proposal
Part 12 item 6. **Effort:** 5 min. **Risk:** none. **Verdict: CHANGE UX ONLY.**

### P1-13 · Export the proposal to PDF
`R2_BUSINESS_PROPOSAL.md` exists only as Markdown. Most submission portals expect PDF, and a judge reading raw Markdown reads a worse document than the one written. **Effort:** 30 min. **Risk:** none. **Verdict: BUILD NOW (trivial).**

## P2 — Nice to have

- **P2-1 · Name a persona in slide 01's flow row.** 5 min. Makes the pain personal. **PITCH BETTER.**
- **P2-2 · Reconcile the driver chart's red/green with the stated colour discipline** — either change the chart or amend `eval/growth_design_ux_mapping.md` to describe what the product actually does. **CHANGE UX ONLY** or documentation.
- **P2-3 · Name the buyer** (one line, proposal §3). **PITCH BETTER.**
- **P2-4 · Show the bundle-hash guarantee in the review block** as a consequence sentence, not a hash. **CHANGE UX ONLY.**
- **P2-5 · Widen market-event headline diversity** (5 distinct across 112). Requires regeneration — **do not do this before submission.** **V2.**
- **P2-6 · Remove or exercise `is_test_account`** (no variance across 105,216 rows). **V2.**
- **P2-7 · Reduce bootstrap resamples on the demo path** to cut S1's 13.5 s attribution cost. Only if a live demo is confirmed and cold start cannot be avoided. **V2.**
- **P2-8 · Observe the loading panel mid-flight** — the least-verified component with the most on-screen exposure during a cold run. **V2.**

---

# Part 16 — Build / don't build / pitch only

### BUILD NOW

| Item | Why it clears the bar |
|---|---|
| **90-second demo recording** (P0-3) | The prototype is otherwise unobservable. This is the only item that converts an entire deliverable from "described" to "seen" |
| **Run `eval/run_llm_eval.py`** (P0-6) | Closes the one hard acceptance criterion that is unmet. The harness exists; this is execution, not construction |
| **Proposal → PDF** (P1-13) | Format risk, trivial effort |
| **One inline evidence line** (P1-7) | *Only if P0s are complete.* Closes the weakest gap in the default screen |

### CHANGE UX ONLY (backend already sufficient)

Slide 03 uncrop (P0-1) · slide 07 caveat (P0-2) · slide 06 caveat (P1-1) ·
dead space on 07/11 (P1-10) · HYPOTHESIS/ANALYTICAL reorder (P1-8) ·
`UNCALIBRATED` gloss (P1-9) · doc-consistency fixes (P0-4, P1-11, P1-12)

### PITCH BETTER (capability exists, communication does not)

Abstention on slide 03 (P0-5) · causal-licence denial in the demo (P1-3) ·
evidence freeze as a consequence not a hash · entitlement-before-ranking ·
"the gate blocked our own template" said aloud early · scope separation earlier ·
0 FP over 1.000/1.000 (P1-4) · persona side-by-side (P1-5) · business-value
reframe (P1-6) · **"the model is optional by design" claimed rather than
conceded** (Part 13 #11)

### V2

Live-data pilot · enterprise IAM · real calibration for MEDIUM/LOW · drift
detection · the *learning* half of the feedback loop · durable workflow state ·
managed vector search (triggered by tenant isolation, not scale) · corpus
diversity work

### DO NOT BUILD

Considered explicitly, as instructed. Default skepticism applied.

| Candidate | Verdict | Reason |
|---|---|---|
| **Knowledge graph** | **No** | Semantic contracts already carry definitions, drivers, lineage and access rules. A graph adds a modelling layer with no question it answers that the contracts do not. Weeks of work, zero visible change |
| **GraphRAG** | **No** | 1,336 documents. GraphRAG solves multi-hop synthesis over large heterogeneous corpora; the cause here is reached by *statistics*, not by document hops. It would make retrieval harder to verify, against the project's central claim |
| **More agents** | **No** | Violates `CLAUDE.md` rule 4 and contradicts slide 11's strongest line. Adding agents would destroy the differentiator to gain a demo effect |
| **Fine-tuning** | **No** | The model writes prose into a schema and is verified afterwards. Fine-tuning improves the one thing already gated. It also makes the system non-reproducible |
| **Forecasting** | **No** | R2-SA lists it as an *option*, not a requirement. It answers "what next", and this product is explicitly about "why did this happen". It would blur the positioning |
| **Real-time streaming** | **No** | A run takes 4–50 s and the claim audit verified "real-time" appears nowhere. Adding it would create a claim the system cannot support |
| **Vector database** | **No** | ADR-recorded. 1,336 × 384 brute force is exact at ~200 ms. The trigger is tenant isolation, not scale, and there is one tenant |
| **More LLMs / model routing** | **No** | Routing config exists; live cost is unmeasured. Adding providers multiplies an unmeasured surface |
| **Automated remediation** | **No, emphatically** | "Raise the request, not roll back" is one of the four strongest differentiators. Building execution would delete it |
| **External live data** | **No** | Introduces non-reproducibility into a seeded, byte-identical pipeline for cosmetic realism |
| **More personas** | **No** | Three already exceed MPE-3's two. The problem is that the existing difference is under-*shown*, not under-built (P1-5) |
| **More dashboards** | **No** | The product's position is that it is *not* a dashboard. Adding one argues against the pitch |

---

# Part 17 — If I were the competitor

Five things I would build to beat BusinessIntelligence.ai, in the order I would
build them.

### 1. Ship a 60-second video and a hosted demo
The highest-leverage move against this team. Their system is stronger than mine;
their prototype is invisible without a live slot. I would make sure mine is
watched and theirs is imagined.

### 2. Run a live LLM and measure it
They have no API key, so their MPE-10 is incomplete and their verification stat
is measured against their own template. I would show model-generated narratives,
report first-pass verification rate, tokens, latency and cost per insight, and
let the acceptance-criteria list do the rest.

### 3. Produce one real measured number
Not an ROI table — those get attacked. One measurement: *"we timed three
analysts on a real incident; median 3 hours 50 minutes. Ours: 12 seconds."*
Their principled blank in the impact column loses to any honest number.

### 4. Use a public real dataset
Public retail or e-commerce data instantly neutralises "your data is synthetic",
which is the attack they spend a whole audit defending against. It costs me
detection precision and buys me the credibility they cannot purchase.

### 5. Front-load the wow
Whatever my differentiator is, it goes on slide 02. I would let them spend six
slides earning trust while I spend one.

### Which can be neutralised before submission?

| Threat | Neutralisable? | How |
|---|---|---|
| **#1 video / hosted demo** | **Yes — fully.** | P0-3. Record the 90-second script. Do *not* attempt hosting |
| **#2 live LLM measurement** | **Yes — fully**, and it is the highest-value technical action available | P0-6. The harness is written |
| **#5 front-loading** | **Yes — fully.** | P0-5 + Part 8's cold open |
| **#3 one real number** | **Partially.** | P1-6's reframe. A real baseline cannot be acquired in time and must not be invented |
| **#4 real public dataset** | **No — and do not attempt it.** | Swapping datasets would invalidate the entire evaluation suite, all eight scenario terminals, the detection benchmark and the realism audit, days before a deadline. This is the one threat to accept and answer verbally |

**Three of five are fully neutralisable, and all three are already P0.** That is
the strongest argument for the priority ordering in Part 15.

---

# Part 18 — Final scorecard

| Dimension | Score |
|---|---:|
| Problem | **9** / 10 |
| Product | **8** / 10 |
| UX | **7** / 10 |
| Business value | **5** / 10 |
| Technical depth | **9** / 10 |
| Analytical rigour | **9** / 10 |
| AI innovation | **7** / 10 |
| Responsible AI | **10** / 10 |
| Security | **9** / 10 |
| Differentiation | **8** / 10 |
| Demo | **6** / 10 |
| Judge comprehension | **6** / 10 |
| Production credibility | **7** / 10 |

**Notes on the two that may surprise.**

*AI innovation — 7.* The innovation here is architectural restraint, not model
capability. That is genuinely novel and genuinely valuable, and it will
nonetheless read as conservative to a judge scoring "AI innovation" against
teams shipping agent swarms. The score reflects how it will be *received*, not
how good the decision is. Do not change the architecture to raise it.

*Responsible AI — 10.* Not graded on a curve. Three independently verifiable
structural guarantees (no tools key, no confidence field, no predicate reads
model output), a gate that caught the team's own bug, and a causal licence that
is actually denied. This is the best category in the submission by a distance.

## Overall: **74 / 100**

Consistent with Part 2 by construction — the same evidence, weighted the same
way.

## Current competitiveness: **STRONG CONTENDER**

Not "Competitive", and not "Exceptional".

**Why not Competitive (i.e. why it is higher).** The substance is well past the
threshold. A working 19.6k-line system with 574 tests, an exact identity
decomposition, a verification gate that has caught its own team's bug, a causal
licence that gets denied, a six-stage entitlement chain with a non-vacuity
control, and eleven typed terminal states each with a designed screen — this is
not a competition prototype dressed as a product. Very few of 600 submissions
will have anything comparable behind the demo, and the responsible-AI story is
better than most commercial products'.

**Why not Exceptional (i.e. why it is lower).** Exceptional means a judge
shortlists it after 90 seconds without being convinced. Today that judge sees a
cropped screenshot of a big number, an unqualified 50/25/25 split, a hard
acceptance criterion reading zero, two internal documents disagreeing about
retrieval, no video, and a differentiator on slide seven. The product is
exceptional; the artefacts that carry it to a judge are not yet.

**The classification is a statement about distance, not about quality.** The gap
between Strong Contender and Exceptional here is roughly one working day of
edits and one recording — not a feature, not an architecture change, and not a
single new claim.

---

# Part 19 — Final verdict

## Biggest Strength

**It declines — and the refusal is more useful than most products' answers.**
Six typed abstention states, each with a distinct remedy and a designed screen;
a causal licence that is actually denied on S3; `UNCALIBRATED` where fewer than
ten cases exist; and S4 telling a user to wait four days and why. No competitor
archetype produces this, and it cannot be faked, because faking it requires
knowing exactly why you cannot answer.

## Biggest Weakness

**The submission's transmission is a full band behind its substance.** Every
category scoring 8+ is substance; every category below 7 is transmission. The
differentiator arrives at slide 07 of 11 and demo beat 6 of 7; the product's
best asset is cropped on the Solution slide; there is no video; and the strongest
credibility artefacts live in `eval/` files no judge will open.

## Biggest Competitive Risk

**A UX-first or consulting-style team wins the first 60 seconds and the judge
never reaches the substance.** In a 600-team field, comprehension per second is
the selection filter, and that is precisely the axis where this submission is
weakest and its two most likely rivals are strongest.

## Highest-Leverage Improvement

**Move "it declines" into the first 60 seconds — slide 03 and a demo cold open
— and uncrop the slide 03 hero so the product's five answers are actually
visible.** Roughly ninety minutes of work. It changes what a judge concludes
after three slides, which is the only decision most judges will make.

## Best Existing Feature to Emphasise

**The verification gate blocking the team's own fallback template.** It is one
sentence, it is true, it is checkable, and it does something no polished
submission does: it reports the team's own safety mechanism catching the team's
own bug. It should be said aloud, early, in the pitch — not left as a
danger-tinted card on slide 06.

## Feature We Are Overengineering

**The feedback loop** — five typed outcomes, routed consumers, live counter
updates — with zero cycles run, which converts an R2-OBJ into a ⚠. Runner-up:
the **300–400-resample moving-block bootstrap**, which costs 13.5 s of a 53 s
run (the largest single latency contributor) to produce one line on one slide
that no user ever sees. Neither should be removed; both should stop being
pitched.

## Feature We Are Under-Communicating

**The causal-language licence.** A difference-in-differences test with a
parallel-trend check that gates the word "caused" — and *denies* it on S3, in
the UI, degrading the wording to "association only". It is plain English, it is
visual, it takes eight seconds, no competitor archetype has it, and it appears in
no demo path. Close runner-up: **entitlement resolved before ranking**, whose
underlying insight is genuinely sophisticated and currently sits as a footnote.

## One Thing We Absolutely Should NOT Change

**The deterministic / AI boundary and everything that enforces it** — no `tools`
key, no `confidence` field on `Narrative`, no routing predicate reading model
output, Gate 2's numeric allowlist over a frozen hashed bundle, and failing
closed to a verified template.

This is the product. Every differentiator in Part 14 is downstream of it. It is
also the thing most likely to be eroded by a well-meant late change — a chat box
"because judges like chat", an agent "because it demos well", a confidence score
"because a number looks decisive". Any of those would trade the moat for a
feature every competitor already has.

## Top 5 Actions Before Submission

| # | Action | Effort | Why this one |
|---|---|---|---|
| **1** | **Uncrop the slide 03 hero and put one abstention line on slide 03** (P0-1, P0-5) | ~90 min | Fixes the two highest-probability rejection reasons at once. Makes the differentiator visible in the only three slides most judges read |
| **2** | **Record the 90-second demo** (P0-3, Part 8 script) | 2–3 h | Converts the prototype from described to seen, and lets the refusal be shown first — which a live demo under time pressure cannot guarantee |
| **3** | **Run `eval/run_llm_eval.py` with a key** (P0-6) | ~1 h | The only unmet hard acceptance criterion, and the only fix for a safety stat currently measured against the system's own template. Accept that it may return uncomfortable news — finding it in Q&A is worse |
| **4** | **Add the slide 07 caveat and the slide 06 template clause; fix `eval/final_evaluation_report.md` §3** (P0-2, P0-4, P1-1) | ~45 min | Three places where the project's own standard was not applied to the project's own pitch. Each is a free attack a judge does not need to be told about |
| **5** | **Reframe business value as a built instrument, and lead detection with 0 FP / 48 clean slices** (P1-6, P1-4) | ~45 min | Turns the lowest-scoring category from apologetic into confident, and removes the most attackable number from large type — without inventing a single figure |

**Total: roughly one working day.** None of it is a feature. None of it changes
the architecture. None of it introduces a claim that is not already true.

---

*Audit performed against the repository state of 2026-08-26. No code was
modified. Where this document disagrees with an existing `eval/` report, the
disagreement and its evidence are stated in place.*
