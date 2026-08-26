# Pitch — speaker notes

Talk track for `R2_PITCH_DECK.md`.

---

## How this file relates to the demo script

There are two performances, and they must not be confused.

| | **This file** | **`eval/final_demo_script.md`** |
|---|---|---|
| What it drives | The slides | The **running application** |
| Length | 5–7 min, or a 3-min cut | Exactly 3:00 |
| Content | Problem, architecture, evidence, readiness, ask | S1 end to end, then S2 refusing to guess |
| Authority | Authoritative for slide narration | **Authoritative for the live demo. Nothing here overrides it** |

**If the format allows a live demo, run the demo script unmodified and replace
Slides 03, 05, 06 and 07 with it** — those four slides are exactly what the demo
shows, and showing the product beats describing it. Keep Slides 01, 02, 04, 08,
09, 10, 11 as the frame around it. The mapping is at the end of this file.

**If the format does not allow a live demo,** run the slides straight through
using the beats below. Do not paraphrase the demo script here — it describes
screens that will not be on the projector.

---

## Delivery rules — carried forward from the Round 1 video script

These held at 135 words per minute in Round 1 and still hold.

- **Say numbers as words.** "Twenty five percent." "Zero of ten." "Nine of nine."
- **Do not read citations aloud.** "A twenty twenty six audit" is enough. The arXiv reference is on the slide for anyone who wants it.
- **Three lines carry the whole pitch.** Give each a clear beat before and after:
  1. *"The narration request has no tools key. Absent, not empty."*
  2. *"The gate blocked our own template."*
  3. *"Two of eight scenarios end with no recommendation at all."*
- **Volunteer the limitations before anyone finds them.** Every limitation in this deck reads as confidence when you say it first and as spin when a judge says it first. This is the single highest-leverage delivery instruction in the file.
- **Never say** "accurate", "production-ready", "enterprise-ready", "real-time", or "autonomous". The system is none of those and the deck says so. Say "measured on synthetic data" and "prototype".

---

# Slide-by-slide

## Slide 01 — The gap has not moved (0:00–0:40)

> "A dashboard says net revenue in the West fell. It will not say why — and that
> is not a tooling gap that got fixed while we were building. Seventy three
> percent of BI implementations fail on the diagnostic gap rather than on
> technology. About twenty one percent of employees actually use the dashboard.
>
> And the labour is not free. Roughly seventy percent of analyst time goes to
> investigating alerts that turn out to be legitimate, and past thirty alerts a
> day, detection accuracy falls twenty two percent. The tool that fires on
> everything trains people to ignore it."

Point at the flow row, do not read it.

> "That is the path a leader lives today. Four tools, two days, and a narrative
> with no ranking and no stated confidence."

**Land this and move.** The problem is not the interesting part of this pitch.
Forty seconds, maximum.

**If asked for the customer research:** Round 1 scraped and coded a corpus of G2,
Capterra and Reddit reviews on the leading BI tools. Eighteen percent say you need
an expert; thirteen percent describe manual digging; **0.6% ever use the words
"root cause."** People are not asking for RCA — they are complaining about the
labour that replaces it. That finding is in `docs/ROUND1_MASTER.md` §9.

Two cautions before you use it. It is deliberately **not** a slide claim in Round 2,
because this deck restricts its numbers to the proposal's evidence file. And Round 1's
own materials give the corpus size as both **314** and **384** in different places, so
**quote no total** — give the percentages and say it is Round 1 research that Round 2
did not re-verify.

---

## Slide 02 — The obvious fix is the dangerous one (0:40–1:15)

This slide exists to kill one question before it is asked.

> "The obvious answer is to point a language model at the warehouse. Here is why
> we did not.
>
> A twenty twenty six fidelity audit gave a model the evidence and asked for a
> credit-risk narrative. It inverted the risk direction on three of four
> factors. Its priors overrode the evidence it was handed — under constrained
> prompting.
>
> And the models best at multi-step causal reasoning are measurably worse at
> knowing when to stay quiet. AbstentionBench measured reasoning-tuned models
> abstaining twenty four percent worse than their non-reasoning counterparts."

