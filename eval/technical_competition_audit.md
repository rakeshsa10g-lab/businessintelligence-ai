# Technical competition audit — independent teardown

**Reviewer role:** second, independent senior architect / product reviewer.
**Posture:** adversarial. Nothing here assumes the current architecture is
right because it is elaborate.
**Method:** read `CLAUDE.md`, the four architecture documents, the submission
pack and every `eval/` report; then inspected the repository; then **ran the
system** — ten probe scripts against the real graph, including deliberate
failure injection, concurrency and profiling. Findings marked `MEASURED-HERE`
were produced during this audit on this machine and are reproducible; they are
not restatements of the project's own reports.

**No repository code was modified.** Probes ran from a scratch directory and
patched only in-process.

---

## 1. Executive verdict

This is, by a wide margin, the most disciplined Round 2 codebase I would expect
to see in a 600-team field. The trust architecture is real: the evidence freeze,
Gate 2, the causal licence, the entitlement chokepoint and the abstention
taxonomy are implemented, tested and *documented against their own failures*.
The self-audits (`claim_audit.md`, `complexity_audit.md`, `data_realism_audit.md`)
are better than most professional engineering post-mortems. The team has already
found and fixed the class of problem that sinks competitors — overstated claims,
a corpus that made retrieval trivial, a p-value that was post-selection.

That is the good news, and it means the remaining risk is concentrated in three
places the project has **not** looked, because all three require *running the
system under conditions the test suite never creates*:

1. **Concurrency breaks the flagship guarantee.** With two browser sessions
   open — two threads on the shared module-global DuckDB connection — result
   sets cross between threads. `MEASURED-HERE`: a region-restricted `ops_lead`
   principal received a 916-row result set containing **East, North, South and
   West**, when her compiled SQL filtered to West and should have returned 229
   rows. This is not an authorisation defect (the policy layer is correct); it
   is a shared-connection defect that produces the exact outcome the
   architecture exists to prevent. Every one of the 32 security tests is
   single-threaded, which is why it was never seen. **The fix is ~5 lines and I
   verified it works** (§7.1, §8 P0-1).

2. **An infrastructure crash is narrated to the user as an analytical
   conclusion.** `MEASURED-HERE`: kill retrieval (or the warehouse) mid-run and
   the user is shown *"A real movement, but nothing explains it — no source the
   system can read supports any particular explanation."* That sentence is
   false; the system never looked. For a product whose central differentiator is
   *honest failure behaviour*, this is the sharpest attack available to a judge,
   and it is a one-node fix (§7.2, §8 P0-2).

3. **The performance analysis in `complexity_audit.md` identifies the wrong
   bottleneck.** It states the moving-block bootstrap is "the single largest
   runtime cost in the system". `MEASURED-HERE`: with the bootstrap disabled
   entirely, attribution still takes **15.4 s of a 17 s run**. 93% of it is
   **288 per-cell STL decompositions** in `build_forecast_cube`, at ~50 ms each.
   The bootstrap costs ~0.6 s. Fixing the real bottleneck takes a warm run from
   ~17 s to ~3–5 s — the largest user-visible improvement available anywhere in
   the project (§6, §8 P0-3).

Beneath those, the biggest *competitive* risk is different in kind: the system
is superb at refusing to be wrong and comparatively thin at **letting a user ask
a second question**. `ui/state.py:139` hardcodes `kpi_id="net_revenue"` and the
eight scenarios are a fixed list imported from the evaluation harness. A judge
who asks "can I look at refund rate for East?" gets a dropdown of eight pre-baked
runs. Competitors with weaker engineering will beat this on *interactivity*, and
the gap is not architectural — every layer already takes a `kpi_id`, a `Window`
and a `slice_filter` (§9, §8 P1-1).

**Verdict: strong shortlist candidate today; winner if P0-1 through P0-5 land.**
The P0s are all small, and each converts a latent embarrassment into another
proof point of the discipline the pitch is built on. That is the cheapest
credibility available anywhere in this project.

---

## 2. Scorecard

| # | Category | Score | Basis |
|---|---|:---:|---|
| 1 | Product | **7.5**/10 | The decision workflow (movement → why → evidence → reliability → bounded action → owner) is genuinely better than the category. Loses points for being scenario-locked: one KPI, eight fixed slices, no user-composed question |
| 2 | UX | **8**/10 | Progressive disclosure is exemplary; the epistemic classes are a real innovation; research-grounded throughout. Loses points for **no KPI time-series chart** — the artefact this category is defined by — and for a 17 s spinner with no cached results |
| 3 | Technical architecture | **9**/10 | 12 acyclic packages, one data chokepoint, thin nodes, typed contracts, routing that provably cannot read model output. Docked for the shared-connection global and for `ui/` importing `eval/` |
| 4 | Analytical rigor | **9**/10 | ADR-015/016/017/018/019/022 are the work of people who checked their own arithmetic and found it wrong. Docked for confidence calibration having **no held-out split** (§5.3) |
| 5 | AI innovation | **7**/10 | The innovation is *constraint*, not capability — schema-constrained narration, no tools key, no confidence field, verified template. Strong and defensible, but **zero live model calls have ever been made**, so the AI half of an AI challenge is unexercised |
| 6 | Trust | **9.5**/10 | Best-in-class: freeze + hash, ten deterministic checks, causal licence, calibrated bands that report `UNCALIBRATED`, abstention as a first-class outcome. Docked only for P0-2 — a crash wearing an abstention's clothes |
| 7 | Security | **7**/10 | Design excellent (filter-before-rank, single chokepoint, audit on denial, non-vacuity control). **Downgraded from 9.5 by the measured concurrency cross-over** — a correct policy defeated by an implementation global |
| 8 | Business value | **7**/10 | Levers, decision rights, owner, monitoring metric, and a *range* with its basis named. Honest that `p_human` and decision values are assumptions. No baseline and no measured saving — correctly not claimed, but it costs points against teams that will simply assert one |
| 9 | Demo | **6.5**/10 | The story is excellent and the script is disciplined. The mechanics are fragile: 17 s warm runs (the script says 4 s), a 36 s first-query model load, no result cache, a network fetch on a cold machine |
| 10 | Differentiation | **9**/10 | "It declines, and it can prove why" is a category-defining position, and it is *implemented*, not asserted |
| 11 | Production credibility | **8.5**/10 | `PRODUCTION_EVOLUTION.md` with triggers-not-volumes is the most senior document in the repository. Docked because the "~2 concurrent users" limit is presented as throughput when it is actually **correctness** |

**Weighted overall competition readiness: 8.1 / 10** — top decile, with three
small defects standing between it and top percentile.

---

## 3. Competitor archetypes

For each: what they will build, where they beat you, how you beat them, what is
worth stealing. Assume the strongest version of each, not the median.

### 3.1 Generic agentic BI copilot
**Architecture.** LangChain/LangGraph `create_agent` loop, SQL-generation tool
over a warehouse, retriever tool, chart tool, chat UI, streaming tokens.
**Strengths.** Feels magical in 90 seconds. Any question, any KPI, instant.
Beautiful streaming. Effortless "wow".
**Weaknesses.** Every number is model-produced. No materiality concept. Cannot
say "I don't know". Text-to-SQL breaks on the third question and nobody notices
because the answer still looks right.
**Where they beat you.** Interactivity, breadth, perceived intelligence, demo
energy. A judge who values "ask it anything" prefers them.
**How you beat them.** Ask their demo for a number, then ask *"how do you know
that's right?"* Their answer is "the model wrote SQL". Yours is a frozen hashed
bundle and ten mechanical checks. Then show S7: their system narrates a channel
rename as 5.9% growth; yours declines to alert.
**Steal.** Two things only: (a) *streaming progress* — `ui/components/progress.py`
exists; use it so 17 s reads as work, not as a hang; (b) a **question composer
that is not a chat box** (§9.2).
**Overkill.** Their agent loop. Do not add tools. Your whole thesis is that a
model which can re-query is the failure mode.

### 3.2 RAG analytics assistant
**Architecture.** Pinecone/Chroma + embeddings over documents + LLM with
citations. Possibly a metrics table dumped into the index.
**Strengths.** Citations look rigorous. Cheap to build, easy to make pretty.
**Weaknesses.** No statistics at all — cannot establish that a movement is real,
let alone material. Retrieval over numbers is a category error (their AOV will
be "approximately"). No entitlement model.
**Where they beat you.** Corpus breadth, apparent source coverage, possibly a
slicker citation UI.
**How you beat them.** LMDI closing to 0.000000000% and the self-explaining
109.9% share is a number no retrieval system can produce. And your retrieval is
entitlement-filtered *before* ranking; theirs filters after, if at all.
**Steal.** Their citation polish — inline hoverable source cards. Your Evidence
tab is good, but one CRM card currently renders with the literal heading
"Evidence" (§10).
**Overkill.** A vector database. ADR-004 is right; 1,336 × 384 floats is a numpy
array.