**Pause here.** Then the inference:

> "So the capability you want for root-cause analysis actively works against the
> humility you need. Gartner has a name for the result — agent drift — and
> prescribes guardian layers.
>
> That is not a feature you add at the end. It is where you start."

---

## Slide 03 — One engine, from a number to a decision (1:15–2:00)

Show the screen. Let it sit for two seconds before speaking.

> "Five stages. Detect, Attribute, Explain, Recommend, Verify. One screen.
>
> Net revenue in West on Web and Mobile, down twenty five percent over two
> weeks. The chip says **material** — that is not a threshold on the percentage,
> it is a business rule with a statistical leg and a business leg. Most
> movements never get here.
>
> Conversion rate is the driver. Notice it says it accounts for **more than the
> whole movement** — one hundred and nine point nine percent — because sessions
> actually rose and partly offset it.
>
> Eight documents corroborate, and two of them are on the screen — the count is
> not asked to be taken on trust. Reliability is a track record, not a score, and
> the caveat that those cases are synthetic is in the same block, not a
> footnote. And the action names an owner, a monitoring metric and a review
> window."

Then the framing line:

> "There is no chat box, and that is deliberate. A conversational surface invites
> the user to ask the model questions it must not answer, from data it must not
> reach."

**Then point at the red card on the right — do not skip this even under time
pressure.** It is the earliest moment a judge can tell this is not a BI copilot,
and the product/judge audit found the pitch was previously waiting until Slide 05
to say it.

> "And one thing to hold on to before we go further: this screen is what you get
> when the evidence agrees. When it doesn't, you don't get this screen at all.
> I'll show you that in two minutes."

---

## Slide 04 — Round 1 promised this. Round 2 runs it, and corrects it. (2:00–2:30)

**Judges who saw Round 1 will remember the promises. Say the changes before they
check.**

> "Round 1 was a concept deck. This is what survived contact with an
> implementation.
>
> Kept: five stages, the materiality gate, two gates not one, escalation as a
> cost rule rather than a threshold. Those all run.
>
> Changed: we said confidence zero point eight two. The system now has nowhere
> to write a confidence — the type has no such field. It reports a calibrated
> band and a track record instead, and it reports **uncalibrated** where it has
> fewer than ten observed cases.
>
> We said CUSUM and Bayesian online detection. We built neither. We said
> conformal prediction. We built cost-sensitive deferral instead.
>
> Four of five changes made the claim smaller. That is what having a working
> system does to a pitch."

**If time is tight, this is the second slide to cut.** It only lands with judges
who saw Round 1.

---

## Slide 05 — Every number is computed, never generated (2:30–3:10)

This is the technical spine. Slow down.

> "The central claim is one sentence: every number a user sees is computed by
> SQL, statistics or a business rule. The model writes the sentence and nothing
> else.
>
> Detection is decomposition, a robust z-score and changepoint detection.
> Attribution is an exact index decomposition — it closes to zero to nine
> decimal places, so it is an identity, not a fit. Localisation is Adtributor.
> Causal testing is difference-in-differences with a parallel-trend check.
> Routing is pure functions over deterministic state.
>
> The model sees a frozen, hashed evidence bundle. It has no database access.
> **The narration request has no tools key — absent, not empty.** A model that
> cannot query cannot fabricate a query result."

**Pause.** Then the proof:

> "And the cheapest available proof that the numbers are computed is on the
> previous slide. One hundred and nine point nine percent. No language model
> generates a self-explaining share above one hundred percent."

**If asked how you know:** two tests. One asserts the absence of the tools key
against the **recorded request**, not the code that builds it. The other asserts
that no routing predicate reads model output against the predicate **source** —
a predicate that started consulting the narrative would pass every behavioural
test and still fail that one.

---

## Slide 06 — Nothing ships unverified (3:10–3:50)