### 3.3 Multi-agent root-cause system
**Architecture.** Planner / analyst / critic / writer agents, message bus,
CrewAI or AutoGen. Impressive architecture diagram.
**Strengths.** The diagram sells. "Critic agent" sounds like verification.
Judges who equate agent count with sophistication reward it.
**Weaknesses.** Every agent boundary is a place a number mutates unchecked. A
critic agent is an LLM judging an LLM — CALM (arXiv 2508.21273) shows that
degrades as often as it helps. Non-deterministic, unauditable, slow, expensive.
**Where they beat you.** Perceived AI sophistication. This is your biggest
*narrative* risk: a judge may read "no multi-agent" as "less advanced".
**How you beat them.** Name it first and make it a virtue — ADR-009 is written;
put its argument on a slide as *"we removed the agents on purpose, here is the
failing case"*. Then show the deterministic thing their critic cannot be: Gate 2
blocked **your own template**, a result an LLM critic can never guarantee.
**Steal.** Nothing architecturally. Steal the *vocabulary*: they say "critic
agent"; you say "**guardian layer**, and ours is deterministic".
**Overkill.** Any of it.

### 3.4 Traditional ML anomaly detector + LLM
**Architecture.** Prophet / Isolation Forest / LSTM autoencoder for detection,
then an LLM to write it up. Possibly a real training pipeline.
**Strengths.** Credible ML story. ROC curves. Feature importance. An ML-background
judge feels at home.
**Weaknesses.** Detects, does not explain — SHAP over a forecast error is not
attribution. No evidence integration. No abstention. Usually no materiality
distinction, so precision is terrible on real data.
**Where they beat you.** ML-flavoured charts, and possibly genuine out-of-sample
validation, which you lack.
**How you beat them.** Two separate legs — statistical significance **and**
business materiality (`detection/materiality.py`) — plus **0 false positives on
48 clean slices**, which is the harder half of your detection result and the one
to lead with. Their detector fires on everything.
**Steal.** *Out-of-sample discipline.* Their train/test split is exactly what
your confidence calibration is missing (§5.3).
**Overkill.** Deep models. STL/MAD/PELT is more defensible and 100× cheaper to
justify.

### 3.5 Deep causal analytics solution
**Architecture.** DoWhy / EconML, causal graphs, propensity scores, possibly DAG
discovery (PC / NOTEARS), synthetic control.
**Strengths.** The most technically intimidating competitor. Real causal
vocabulary. A DAG on a slide is persuasive.
**Weaknesses.** Causal discovery on observational business data with six events
is unidentifiable, and they will not say so. Usually no product around it. No
evidence retrieval. Their assumptions are unstated where yours are tested.
**Where they beat you.** Perceived methodological depth. An econometrician judge
out-argues you on method.
**How you beat them.** You **test the parallel-trends assumption and refuse the
licence when it fails** (`attribution/counterfactual.py::_parallel_trend`; S3
denied). Ask them: *"what happens in your system when parallel trends fail?"*
Most implementations do not check. Your position — *DiD licenses wording, not
truth* — is the more sophisticated one and it is already on the slide.
**Steal.** *Synthetic control* as a named V2 line (a weighted donor pool beats a
single best-correlated control). Mention it; do not build it.
**Overkill.** Causal discovery. Say why: with 4 dimensions and 6 events the graph
is not identifiable, and a wrong DAG is worse than no DAG.

### 3.6 Enterprise BI copilot (Power BI / Tableau-embedded)
**Architecture.** Semantic model over a real warehouse, RLS from the BI tool, LLM
narration inside the vendor's frame.
**Strengths.** Real IAM, real RLS, real deployment story, familiar surface.
Answers "how does this reach my users" better than you can.
**Where they beat you.** Authentication (you have none), embedding into existing
workflow, enterprise plausibility.
**How you beat them.** Their narration is unverified prose over a correct number
— exactly the failure mode of the 2026 fidelity audit you cite. They have no
abstention path: a BI copilot always answers. And your entitlement runs *before
ranking* over unstructured evidence, which no BI tool does at all.
**Steal.** Their answer to distribution. One line on the roadmap slide: *"the
natural surface for V2 is inside the BI tool the analyst already has"* —
`PRODUCTION_EVOLUTION.md` row 4 says this; the deck does not.
**Overkill.** Building an actual Power BI extension.

### 3.7 Pure UX/product winner
**Architecture.** Thin analytics, exceptional design. Figma-grade interface,
motion, live charts, mobile view, maybe a Next.js frontend.
**Strengths.** In a five-minute pitch, design reads as quality. Judges are human.
**Weaknesses.** Under one hard question the analytics collapse.
**Where they beat you.** Immediately and visibly. Streamlit looks like Streamlit,
and **you have no time-series chart** (§9.1). This is the archetype most likely
to beat you on the day.
**How you beat them.** Close the visual gap cheaply: one KPI chart with the event
window shaded and the STL counterfactual drawn dashed turns your strongest hidden
machinery into your strongest visible artefact. Then let the abstention screens
work — S4 and S7 are better *product* than a prettier version of a wrong answer.
**Steal.** Exactly one thing: the chart. Do not restyle the app.
**Overkill.** Replacing Streamlit. ADR-006 is right and the roadmap concedes it.

### 3.8 Consulting-style strategy solution
**Architecture.** Slides. Maybe a Figma prototype. Deep market framing, TAM, GTM,
pricing, org design.
**Strengths.** Business narrative, ROI arithmetic, exec fluency. They will quote
a number for time saved. You explicitly will not.
**Where they beat you.** The business-value slide, every time.
**How you beat them.** "Round 2 asks for a working prototype." Then run S2 live
and let the system refuse to answer.
**Steal.** One quantified frame you can defend: not "we save X hours" but **"here
is the decision this changes and who owns it"** — the scope band ("Raise the
request, not roll back") is your business slide and it is buried on slide 08.
**Overkill.** TAM sizing. You lose that fight and it is not what Track 3 grades.

---

## 4. Architecture critique

For each layer: **excellent / fragile / unnecessary / missing / what a judge
attacks.**

### 4.1 System design (LangGraph, 26 nodes, 11 terminals)
- **Excellent.** Routing predicates are pure functions of deterministic state,
  and `test_no_routing_predicate_reads_a_narrative` asserts it against the
  *source*, not the behaviour. That single test is worth more than the graph.
  Eleven typed terminals with distinct screens is real product design.
- **Fragile.** Nodes execute even when their predecessor failed: `retrieve`
  raising leaves `rank_hypotheses` to raise `KeyError: 'retrieval'`
  (`MEASURED-HERE`, §7.2). It fails safe, but records three failures for one
  fault and produces a misleading terminal.
- **Unnecessary.** Nothing. 26 nodes for 11 terminals and one bounded cycle is
  not bloat.
- **Missing.** A **system-error terminal downstream of gate 1**. `CONTRACT_ERROR`
  exists but is unreachable after `enforce_entitlements`; every later crash is
  laundered into an abstention.
- **Judge attacks.** *"Why LangGraph and not a for-loop?"* The honest answer is
  on your side (interrupt + durable checkpoint + resume with an identical bundle
  hash is not a for-loop) and `graph_report.md` measures overhead at 13–40 ms.
  Have the resume demo ready; it is the only unanswerable version of the answer.

### 4.2 Module boundaries
- **Excellent.** 12 packages, 0 circular imports, every engine takes a
  `Principal` or a frozen bundle, `security/` never imports `semantic/`. The
  chokepoint test is mechanical.
- **Fragile.** `ui/state.py:38` imports `SCENARIOS`, `PERSONAS`, `WINDOW` from
  `eval/run_recommendation_eval.py`. The shipping application depends on the
  evaluation harness at import time. ADR-028's intent (one executable definition)
  is right; the direction is wrong — both should read `config/scenarios.yaml`.
- **Missing.** A boundary test for the reverse direction: nothing stops `eval/`
  from growing product logic that `ui/` then depends on.
- **Judge attacks.** "Show me the dependency graph." You win this. Have the
  0-circular-imports figure ready.

### 4.3 Analytical pipeline
- **Excellent.** ADR-016 (STL smoothers that cannot absorb the event) is the best
  piece of statistical engineering in the repository — a measured leak of −6.76%
  against a ground truth of −24.98%, found and closed. ADR-015 (dimensionless BIC
  penalty) is second.
- **Fragile.** Materiality is calibrated **for `net_revenue` only** (ADR-017,
  stated). Four contracts carry intuition-authored floors. A judge who says "run
  it on `refund_rate`" is on untested ground.
- **Unnecessary.** Nothing — but see §6: the *cost profile* is not what the
  project believes it is.
- **Missing.** Any **out-of-sample** validation. Detection thresholds use an
  event-free holdout (good); confidence calibration does not (§5.3).
- **Judge attacks.** "1.000/1.000 is a red flag." Your own answer is right: lead
  with **0 false positives on 48 clean slices**, not with recall.

### 4.4 Retrieval
- **Excellent.** Per-cause-bucket queries (ADR-021) is genuinely good, and the
  failure it fixes — searching payment terms because the driver was conversion —
  is the exact confirmation-bias trap most competitors will ship. RRF across
  buckets *and* retrievers is elegant.
- **Fragile.** `embed_query` is called inside the retrieval loop with no guard; a
  model-load failure propagates as a node crash (§7.2). The sentence-transformer
  is fetched from HuggingFace on first use — a cold machine with no network
  cannot run the demo at all, and offline first-load still costs **36.4 s**
  (`MEASURED-HERE`).
- **Missing.** A `BM25_ONLY` degradation path when the dense model is
  unavailable. The mode exists in `RetrievalMode`; nothing selects it
  automatically.
- **Judge attacks.** "Hybrid didn't beat BM25" — no longer true after the corpus
  widening, and *"we widened the corpus and our numbers got worse"* is your most
  credible evidence-discipline story. Lead with it.

### 4.5 EvidenceBundle / freeze boundary
- **Excellent.** Frozen Pydantic models, tuple collections, a canonical hash with
  `created_at` and raw analytical objects excluded for stated reasons. The
  identical hash across interrupt/resume is a strong demo beat (`MEASURED-HERE`:
  confirmed stable).
- **Fragile.** `history_days` and `has_stable_baseline` — two inputs that gate
  **lever eligibility** — are supplied by the *caller* and hardcoded per scenario
  id in five places, including `ui/state.py:146`. Detection already computes
  `coverage.observations_available`; the bundle should read it.
- **Judge attacks.** "What exactly is hashed?" You have a good answer — but a
  judge who reads `ui/state.py:146` will ask why the UI is telling the analytics
  layer how much history exists (§8 P1-4).

### 4.6 Verification (Gate 2)
- **Excellent.** Checking the *structured claim* rather than the prose (ADR-024)
  is the correct and non-obvious design. Eleven checks, deterministic ordering,
  and the gate blocking your own template is the strongest single piece of
  evidence in the project.
- **Fragile.** Nothing in the implementation.
- **Missing.** **Semantic entailment.** Every check is set-membership or a string
  test. A claim that cites a real evidence id, uses only allowlisted numbers,
  states the correct direction and names the dominant driver can still
  *misrepresent what the cited document says*. Gate 2 verifies references, not
  meaning.
- **Judge attacks.** The sharpest available verification question, and it is not
  answered anywhere in `judge_defense.md`: *"Your gate checks that the citation
  exists. What checks that the sentence is what the document says?"* Prepared
  answer in §5.5.

### 4.7 LLM boundary
- **Excellent.** No `tools` key (asserted against the recorded request), no
  `confidence` field on `Narrative`, failure as a return value, one call. Three
  structural guarantees rather than three prompt instructions.
- **Fragile.** **It has never run.** Zero live model calls across the project
  (`final_telemetry_report.md`: LLM calls 0, tokens 0, cost $0). Every narration
  claim is validated against fake clients only.
- **Missing.** Any handling of **indirect prompt injection**. Up to 12 evidence
  excerpts of untrusted third-party text (support tickets, CRM notes) are
  interpolated into the payload with no delimiting, no instruction-stripping and
  no test. `security_audit.md` does not mention injection once.
- **Judge attacks.** "A customer writes 'ignore previous instructions' in a
  support ticket — what happens?" Today the honest answer is *"we don't know,
  because no model has ever read our prompts."* That is a bad answer in an AI
  competition (§8 P0-4, P1-7).

### 4.8 Recommendation / deferral
- **Excellent.** The expected-loss rule is the right formulation, and the
  request-vs-approve distinction ("Raise the request", never "roll back") is the
  most commercially astute thing in the product. `never_automate_lever_ids` and
  the persona-rights guard are real.
- **Fragile.** `p_human`, decision values and `recovery_fraction` are assumptions
  that move the automate/defer boundary directly. Correctly labelled — but a
  judge can wobble the whole automation story by asking where 0.90 came from.
- **Missing.** Sensitivity analysis *in the UI*. `eval/sensitivity.py` exists;
  nothing surfaces *"this decision flips if p_human > 0.93"*. One line turns the
  weakest input into a demonstration of rigour.
- **Judge attacks.** "You automated an action on a made-up probability." Answer
  with the sensitivity band, not with a defence of the number.

### 4.9 Telemetry
- **Excellent.** Recorded as the node runs, not reconstructed. Allowlist
  redaction. Lineage built inside a guard so a formatting fault cannot destroy an
  analysis — that lesson deserves a slide of its own.
- **Fragile.** Dies with the process (documented, with a trigger).
- **Missing.** Node **failure** is recorded but never surfaced in the business
  view: Audit shows the error, Workspace shows a confident abstention (§7.2).

### 4.10 Security
- **Excellent.** Filter-before-rank; audit on denial; a six-stage leak chain with
  a **non-vacuity control** — a technique most professional teams do not use.
- **Fragile — the audit's most serious finding.** The gateway holds a single
  module-global DuckDB connection (`semantic/gateway.py:30`) behind a lock that
  guards *connection creation only*, not query execution. Under concurrent
  threads, result sets cross (§7.1).
- **Missing.** Authentication (known, correctly stated). SQL-string interpolation
  of `principal.user_region` into the row filter
  (`security/entitlements.py:141`) is safe today because personas are a fixed
  dict, but it is a string-concatenation path into SQL that will meet real IdP
  claims in V2.
- **Judge attacks.** "Two of us open the app at once — what happens?" Today:
  wrong data, possibly another persona's rows. After P0-1: a demo-able
  regression test that makes the guarantee stronger than it was before.

---

## 5. The hardest questions a strong technical judge will ask

Each: **truthful answer · evidence · residual weakness · how to improve.**
Questions `eval/judge_defense.md` already answers well (synthetic data, why not
let the LLM query, why LangGraph, why no vector DB) are skipped; these are the
ones **not** covered there.

### 5.1 Data
**Q: Your events were injected by the same code your detector was tuned against.
Isn't detection recall tautological?**
*Answer:* Yes, and we say so — recall of 1.000 is recall over *injected* events
constructed to be detectable by this method's assumptions. The load-bearing
figure is **0 false positives across 48 clean slices**, which is not guaranteed
by construction. *Evidence:* `detection_report.md`, `claim_audit.md`.
*Residual:* no event class the generator never imagined.
*Improve:* inject three *adversarial* shapes the pipeline was not designed for —
a slow ramp, a step that reverses, a seasonal-amplitude change — and report
whatever recall results, failures included. One afternoon; enormous credibility.

**Q: `sessions` appears in two sources with a 4.45% gap. Which one is true?**
*Answer:* Neither is wrong; they are different populations, and we measure and
report the difference as a `SourceReconciliation` rather than absorbing it
(ADR-018). *Evidence:* `attribution/engine.py::source_reconciliation`.
*Residual:* the reconciliation is computed but barely surfaced in the UI.
*Improve:* one Method line: *"S2 sits −4.45% below S1; classified population, not
definition; not used in the identity."*

**Q: Your grain is daily, finance is weekly at T+3, sessions are hourly. Where
does the mixing happen?**
*Answer:* It does not — the identity is evaluated entirely on the S1 population
at daily grain, precisely so nothing mixes (ADR-018).
*Residual:* the heterogeneous-source story is therefore told through
reconciliation and freshness, not through the arithmetic. Defensible — but
rehearse it, because the brief emphasises heterogeneity and a judge may read
S1-only as a dodge.

### 5.2 Statistics
**Q: PELT selects the window, then you report a Welch p-value on that window.
That is post-selection inference.**
*Answer:* Correct, and we found it ourselves: it reads p < 0.001 on pure noise,
so it was removed from confidence (ADR-017) and is reported for transparency
only, never gating. **One of your strongest answers — rehearse it.**
*Residual:* it is still displayed, which invites the question.
*Improve:* label it in Method as *"post-selection; reported, not used"*.