> "Two gates. Before generation, a sufficiency check — thin or stale evidence and
> it says so rather than writing around it. After generation, ten deterministic
> checks against the frozen bundle: every figure, every driver, every citation,
> and whether the causal wording was licensed.
>
> Zero false acceptances across ten hand-built corrupt narratives. Zero false
> rejections across six valid ones. Nine of nine injected violations caught by
> the check we expected to catch them.
>
> And the honest version of that: none of *those* ten got through. That is not
> the same as saying none could."

**Then the line that wins the technical judge:**

> "The strongest evidence that the gate is real is that it blocked **our own**
> fallback template. A bug made the template cite two evidence ids the frozen
> bundle no longer held, and the gate rejected it. We had documented that
> template as unfailable by construction. It was unfailable by luck. We fixed
> both the builder and the docstring.
>
> A gate that only ever passes what we produce is not a gate."

**On causal language:**

> "The word *caused* is licensed, not asserted. A difference-in-differences test
> with a parallel-trend check decides whether the system may use it. On one demo
> scenario the licence is denied and the wording degrades to *association only*
> — in the interface, not in a log. And to be precise: that test licenses
> **wording**, not **truth**. It assumes no unobserved confounder affecting only
> the treated slice."

---

## Slide 07 — It declines (3:50–4:30)

**The beat that wins the room. Do not rush it.**

> "Across eight scenarios the system automates four, routes two to a human, and
> declines two.
>
> It declines for three different reasons. In one, two explanations are equally
> supported and they imply **different owners** — one is a pricing problem, one
> is a supply problem. Guessing does not just risk a wrong answer; it sends the
> wrong team. So the system stops, states the question, and hands it to a
> person.
>
> In another, a new category has fifty two of the fifty six days a seasonal
> baseline needs. It will not extrapolate. It tells you how long to wait — a
> refusal is actionable when it says what would change its mind.
>
> In the third, a channel rename looks like almost six percent growth.
> Statistically real, commercially meaningless. No alert, no recommendation, no
> invented cause. That is the alert-fatigue answer."

**Then the two credibility details:**

> "The pause is real, not a message. The workflow interrupts on a durable
> checkpoint, and resuming produces the same run with an identical evidence
> hash — so the analyst's decision attaches to exactly what they reviewed.
>
> And notice it limits its own claims. Only the high band has enough observed
> cases to quote a rate. The others report **uncalibrated**. On that ambiguous
> case, the cost arithmetic that would justify automating is not available — it
> could not automate it even if it wanted to."

Close on the band:

> "A system that always answers cannot be trusted on the answer it gives."

---

## Slide 08 — Who may see what, and who may do what (4:30–5:00)

> "Three personas, and the differences are real rather than cosmetic. The
> operations lead is denied CRM notes — and the system tells her **how many**
> items were withheld. A silently shorter list would be worse than a refusal.
> The finance director carries a higher configured decision value, so the same
> evidence can route differently for him than for her."

**Then the point enterprise buyers actually care about:**

> "Read the button. It says **raise the request**. It does not say roll back.
>
> That persona holds request rights on this lever, not approval rights. So what
> gets automated is raising an engineering request. Executing a rollback is a
> different lever, no persona in this system can approve it, and it sits on a
> never-automate list.
>
> The real enterprise fear is not a wrong explanation. It is a correct
> explanation wired to the wrong action."

**And volunteer the gap:**

> "Entitlement is applied before ranking, not after — a restricted document that
> reaches the ranker has already influenced what you see. Thirty two security
> tests, a six-stage leak chain with a non-vacuity control, zero restricted
> items reaching any stage.
>
> But there is no authentication. Persona is a dropdown. Authorisation is real
> and tested end to end; identity is not. That is fine for a local prototype and
> unacceptable with real data, which is why enterprise identity is priority one
> on the roadmap — triggered by *before any real data*, not by a user count."

---

## Slide 09 — What we measured, and what we refuse to claim (5:00–5:40)