**Q: Your materiality threshold (9.0%) was calibrated on `net_revenue` alone.
What about the other four KPIs?**
*Answer:* They carry intuition-authored floors, recorded as a known limitation
(ADR-017). *Improve:* run the same null-distribution calibration for all five.
`eval/run_detection_eval.py` has the machinery. **High value per hour** — it
converts "we calibrated one" into "we calibrated all five, here is each null
distribution".

**Q: The bootstrap resamples the same series. That is ranking stability, not
out-of-sample validity.**
*Answer:* Agreed, and it is stated that way in `final_evaluation_report.md`.
*Improve:* one honest sentence on the slide — *"stability under resampling, not
generalisation; generalisation needs a pilot."*

### 5.3 Calibration — the question nobody has asked yet
**Q: Your S1 screen says "correct in 12 of 12 similar past cases". Was S1 in
those 12?**
*Answer, truthfully:* **Effectively yes.** `eval/seed_calibration.py` builds the
table over a slice universe of single dimensions plus region × other, across the
same six injected events — and the demo slices are drawn from that universe.
There is **no held-out split** for confidence calibration, unlike the retrieval
benchmark (proper dev/eval split) and unlike the materiality threshold
(event-free holdout period).
*Evidence:* `eval/seed_calibration.py::slice_universe`, `config/calibration.json`
(n_cases 64; HIGH 12/12).
*Residual:* the track record displayed beside a demonstrated case is not
independent of that case. This is the most legitimate statistical attack on the
project and it lands on **the most user-visible number in the product**.
*Improve — cheap, before submission:* re-seed the table excluding the demo
scenario slices and add one caption line: *"the comparable cases exclude this
slice"*. If the counts worsen, that is another "our numbers got worse and we kept
them" story, which is your best genre.

### 5.4 Attribution and causality
**Q: LMDI assumes a multiplicative identity. What about a pure mix shift that is
not in the identity?**
*Answer:* Adtributor answers the dimensional question, LMDI the factor question;
a mix shift with unchanged marginals returns `MULTI_DIMENSIONAL_CASE` and routes
to a human (ADR-019, with a worked 2×2 counterexample). **Exceptionally good
answer — rehearse it verbatim.**

**Q: Adtributor on a ratio KPI?**
*Answer:* Refused structurally — `assert_attributable` raises; ratios route via
`attribute_via` to a fundamental. Strong.

**Q: Your DiD picks the single most-correlated control. Why not synthetic
control?**
*Answer:* A single donor with a *tested* parallel-trend assumption is the honest
minimum; synthetic control is the named V2 upgrade.
*Residual:* with four regions the donor pool is three, which is thin, and
`MIN_CORRELATION = 0.30` is a low bar.
*Improve:* report the chosen control, its pre-period correlation and the
runners-up in Method. `considered` is computed and then discarded.

### 5.5 Verification — the question not in `judge_defense.md`
**Q: Gate 2 checks that a citation exists. What checks that the claim is what the
cited document actually says?**
*Answer, truthfully:* Nothing does. Gate 2 verifies references, numbers,
direction, coverage and licence — all decidable set/string tests, chosen because
a verifier unreliable in the direction of *accepting* is worse than none
(ADR-024). Semantic faithfulness is not checked.
*Residual:* a well-formed narrative could cite a real ticket, mischaracterise it,
and pass all eleven checks.
*Improve:* add an **advisory** entailment check — claim text against its cited
excerpts, scored with the embedding model already loaded; cosine below a floor
emits an `INFO` violation and never blocks. Consistent with "LLM-as-judge is
advisory only", costs ~5 ms, and converts an unanswered question into a designed
answer (§8 P1-8).

### 5.6 Retrieval
**Q: Your relevance labels come from the generator. Isn't the benchmark
circular?**
*Answer:* Labels come from `planted_for` / `is_decoy`, read only by the benchmark
builder and the harness; `tests/test_retrieval.py` asserts no module under
`retrieval/` mentions them. There is a dev/eval split.
*Residual:* labels encode *planted-ness*, not human judgement of usefulness.
*Improve:* hand-label 20 pairs and report agreement. Two hours, and it is the
difference between "generated benchmark" and "generated benchmark, spot-checked
by a human".

### 5.7 LLM
**Q: How do you know your prompts work?** *Today:* you do not. Zero live calls.
*Improve:* §8 P0-4 — the single highest-value hour available.

**Q: An untrusted support ticket goes into your prompt. What stops it steering
the narrative?**
*Answer:* Structurally, a lot — no tools, no confidence field, numbers
allowlisted, citations must resolve, causal wording licensed, dominant driver
enforced. But there is **no injection-specific defence and no test**.
*Improve:* one test that plants an injection string in a document body and
asserts Gate 2 still blocks the resulting narrative, plus explicit delimiting of
excerpts in `llm/payload.py`. Half a day, and it converts a likely question into
a prepared answer.

### 5.8 Security
**Q: Two analysts use it at once. Prove nobody sees the other's rows.**
*Today:* you cannot (§7.1). After P0-1 you can, with a test.
**This is the question I would ask if I wanted to break this project.**

### 5.9 LangGraph
**Q: Is the graph decorative?**
*Answer:* No, and the proof is not the diagram — it is `resume_review` continuing
a paused run from a durable checkpoint with an **identical bundle hash**
(`MEASURED-HERE`: confirmed), plus a retry cap enforced on state so a resumed run
cannot buy a fresh budget (ADR-030), plus a `recursion_limit` backstop that
exists because the counter was once wrong.
*Residual:* after resuming, the terminal is **still** `REVIEW_REQUIRED`
regardless of the analyst's decision, and the decision is not recorded anywhere
durable (§7.4). A judge who resumes twice sees the same screen twice.
*Improve:* §8 P0-5.

---

## 6. Performance — where the time actually goes

`MEASURED-HERE`, Windows 11 / Python 3.13.4, warm process, in-memory
checkpointer, `HF_HUB_OFFLINE=1`, index pre-loaded.

| Stage | Measured | Note |
|---|---:|---|
| `load_index()` | **0.0 s** | numpy + json; genuinely free |
| First `get_model()` | **36.4 s** | offline, from disk. With no network and no cache, HF HEAD requests retry 5× with backoff before failing |
| S1 warm end-to-end | **17.6 / 16.7 s** | two consecutive runs |
| S2 warm end-to-end | **16.7 / 16.9 s** | |
| Whole market (no slice) | **15.9 / 17.3 s** | |
| — of which `attribute` | **15.3–16.6 s (93–95%)** | |
| — of which `detect` | 0.4–0.5 s | |
| — of which `retrieve` | 0.2–0.3 s | steady state, as documented |
| — of which `rank_hypotheses` | 0.0–0.1 s | |
| Gate 2 | < 5 ms | as documented |
| Graph overhead | 13–40 ms | as documented — the project's figure is correct |

### The finding that changes the optimisation target

`complexity_audit.md` states the moving-block bootstrap is *"the single largest
runtime cost in the system — 3.7–14.2 s of every run, dominating everything else
combined."* **That is not what the profiler says.**

```
attribute(n_resamples=0,  robustness off) : 15.4 s
attribute(n_resamples=30, robustness on ) : 15.3 s

cProfile, cumulative:
  288 calls   14.076 s tottime   detection/decompose.py:37(decompose)
    1 call     0.628 s cumtime   attribution/robustness.py:82(assess)
```

- The bootstrap costs **0.63 s**, not 14 s.
- **288 per-cell STL decompositions** inside `build_forecast_cube` cost
  **14.1 s** — 93% of the run. The cube is region(4) × channel(5) × segment(3) ×
  product_category(5); every non-empty cell gets its own robust STL over 229
  days.
- Isolated cost of one decomposition: **`robust=True` 75.7 ms vs
  `robust=False` 11.6 ms — a 6.5× multiplier** (`MEASURED-HERE`).

Three fixes, ascending risk:

1. **Parallelise the cube** (thread/process pool over cells). No numerical change
   whatsoever. Eight cores ⇒ ~14 s → ~2–3 s. **Lowest risk, biggest win.**
2. **Cache the cube** keyed by (kpi, window, principal filter, dims). Repeat runs
   become near-instant and the demo's back-and-forth stops costing 17 s a click.
3. **`robust=False` for cube cells only**, keeping robust STL on the primary
   detection series where outlier resistance is load-bearing. ~6× on the same
   path — but it *can* move numbers, so it needs a before/after table across the
   eight scenarios before it is defensible.

**If you had 2× development time, this is where the largest user-visible
improvement lives** — not in analytics, not in the model. A three-second run
turns the demo from "click, explain the wait, hope" into "click, done", and
removes the only moment in the pitch where the presenter must fill silence.

Second-largest: the **36 s first-query model load**. Cheapest mitigations first:
call `warm_up()` at app start (it is written and never called from `app.py`);
ship a pre-flight script that loads the model and fails loudly if the HF cache is
cold; set `HF_HUB_OFFLINE=1` in the documented run environment so a venue network
cannot introduce a retry storm.

**Streamlit reruns.** `app.main()` re-runs the whole analysis whenever the
scenario *or persona* differs from the stored result, and `st.session_state`
holds exactly **one** result. Clicking S1 → S2 → S1 costs three full runs
(~50 s). A dict keyed by `(scenario_id, persona_id)` is a five-line change with
outsized demo value.

**LLM cost/latency.** Unmeasured, correctly not estimated. Expect single-digit
seconds and sub-cent per insight on a Claude-class model with a ~4–6k-token
payload — but *measure it*; do not put an estimate on a slide.

---

## 7. Kill-the-demo results

Ten probes against the real graph. `✅` = typed terminal, no traceback, coherent
audit trail. `⚠` = failed safe but the user was misled. `❌` = incorrect result
or a broken guarantee.

| # | Attack | Result | What happened |
|---|---|:---:|---|
| 1 | Unknown KPI | ✅ | `CLARIFY_REQUESTED`, lists the real KPIs, 0.1 s |
| 2 | Unknown persona | ✅ | `CONTRACT_ERROR`, loud and correct — a config bug is not a polite abstention |
| 3 | Nonexistent slice value (`region=Atlantis`) | ✅ | `ABSTAIN_DATA_QUALITY` — "no observations returned for this slice and window" |
| 4 | Nonexistent dimension (`planet=Earth`) | ⚠ | Silently drops the unknown dimension, runs the full unfiltered analysis for **101.9 s**, then abstains |
| 5 | 2-day window | ✅ | `ABSTAIN_SPARSE_HISTORY`, "2 of 56 days", says how long to wait |
| 6 | Future window | ✅ | `ABSTAIN_DATA_QUALITY` |
| 7 | Inverted window | ✅ | Rejected by Pydantic at the type boundary before any work |
| 8 | Restricted KPI (`ops_lead` → `refund_rate`) | ✅ | `ACCESS_DENIED` plus an audited denial, 0.1 s |
| 9 | Garbage JSON from the model | ✅ | Falls to `VERIFIED_TEMPLATE`; Gate 2 passes; HIGH confidence intact |
| 10 | **Fabricating model** ("revenue fell 99.9%", cites `FAKE-1`) | ✅ | Blocked; `VERIFIED_TEMPLATE`; the fabricated number never reaches the user |
| 11 | Client raising on every call | ✅ | `VERIFIED_TEMPLATE` after the capped retry |
| 12 | **Retrieval outage** | ⚠ | §7.2 — a false analytical statement |
| 13 | **Warehouse outage mid-run** | ⚠ | Same terminal, same false statement |
| 14 | Checkpoint resume | ⚠ | Bundle hash stable ✅; terminal unchanged and decision unrecorded (§7.4) |
| 15 | Double resume | ⚠ | Accepted silently; no idempotency guard; same screen returned |
| 16 | Repeated identical runs | ✅ | Deterministic terminals and identical bundle hashes once warm |
| 17 | **Concurrent use** | ❌ | §7.1 — **the entitlement guarantee is broken** |

### 7.1 ❌ Concurrency: cross-principal result leakage

*Probe:* three threads as `priya` (`ops_lead`, row filter `region='West'`) and
three as `meera` (`analytics_lead`, all regions), each issuing six
`guarded_query` calls against the shared gateway connection.

```
done in 1.0s   reads=26  errors=10
ENTITLEMENT VIOLATIONS (priya seeing non-West):
  [('priya', ['East','North','South','West'], 916)]
shapes: priya→0 rows ×5 · priya→229 West ×5 · priya→1 row ×3
        meera→0 rows ×4 · meera→229 West ×4 · meera→916 all-regions ×1 …
errors: ValueError: no watermark recorded for source 'S1'
        TypeError: argument of type 'NoneType' is not iterable
        TypeError: unsupported operand type(s) for -: 'datetime.datetime' and 'date'
```

Three harms, ascending severity:

1. Spurious exceptions from a healthy database (a missing watermark that exists).
2. **Silently wrong inputs** — 0-row and 1-row result sets that would drive an
   analysis to "no observations for this slice": a wrong *analytical* answer
   caused by a second user clicking Run.
3. **A restricted principal receiving another principal's rows.** Priya's SQL
   correctly carried her row filter; the shared connection handed her a different
   query's result.

*Cause:* `semantic/gateway.py:30` — one module-global `duckdb` connection; `_lock`
guards creation only, not `con.execute(...)`. Streamlit runs each session on its
own thread, so two open browser tabs suffice.

*Why 32 security tests pass:* every one of them is single-threaded.

*Verified fix (`MEASURED-HERE`).* Handing each thread its own DuckDB cursor —
patched in-process, no repository change — produced:

```
WITH per-thread cursor: 0.6s  reads=36  errors=0
violations: none
shapes: meera→916 all-regions ×18 · priya→229 West ×18
```

Zero errors, zero violations, every result set correct — and faster. The change
lives inside `connect()` / `guarded_query` and touches nothing else.

### 7.2 ⚠ An infrastructure crash delivered as an analytical conclusion

*Probe:* force `retrieval.engine.retrieve_evidence` to raise `ConnectionError`;
separately force `attribution.engine.attribute` to raise a DuckDB lock error.

Both produce the same user-facing screen:

> **A real movement, but nothing explains it**
> "The movement itself is established — it cleared detection and the materiality
> gate. What is missing is corroboration: no source the system can read supports
> any particular explanation."

Telemetry records the truth (`retrieve: ConnectionError…`, then
`rank_hypotheses: KeyError 'retrieval'`) and the Audit tab would show it — but
the Workspace states, confidently and falsely, that a search was performed and
came back empty. The next-step advice ("name the missing source") sends the
analyst to solve a data-coverage problem that does not exist.

*Cause:* `graph/routing.py::route_sufficiency` maps both `"insufficient"` and
`"error"` to `abstain_insufficient_evidence`, and that node's `terminal_reason`
is a constant string that never inspects `state["error"]`.

*Why it matters more here than elsewhere:* the entire pitch is *"it knows when it
should not answer"*. A crash wearing an abstention's clothes is the precise
inversion of that claim, and a judge can trigger it by unplugging the wifi.

### 7.3 ⚠ Silent degradation when the embedding model is unavailable

Before the sentence-transformer finished loading, two identical S1 requests in
one process returned `ABSTAIN_INSUFFICIENT_EVIDENCE`; later requests in the same
process returned `VERIFIED_TEMPLATE / HIGH`. Same input, different answer, no
user-visible difference in kind. `RetrievalMode.BM25_ONLY` exists and would have
degraded gracefully; nothing selects it.

### 7.4 ⚠ The human-in-the-loop closes nothing

- `resume_review(..., {"outcome": "accept"})` returns terminal
  **`REVIEW_REQUIRED`** — the same terminal as before the decision. Accepting and
  rejecting are indistinguishable in the run's outcome.
- The decision is stored on graph state and in the checkpoint, but **nothing
  records it durably**: `feedback/store.py` is imported by `tests/` and nowhere
  else. `grep -rn "from feedback"` across `graph/` and `ui/` returns nothing.
- Consequence for the pitch: `judge_defense.md` says the loop is *"implemented
  and wired"*. It is implemented and **not wired**. A judge who greps finds that
  in ten seconds, and it costs the one thing you cannot afford to lose — the
  audience's belief that your claims are exact.
- A second `resume_review` on a completed thread is accepted without complaint.

### 7.5 ✅ What held up impressively

- **Every malformed-model attack failed closed.** A model asserting a 99.9% drop
  with a fabricated citation never reached the screen.
- **Bundle hash identical across interrupt/resume.** The demo beat is real.
- **Access denial is fast, typed and audited** — 0.1 s, before any analysis.
- **Type boundaries catch nonsense early** — an inverted window never enters the
  graph.
- **Sparse history produces the best abstention screen I have seen in a student
  project**: days available, days required, and how long to wait.

---

## 8. Backlog

Every item: current problem · why a competitor beats you here · user value ·
judge value · complexity · time · regression risk · files.

### P0 — before submission

**P0-1 · Thread-safe database access**
- *Problem:* one shared DuckDB connection; concurrent sessions cross result sets
  and defeat row-level entitlement (§7.1).