> "Every number in this deck carries a label: measured, synthetic evaluation,
> research-sourced, assumption, or illustrative.
>
> Measured: five hundred and seventy four tests passing. Eight of eight
> scenarios end to end. And the orchestration layer changed no decision — the
> graph agrees with the direct module path on all eight.
>
> Synthetic: detection precision and recall are both one point zero. Here is the
> honest reading of that. Recall of one means every event **we injected** was
> found, and we built those events to be detectable by this method's
> assumptions. The figure that is not guaranteed by construction — and therefore
> the only meaningful one — is **zero false positives across forty eight clean
> slices**."

**Then the slide's real purpose:**

> "The result we are proudest of is a set of numbers that got worse.
>
> A realism audit found our document corpus held thirteen distinct texts across
> nearly nine hundred records. Retrieval was closer to a lookup than to search.
> We widened it, and every retrieval score fell — precision at five from zero
> point eight one to zero point five five.
>
> The lower numbers are the ones we report. And they are the first measured
> evidence that dense retrieval earns its place, because dense retrieval
> now beats keyword search on recall where before it did not."

Point at the bottom band, do not read it.

> "And this is what we searched for and did not find anywhere in the repository.
> No ROI. No savings. No adoption. No productivity gain. Not because we could
> not construct them — because a fabricated number in this deck would undermine
> every measured one above it."

---

## Slide 10 — Prototype readiness (5:40–6:10)

**Say the gaps first. Always.**

> "Fourteen areas assessed. Eight are genuinely real, one is partial, four are
> deliberately lightweight, one is deferred with named triggers.
>
> Four gaps, before you ask. There is no live model evaluation — no API key in
> this environment, so latency, tokens and cost are unmeasured and we have not
> estimated them. The harness is written and unrun. Every metric is synthetic;
> that is the largest open risk. We never measured a baseline investigation
> time, which is precisely why we make no time-saving claim. And concurrent
> capacity is about two users, because the database permits one writer and the
> audit log writes on every read — so concurrency is a storage migration, not a
> worker count. Saying it scales horizontally would be false."

**Volunteer template mode here if you have not already:**

> "You may notice the wording is template-generated. Running without a model key
> is a supported mode, not a degraded one — the numbers, the evidence and the
> decision are identical either way. The interface says so itself."

> "And every production migration has a **trigger** rather than a volume.
> Enterprise identity is triggered by *before any real data* — a correctness
> condition, not a scale one. Managed vector search is triggered by the first
> customer with data-isolation requirements: security before scale."

---

## Slide 11 — Why this wins, and what a pilot would prove (6:10–6:45)

> "Several categories will produce an explanation. Look at the last two columns.
> None of them declines, and none produces a bounded, owned action when it does
> answer. That is the gap.
>
> And the honest benchmark is not a competitor — it is a good analyst. A good
> analyst does everything in that table. What they cannot do is run in fifteen
> seconds, apply the same materiality rule every time, or leave an audit trail
> that survives their absence. We are not competing with the spreadsheet. We are
> competing with how long the spreadsheet takes."

**The ask:**

> "Round 1 closed on a line: *we are selling the two days back.* We now have the
> working system and **less** licence to say that, because we know exactly what
> we have and have not measured.
>
> So here is the version we can stand behind. One KPI family, one team, one
> quarter, measuring time-to-explanation against the current baseline. That is
> the single measurement that converts our strongest argument into a data
> point — and it is priority five on the roadmap for exactly that reason."

**Close on the band. Say it slowly, then stop talking.**

> "A dashboard tells you what moved. A language model will tell you why,
> confidently, whether or not it knows.
>
> This system tells you why, shows the evidence, recommends what to do — and
> tells you when it cannot.
>
> That last capability is the hardest to build, the easiest to skip, and the
> only one that makes the other three safe to rely on."

---

# Timing