- *Competitors:* an enterprise-BI archetype gets this free from the platform.
- *User value:* correctness under the most ordinary condition imaginable — two
  people using the app.
- *Judge value:* very high. Converts your most breakable claim into a regression
  test, and gives you a story: *"we tested concurrency, found it, fixed it, and
  here is the test."*
- *Complexity:* low. *Time:* 1–2 h including the test. *Regression risk:* low —
  a per-thread cursor is DuckDB's documented pattern and I verified it end to end.
- *Files:* `semantic/gateway.py` (`connect`, `guarded_query`, `documents`,
  `schema_changes`); new `tests/test_concurrency.py`.

**P0-2 · A system failure must not be narrated as an abstention**
- *Problem:* node crashes are laundered into `ABSTAIN_INSUFFICIENT_EVIDENCE` with
  a false explanation (§7.2).
- *Competitors:* nobody else claims honest failure, so nobody else is *vulnerable*
  to this. It is a self-inflicted wound.
- *User value:* an analyst stops chasing a data-coverage problem that does not
  exist. *Judge value:* very high, and cheap.
- *Complexity:* low. *Time:* 1–2 h. *Regression risk:* low.
- *Files:* `graph/routing.py::route_sufficiency` (route `"error"` separately);
  `graph/types.py` (add e.g. `SYSTEM_ERROR` to `TerminalState` and
  `SILENT_TERMINALS`); `graph/nodes.py` (a terminal node that reads
  `state["error"]`); `ui/components/abstention.py` (a renderer saying *"the
  analysis could not complete — retrieval was unavailable"*, detail in Audit);
  `tests/test_graph_failures.py`.

**P0-3 · Make a warm run fast (parallelise / cache the forecast cube)**
- *Problem:* 93% of a 17 s run is 288 serial robust STL fits (§6). Two documents
  claim the app runs a 400-resample bootstrap; the graph passes 30; the demo
  script claims 4 s warm and it is 17 s.
- *Competitors:* every LLM-first competitor answers in two seconds. Latency is the
  most visible quality signal in a live demo.
- *User value:* very high. *Judge value:* high — and it removes the presenter's
  need to talk over a spinner.
- *Complexity:* medium-low. *Time:* half a day for pool + cache; add 2 h to
  evaluate `robust=False` for cube cells (requires a before/after table across all
  eight scenarios).
- *Regression risk:* **none** for parallelisation and caching (identical
  arithmetic); **medium** for the `robust` flag — do that last, or not at all.
- *Files:* `attribution/engine.py::build_forecast_cube`; `graph/nodes.py`
  (`n_resamples=30` should come from config, not a literal);
  `eval/complexity_audit.md` and `eval/final_telemetry_report.md` (correct the
  bottleneck attribution — *publishing the correction is worth more than the
  speed-up*); `eval/final_demo_script.md` (fix "~4 s").

**P0-4 · Run the LLM once, for real**
- *Problem:* zero live model calls in the entire project. Every narration claim is
  validated against fakes. `eval/run_llm_eval.py` is written and unrun.
- *Competitors:* every one of them will have run their model. In an *AI*
  innovation challenge, "we never called the model" is your most quotable
  weakness.
- *User value:* the product's prose stops being a template. *Judge value:*
  enormous — it converts seven `LIVE LLM EVALUATION PENDING` rows into
  measurements and lets you say *"we ran a live model against Gate 2 N times; here
  is the first-pass rate and here is what it tried to slip past."* If the model
  **fails** a check on a real run, that is your best slide, not your worst.
- *Complexity:* trivial (one key). *Time:* 1 h. *Cost:* cents.
- *Regression risk:* low — but rehearse the demo in template mode regardless;
  never put a network call on the critical path of a live pitch.
- *Files:* none. Run `python -m eval.run_llm_eval`; update
  `eval/final_telemetry_report.md`, `eval/final_evaluation_report.md`,
  `eval/claim_audit.md`, and slides 09/10.

**P0-5 · Close the human-in-the-loop**
- *Problem:* accept and reject produce the same terminal; the decision is never
  recorded; `judge_defense.md` claims the loop is "wired" when nothing calls
  `feedback.store.record` (§7.4).
- *Competitors:* nobody will have a real interrupt/resume. You are currently
  under-selling *and* over-claiming the same feature — the worst combination.
- *User value:* the analyst's decision has a consequence. *Judge value:* very high
  — *"watch the calibration counter go from 12 to 13 because I clicked Accept"* is
  a closing beat no competitor can match.
- *Complexity:* low-medium. *Time:* 3–4 h. *Regression risk:* low; the
  terminal-state change touches `SILENT_TERMINALS` and UI routing, so test all
  four outcomes.
- *Files:* `graph/nodes.py::human_review` (map the four outcomes to distinct
  terminals or a `review_outcome` field); `graph/types.py`; `feedback/store.py`
  (actually call `record`); `ui/components/review.py` (confirm the recorded
  outcome and show the updated counter); `eval/judge_defense.md` (correct the
  claim *regardless* of whether the rest ships).

### P1 — materially improves shortlist odds

**P1-1 · A question composer (not a chat box)**
- *Problem:* `ui/state.py:139` hardcodes `kpi_id="net_revenue"`; the eight
  scenarios are a fixed import from `eval/`. A judge cannot ask a second question.
  Six KPI contracts exist and every layer is parameterised — the capability is
  built and unreachable.
- *Competitors:* this is the generic-copilot archetype's entire advantage.
- *User value:* high. *Judge value:* very high — the difference between a *demo*
  and a *product*.
- *Complexity:* medium (guardrails matter: the pre-computed scenarios stay the
  default and an ad-hoc run must show that it is ad-hoc). *Time:* 1 day.
- *Regression risk:* medium — untested slices find untested paths (probe #4 took
  102 s on the whole market). Ship with P0-3, or behind a "may take longer" notice.
- *Files:* `ui/state.py`; `app.py` (sidebar); new `config/scenarios.yaml`;
  `ui/components/movement.py`.

**P1-2 · The KPI time-series chart**
- *Problem:* there is no chart of the metric. The only chart is a driver
  waterfall. The STL counterfactual, the changepoint and the event window are all
  computed and all invisible.
- *Competitors:* every UX-led competitor will have a chart. This is the visual the
  category is defined by.
- *User value:* very high — recognition beats recollection, which is the research
  the rest of this UI is built on.
- *Judge value:* very high per hour: one figure makes STL, PELT and the
  counterfactual *visible* instead of asserted.
- *Complexity:* low — `result.detection.decomposition` already carries `observed`,
  `dates` and the baseline curve; Plotly is already a dependency.
- *Time:* 3–4 h. *Regression risk:* very low (presentation only; `ui/safe.py`
  already isolates a panel failure).
- *Files:* new `ui/components/series.py`; `app.py::workspace_tab`;
  `tests/test_ui.py`.

**P1-3 · Cache results per (scenario, persona)**
- *Problem:* one `st.session_state["result"]` slot; every scenario or persona
  switch re-runs from scratch (§6).
- *Judge value:* moderate; *demo* value high. *Complexity:* trivial. *Time:*
  30 min. *Risk:* low — key the cache on the same fields `stale` already compares.
- *Files:* `ui/state.py`, `app.py`.

**P1-4 · Derive `history_days` / `has_stable_baseline` from detection**
- *Problem:* two inputs that gate lever eligibility are hardcoded per scenario id
  in five places, one of them the UI (`ui/state.py:146`).
- *Judge value:* high if found — it undercuts "the UI computes nothing".
- *Complexity:* low. *Time:* 2 h. *Risk:* low-medium (lever eligibility may shift
  on S4; diff the eight-scenario table before and after).
- *Files:* `graph/nodes.py::rank_hypotheses`; `evidence/bundle.py`;
  `ui/state.py`; five `eval/*.py` call sites; `tests/test_evidence.py`.

**P1-5 · Calibrate materiality for the other four KPI contracts**
- *Problem:* only `net_revenue` has a measured null distribution (ADR-017).
- *Judge value:* high — turns a stated limitation into a table.
- *Complexity:* low (machinery exists). *Time:* half a day including the run.
- *Files:* `semantic/kpis/*.yaml`; `eval/run_detection_eval.py`; a new ADR.

**P1-6 · Re-seed calibration with the demo slices held out**
- *Problem:* the "12 of 12" beside S1 was computed over a universe that includes
  S1's own slice (§5.3).
- *Judge value:* high — this is the attack I would run.
- *Complexity:* low. *Time:* 2 h. *Risk:* the numbers may get worse, which suits
  your evidence-discipline narrative.
- *Files:* `eval/seed_calibration.py`; `config/calibration.json`;
  `ui/components/confidence.py` (one caption line); `eval/claim_audit.md`.

**P1-7 · Prompt-injection defence and test**
- *Problem:* untrusted document text enters the prompt undelimited; no test; not
  mentioned in the security audit (§5.7).
- *Judge value:* high — a 2026 judge will ask. *Complexity:* low. *Time:* half a
  day.
- *Files:* `llm/payload.py` (delimit and label excerpts as untrusted data);
  `tests/test_llm.py`; `eval/security_audit.md`.

**P1-8 · Advisory entailment check in Gate 2**
- *Problem:* Gate 2 verifies references, not meaning (§5.5).
- *Judge value:* high — answers the sharpest verification question with a
  mechanism rather than a concession.
- *Complexity:* medium-low; reuse the loaded embedding model, `INFO` severity
  only, never blocking. *Time:* half a day. *Risk:* low if advisory-only.
  Requires an ADR.
- *Files:* new `verification/entailment.py`; `verification/engine.py`;
  `verification/types.py`; `docs/DECISIONS.md`.

**P1-9 · Graceful retrieval degradation**
- *Problem:* dense failure crashes the node instead of falling back to
  `BM25_ONLY` (§7.3). *Complexity:* low. *Time:* 2 h.
- *Files:* `retrieval/engine.py`; `tests/test_retrieval.py`.

**P1-10 · Pre-flight script and pinned dependencies**
- *Problem:* the demo depends on a HuggingFace fetch on a cold machine, and
  `requirements.txt` uses `>=` for statsmodels, scipy, streamlit, plotly,
  sentence-transformers and rank-bm25, so a fresh clone in two months may not
  reproduce. *Complexity:* trivial. *Time:* 1 h.
- *Files:* new `scripts/preflight.py`; `requirements.txt`; `docs/DEPLOYMENT.md`;
  `README.md`.

### P2 — optional

- **P2-1** Sensitivity band in the UI: *"this decision flips if p_human > 0.93"* —
  `eval/sensitivity.py` already has the machinery.
- **P2-2** Surface the DiD control choice (chosen control, pre-period correlation,
  runners-up) in Method; `considered` is computed and discarded.
- **P2-3** Adversarial event shapes in the generator (slow ramp, reversing step,
  seasonal-amplitude change); report whatever recall results.
- **P2-4** Hand-label 20 retrieval pairs and report agreement with the generated
  labels.
- **P2-5** Move `SCENARIOS`/`PERSONAS` into `config/scenarios.yaml` so `ui/` stops
  importing `eval/`.
- **P2-6** Fix the evidence card that renders with the literal heading "Evidence"
  for CRM notes (visible in `scripts/_walkthrough_out/S1.txt`).
- **P2-7** Refresh `eval/round2_traceability.md` — it still says DEL-1 and DEL-3
  are "not built"; both now exist under `submission/`.
- **P2-8** Emit OpenTelemetry spans from `NodeTelemetry` (it is a span already,
  minus serialisation).

---

## 9. Product and UX gaps

### 9.1 What the backend has and the UI does not say

| Capability (built, tested) | UI today | Exact change |
|---|---|---|
| STL counterfactual, changepoint date, event window | prose only | **The chart (P1-2).** Observed line, dashed counterfactual, shaded event window, a marker at the changepoint. One figure carries detection, decomposition and quantification at once |
| `SourceReconciliation` — S1 vs S2 −4.45% (population), S1 vs S3 (definition) | not surfaced | One Method line: *"Sessions differ −4.45% between S1 and S2 (population, not definition); not used in the identity"*. This is the heterogeneous-sources requirement made visible |
| DiD control selection (chosen control, correlation, candidates) | one chip | Method: *"Control: region=North, pre-period r = 0.87; two other candidates considered"* |
| `p_human` / decision-value sensitivity | absent | P2-1's one-line band under the recommendation |
| Withheld-evidence count | ✅ good | Add *which source type* was withheld where policy permits — you already allow the source name |
| Confidence provenance | ✅ excellent | Add *"comparable cases exclude this slice"* once P1-6 lands |
| Node failures | Audit only | P0-2 puts the honest sentence on the Workspace |
| Bundle hash / auditability | Audit tab | Put the hash **next to the narrative** as a small monospace chip — your freeze story in eight characters |
| Recommendation scope (request vs approve) | ✅ excellent | No change. The best line in the product |

None of these adds a decision to the screen; each replaces an assertion with a
visible artefact. That is the right trade for this product's cognitive budget.

### 9.2 The single missing interaction

Not chat. Not more agents. **"Ask about something else."**

Today the product answers exactly eight pre-composed questions about one KPI. A
decision-support product must let a user change *what* is being examined — KPI,
window, slice — without a developer. Every layer already accepts those three
parameters; only `ui/state.py` withholds them.

Implement it as a **structured composer, not a text box**: three dropdowns
(KPI × window × slice) and a Run button. That keeps ADR-006's rejection of chat
intact — the user still cannot ask the model an unbounded question — while
removing the impression that the demo is a recording. Pair it with a second-order
feature that costs almost nothing: *"run this same question as a different
persona"* side by side, which makes the entitlement story interactive instead of
narrated.

If only one P1 ships, ship the chart (P1-2). If two, add the composer (P1-1).

---

## 10. Build quality

Assessed as if inherited tomorrow. Cosmetic issues excluded.

**Genuinely good:** zero circular imports; every module docstring states what it
is *not* responsible for; ADRs record failing cases rather than intentions; tests
assert behaviour by causing faults; vacuous tests are treated as defects. This is
better than most production codebases.

| Issue | Severity | Detail |
|---|---|---|
| Shared mutable DuckDB connection | **Critical** | §7.1. `_lock` guards creation, not execution |
| Node cascade after a failed predecessor | High | One fault records three failures and a wrong terminal (§7.2) |
| `n_resamples=30` hardcoded in `graph/nodes.py::attribute` | Medium | A business-logic constant in the workflow layer; the module default is 400; `ui_walkthrough.md` and `antigravity_ui_qa.md` both describe the app as running a **400**-resample bootstrap. Three different stories |
| `history_days` / `has_stable_baseline` hardcoded by scenario id in 5 files | Medium | Duplicated logic *and* a hidden coupling from `ui/` into lever eligibility |
| `ui/` imports `eval/run_recommendation_eval` | Medium | Shipping code depends on the evaluation harness at import time |
| `feedback/` is dead at runtime | Medium | Only `tests/` import it; documentation says "wired" |
| Unpinned deps (`>=`) for six packages | Medium | Reproducibility risk for a judge cloning later |
| Runtime HuggingFace fetch | Medium | Demo-fatal on a cold offline machine; five retries with backoff before it gives up |
| `warm_up()` written, never called | Low-medium | The 36 s load lands on the user's first click instead of at app start |
| SQL string interpolation of `user_region` | Low today | `security/entitlements.py:141`; safe with a fixed persona dict, unsafe the day it meets an IdP claim |
| Docs drift | Low | `round2_traceability.md` says DEL-1/DEL-3 unbuilt; `final_demo_script.md` says warm ≈ 4 s (measured 17 s); `complexity_audit.md` names the wrong bottleneck |
| Test suite 13 min locally / 5 min in CI | Low | Acceptable; the slow half is fixture-bound |

**Not found (checked):** hardcoded secrets, PII on any reachable path, dead
runtime branches beyond `feedback/`, unsafe `eval`/`exec`, mutable default
arguments, bare `except:` without a recorded reason, brittle literal-count
assertions (one existed and was already fixed).

---

## 11. Build / don't build

Default skepticism applied. Every "don't build" is also a *pitch asset*, because
a rejection with a reason is stronger than a feature without one.

| Item | Verdict | Reason |
|---|:---:|---|
| Knowledge graph | **Don't build** | The star schema already models the entity relationships; a KG would restate the warehouse. ADR-005's argument holds |
| GraphRAG | **Don't build** | Solves multi-hop reasoning over unstructured corpora. Your hops are structured joins SQL already does. Adding it would be the clearest possible signal of trend-following |
| Multi-agent | **Don't build — and campaign against it** | ADR-009. The absence *is* the differentiator. Put the argument on a slide |
| Fine-tuning | **Don't build** | ADR-010. 87 examples; the failure mode is grounding, not style |
| Causal discovery (PC/NOTEARS) | **Don't build** | Unidentifiable with four dimensions and six events. A wrong DAG asserted confidently is your thesis in reverse. Name it as considered-and-rejected |
| Forecasting | **V2** | Genuinely useful ("is this recovering?"), genuinely out of scope now. The STL counterfactual is already 80% of the machinery |
| Real-time streaming | **Don't build** | No trigger. The case is diagnostic, not operational alerting |
| Vector database | **Don't build** | ADR-004. 2 MB of floats. The *security* trigger (per-tenant isolation) is the honest one and it is already documented |
| Model routing | **V2** | `config/models.yaml` already has routes; the cost case cannot be made before P0-4 measures anything |
| More LLMs | **Don't build** | Two models is two unvalidated surfaces. You have not validated one |
| Automated actions (executing levers) | **Don't build** | The request-not-execute boundary is your best commercial idea. Executing destroys it |
| External live data | **Don't build** | A live feed adds a network dependency to a demo that already has one too many |
| **Synthetic control (DiD upgrade)** | **V2, name it** | The right answer to "why one control?" Mention as the upgrade path; do not build |
| **Advisory entailment check** | **BUILD (P1-8)** | The one genuinely new mechanism worth adding: it closes the sharpest hole in Gate 2 and costs ~5 ms |
| **Concurrency safety** | **BUILD (P0-1)** | Not a feature. A defect |

---

## 12. Competitive moat

The moat is **not** LMDI, not Adtributor, not the graph. Each is a weekend for a
strong engineer. The moat is the **composition**, and specifically four
properties that only work together:

1. **A closed evidence set with an identity.** The bundle is frozen *and* hashed
   *and* the only input to narration *and* the referent every check resolves
   against. Any one alone is a feature; the four together mean a claim can be
   checked against a *closed set* rather than against "the data". A competitor
   copies the freeze in a day and still does not have the checks that resolve
   against it.

2. **A licence, not a score, for causal language.** `causal_language_licensed` is
   produced by a tested statistical assumption, carried through hypothesis
   ranking (ADR-023 narrows it to `SUPPORTED` hypotheses), enforced by a
   deterministic check, and rendered as a chip. Four layers agree on one boolean.
   Copying the DiD is easy; copying the plumbing that makes a model unable to
   override it is where the weeks go.

3. **Entitlement upstream of ranking, proved by a leak chain with a non-vacuity
   control.** The ordering argument — a restricted document that reaches the
   ranker has already influenced the answer — is one most teams have never
   considered, and the control that proves the test is not vacuous is a technique
   most professionals do not use. **Once P0-1 lands**, this is the hardest item
   on the list to reproduce.

4. **Failure behaviour as designed product.** Eleven typed terminals, each with
   its own screen, its own copy and its own reason, plus a real interrupt on a
   durable checkpoint whose bundle hash survives the pause. Competitors will have
   a try/except and a toast.

Add the fifth, which is not code: **the audit trail of your own mistakes.** The
STL trend leak, the mixed-source identity closing to 94.8%, the weighted sum with
0.000 spread, the post-selection p-value, the 13-template corpus, the template
that failed its own gate. Nobody reproduces that in a fortnight, because it is
the record of having actually built the thing.

### How to say it in the pitch

Do not present the moat as a list of algorithms — that invites a
feature-by-feature comparison you can lose. Present it as **one chain, and
challenge the room to break a link**:

> "Every number is computed, and it is frozen and hashed before a word is
> written. The model sees only that frozen object, has no tools, and has no field
> to write a confidence into. Ten deterministic checks resolve every claim back
> against the hash. The word *caused* requires a counterfactual that passed a
> parallel-trends test. Restricted evidence is removed before ranking, not after.
> And when the chain does not hold, the system stops and says which link failed.
> Break any one of those and the others still hold — that is the point."

Then land the sentence no competitor can say: **"Our own verifier blocked our own
fallback template, and we shipped the fix rather than the excuse."**

---

## 13. Final assessment

**Overall competition readiness: 8.1 / 10.** Top-decile submission; three small
defects and one missing chart separate it from top-percentile.

**Biggest strength.** Trust made mechanical. Not "we prompt carefully" — a frozen
hashed bundle, an absent `tools` key, a missing `confidence` field, eleven
deterministic checks, a causal licence, and an abstention taxonomy with its own
screens. Nobody else in a 600-team field will have built the *guard* before the
thing being guarded.

**Biggest weakness.** The system has never been run under the two conditions a
real deployment guarantees: **a second concurrent user** (which breaks the
entitlement guarantee, §7.1) and **a live language model** (which has never
executed once). Both are hours of work, not weeks.

**Highest-leverage improvement.** P0-3 + P1-2 together: make a warm run ~3 s and
put the KPI chart with its counterfactual on the Workspace. One working day, zero
architectural risk, and it fixes the two things a judge *feels* in the first
thirty seconds — speed, and the absence of the visual this category is defined
by. P0-1 matters more *in principle*; P0-3 + P1-2 change more minds.

**Exact top-5 recommendations, in order**

| # | Do this | Time | Why it is in the top five |
|---|---|---|---|
| 1 | **P0-1** per-thread DuckDB cursor + concurrency test | 1–2 h | Restores the flagship guarantee; verified fix; turns the hardest question into a prepared answer |
| 2 | **P0-3** parallelise/cache the forecast cube, correct the bottleneck docs | ~1 day | 17 s → ~3 s; and publishing the correction to your own performance analysis is worth more than the speed-up |
| 3 | **P1-2** the KPI time-series chart with counterfactual and event window | 3–4 h | Closes the only gap a UX-led competitor can beat you on, and makes STL/PELT visible instead of asserted |
| 4 | **P0-4** run the live model once and publish the numbers | 1 h | Removes "we never called the model" from an AI competition; converts seven PENDING rows into measurements |
| 5 | **P0-2 + P0-5** honest system-error terminal, and close the review loop | ~5 h | Protects the abstention claim from a crash impersonating it, and makes the human-in-the-loop *do* something on stage |

**What NOT to touch.**
- The deterministic/AI boundary. Nothing about it.
- The freeze boundary and the bundle hash.
- Gate 2's design (checks on the structured claim, not the prose) — only *add* an
  advisory check beside it.
- Entitlement-before-ranking ordering.
- The abstention taxonomy and its screens.
- The decisions to have no chat box, no agents, no vector DB, no fine-tuning.
- The self-critical documents. `claim_audit.md` and `data_realism_audit.md` are
  competitive assets; do not soften a sentence in them.
- The eight-scenario harness as the default path — add a composer *beside* it,
  never instead of it.

**What a top competitor will do better.**
- **Speed and interactivity.** Two-second answers to arbitrary questions.
- **Visual polish.** A designed frontend, live charts, motion.
- **Apparent AI depth.** Agent diagrams, streaming reasoning traces, a "critic
  agent" that sounds like your Gate 2 and is not.
- **A confident ROI number.** They will assert a time saving; you will not, and on
  the business slide that costs you — right up until someone asks how they
  measured it.

**What you can do that they probably will not.**
- Break your own system on stage: unplug retrieval and show a *correctly labelled*
  failure (after P0-2).
- Show the gate blocking your own template.
- Resume a paused run and show the bundle hash is byte-identical.
- Show a number above 100% and explain why that is arithmetically correct.
- Show two personas reading the same event with a *counted* withheld-evidence
  notice.
- Publish a claim audit listing every number you refuse to state.
- Say out loud: *"we deliberately removed the agents, and here is the failing case
  that made us."*

None of that requires a better model. All of it requires having built the thing
carefully — which, with the P0s closed, you demonstrably have.

---

### Appendix — reproducing this audit's measurements

All probes ran from a scratch directory with `PYTHONPATH=.` and made no
repository changes.

| Probe | Established |
|---|---|
| 1 | Bad-request taxonomy: eight malformed requests, seven typed terminals, one slow path (102 s on an unknown dimension) |
| 2 | Malformed / fabricating / raising narrators all fail closed to `VERIFIED_TEMPLATE` |
| 3 | Repeated identical runs are deterministic once warm |
| 4 | Retrieval and warehouse outages both surface as `ABSTAIN_INSUFFICIENT_EVIDENCE`; resume preserves the bundle hash; accept/reject do not change the terminal |
| 5 | Warm latency profile: S1 17.6 s / 16.7 s, attribution 93–95% of it |
| 6 | cProfile: 288 `decompose` calls = 14.1 s; bootstrap = 0.63 s |
| 7 | STL cost: `robust=True` 75.7 ms vs `robust=False` 11.6 ms per call |
| 8 | Six concurrent gateway readers: five errors, row counts {0, 1616, 3664} for one query |
| 9 | **Cross-principal leakage**: `ops_lead` received 916 rows spanning all four regions |
| 10 | **Verified fix**: per-thread cursor ⇒ 36 reads, 0 errors, 0 violations, correct shapes |

*Independent technical audit · no repository code modified · all figures measured
on this machine unless attributed to an existing `eval/` report.*