| Format | Plan |
|---|---|
| **7 min** | All eleven slides at the timings above (~6:45), leaving slack |
| **5 min** | Cut Slide 10; fold its four gaps into Slide 09's close. Trim Slides 01 and 04 to 25 s each |
| **3 min, slides only** | Slides 01, 02, 05, 06, 07, 11. Six slides, ~30 s each. This is the Round 1 video spine with Round 2 evidence |
| **3 min, live demo** | Run `eval/final_demo_script.md` unmodified. Open on Slide 02 for 20 s, close on Slide 11's band. Nothing else |

**Never cut Slides 05, 06 and 07.** Those three are the pitch — the same three
the Round 1 video script protected under different names.

---

# Slide ↔ live-demo mapping

If a live demo runs, these slides are redundant with it. Do not show both.

| Demo beat (`eval/final_demo_script.md`) | Replaces | What the slide would have said |
|---|:---:|---|
| 1 · Detect | **03** (top) | Material movement, both legs of the gate |
| 2 · Attribute | **05** | 109.9%, computed not narrated |
| 3 · Evidence | **03** (right panel) | the supporting count and real evidence items; cause inferred, not labelled |
| 4 · Explain and trust | **06**, **07** (calibration) | Track record with its caveat inline; `UNCALIBRATED` |
| 5 · Recommend | **08** (scope band) | Raise the request, not roll back |
| 6 · Stress the trust layer | **07** | Two owners, real interrupt, same bundle hash |
| 7 · Optional | **07** or **08** | Sparse history, or the withheld-item count |

Slides that a demo does **not** cover, and which therefore still earn their
place: **01** problem, **02** why not an LLM on the warehouse, **04** Round 1
continuity, **09** evidence discipline, **10** readiness and gaps, **11** the ask.

---

# Q&A

Full preparation is `eval/judge_defense.md` — 24 questions across three judge
personas, with the weak answers flagged rather than hidden. The pointers below
are the fast index.

### The three most likely questions

| Question | Where the answer lives | The one-line version |
|---|---|---|
| **"Isn't the data synthetic?"** | `judge_defense.md` C1, C2 | "Yes, and every report says so. The figure that is not guaranteed by construction is zero false positives on forty eight clean slices. A pilot on one real KPI family is priority two on the roadmap" |
| **"How do I know the model isn't making it up?"** | `judge_defense.md` B6, B7 | "It has no tools key, no database access, and no field to write a number into. Ten checks run against a frozen hashed bundle. And the gate blocked our own template" |
| **"What is the business value?"** | `judge_defense.md` A5 | "Four mechanisms — operational, decision, risk and governance. Only the risk mechanism is measured. We have not sized the others, and we will not, until a pilot measures the baseline" |

### Questions where our answer is weak — know these cold

Listed in `judge_defense.md` "Weak answers, ranked". Do not improvise past them.

| Question | The honest answer |
|---|---|
| "Have you validated on real data?" | No. It is the largest open risk in the project, it is stated in the proposal as risk 1, and closing it is V2 priority 2 |
| "What does it cost to run?" | Unmeasured. No API key in this environment. The harness exists and has never run. We have not estimated it |
| "Is the confidence actually calibrated?" | Only the high band, on sixty four synthetic cases. The other two bands report *uncalibrated* rather than guess. And the human side of the deferral arithmetic is seeded, not measured |
| "Does the feedback loop work?" | It is implemented, typed and wired. It has run **zero** real cycles. We describe it as implemented, not validated |
| "Can it handle enterprise scale?" | No, and we do not claim it. About two concurrent users. The constraint is the single-writer database plus audit-on-read, which is a storage migration |

**The delivery instruction for this table:** answer at that length and stop.
Every one of these is already in the written proposal. A judge who finds a
limitation you volunteered reads it as rigour. A judge who extracts one you
hedged on reads everything else again.

---

*Team SouthernHustlers · Accenture Innovation Challenge 2026 · Problem Track 3*
*Deck: `R2_PITCH_DECK.md` · Evidence: `R2_PITCH_DECK_SOURCE.md` · Demo: `eval/final_demo_script.md` · Q&A: `eval/judge_defense.md`*
