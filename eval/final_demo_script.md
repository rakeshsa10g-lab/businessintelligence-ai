# Three-minute demo script

**One story, two scenarios.** S1 carries the arc; S2 is the differentiator and
it must land inside the first two minutes. Everything else stays closed.

Do not demonstrate eight scenarios. Do not open the Method tab unless asked —
its existence is worth more than its contents in three minutes.

> **Restructured after the product/judge audit.** The previous cut reached the
> conflicting-evidence moment at 2:15, which the audit found was too late: up to
> that point the demo is legible as a competent BI copilot, and the one thing no
> competitor does was arriving after the judge had already formed a category
> judgement. S2 now starts at **1:30**, and the two beats that used to precede it
> (evidence tour, reliability) are folded into the beats they belong to.

**The one moment a judge should remember:**

> **The system refuses to invent a root cause when the evidence conflicts.**

Everything before it exists to make that refusal meaningful; everything after
it exists to show the refusal is enforced rather than promised.

---

## Before you start

```bash
streamlit run app.py
```

Pre-run **S1 once** so the embedding model is warm. Cold start is ~50 s; warm
is ~4 s. Leave the app on S1, Workspace tab.

Say this line early, unprompted:

> "No API key is configured, so the wording you'll see comes from the verified
> deterministic template — the numbers, the evidence and the decision are
> identical either way. The system says so itself in the sidebar."

Volunteering the limitation before anyone finds it is worth more than the
thirty seconds it costs.

---

## Beat 1 — What moved? (0:00–0:20)

**Show:** the top of the Workspace.

```
Net Revenue · West × Web/Mobile App
↓ 25.0%                         MATERIAL MOVEMENT
12 Jul → 26 Jul 2026
52,750 INR against a baseline of 211,204 INR
```

> "Net revenue in West fell 25% over two weeks. The chip says **material** —
> that's not a threshold on the percentage, it's a business rule with both a
> statistical and a business leg. Most movements never get here."

Point at the KPI chart directly beneath it.

> "And that's the series itself, with the changepoint the detector found and the
> window it compared. Nothing on this chart is drawn by a model."

**Do not** explain STL, MAD or PELT. If asked: *"decomposition, robust z-score,
changepoint detection — it's in the Method tab."*

---

## Beat 2 — Why? (0:20–0:45)

**Show:** the driver chart.

> "Conversion rate is the driver. Note it says it accounts for **more than the
> whole movement** — 109.9% — because sessions actually rose and partly offset
> it. That's an exact identity decomposition, so it closes to zero, and the
> system explains the number rather than hiding it."

Point at *Most affected slice: channel = Web/Mobile App, region = West*.

> "And it localises — not just what moved, but where."

**Why this beat matters:** the 109.9% is the single best demonstration that the
numbers are computed, not narrated. No model would produce a self-explaining
over-100% share.

---

## Beat 3 — Evidence (0:45–1:10)

**Show:** the evidence block — the count *and* the items beneath it.

> "Eight documents corroborate, and the two most relevant are right here — I
> don't have to take the count on trust. Support tickets clustering in the
> affected window, a gateway deployment on the 12th.
>
> Note what none of them says: no ticket says *'the payment gateway caused a
> revenue decline'*. They're customer complaints — 'card declined', 'checkout
> spun forever'. The cause is inferred by the pipeline, not read off a label."

Then, without leaving the screen, point at the reliability block:

> "And reliability is a track record, not a confidence score — correct in 12 of
> 12 similar past cases, with the caveat that those cases are synthetic sitting
> in the same block, not in a footnote."

**Do not** open the Evidence tab here. The default screen now carries enough.

---

## Beat 4 — Action (1:10–1:30)

**Show:** the recommendation block and the button.

> "Escalate to Engineering. Owner named, monitoring metric named, two-day
> check. Expected recovery is a **range**, and it's read from the movement the
> detector measured — the system doesn't estimate it."

Then point at the button text:

> "And read the button: **Raise the request**. Not 'roll back'. The persona has
> request rights on this lever, not approval rights, so what gets automated is
> raising the request. Rolling back is a different lever that no persona in
> this system can approve, and it's on a never-automate list."

**This is the safety beat.** Scope separation is the thing enterprise buyers
actually worry about.

---

## Beat 5 — Now introduce conflicting evidence (1:30–2:00)

**Switch to S2 in the sidebar. Click Run.** (~14 s — talk through it.)

> "That was the case where the evidence agreed. Here's the one where it doesn't.
>
> Same engine, different event. South × Apparel, down 21.9%."

While it runs, set up the stake — do not wait for the screen to make the point:

> "Two explanations come back equally supported: competitive pressure, and stock
> availability. Every tool in this category will pick one and write you a
> confident paragraph about it.
>
> Watch what this one does instead."

**This is the setup, and it is the reason the demo is structured this way.**
Everything before this beat is legible as a competent BI copilot. This is where
that stops being the right category.

---

## Beat 6 — The system refuses to choose (2:00–2:30)

**Show:** the review block.

```
AWAITING YOUR DECISION
Two explanations are equally supported and imply different owners.
Which is it: (competitive pressure on Apparel and South) or
(stock availability in Apparel and South)?

[Accept] [Reject] [Correct] [Request clarification]
```

> "Two explanations, equally supported, and they imply **different owners** —
> one is a pricing problem, one is a supply problem. Guessing doesn't just risk
> a wrong answer; it sends the wrong team. So the system stops, states the
> question, and hands it to a person.
>
> That's a real pause, not a message: the graph is interrupted on a durable
> checkpoint. If I resume it, it's the same run with the same evidence hash —
> the analyst's decision attaches to exactly what they reviewed.
>
> And notice the reliability says **uncalibrated**, so the cost arithmetic that
> would justify automating isn't available. It couldn't automate this even if
> it wanted to."

**This is the beat that wins the room.** A system that declines is more
credible than one that always answers. Give it silence afterwards.

---

## Beat 7 — Entitlement or audit trail (2:30–3:00)

Pick **one**. Do not do both.

**Option A — entitlement (S6):**
> "Same event as the first one, read by an ops lead. One CRM note is withheld —
> and the system says so, with a count. A silently shorter list would be worse."

**Option B — audit trail (Audit tab):**
> "Fifteen lineage records per run, accumulated during execution rather than
> rebuilt at the end. Contract version, entitlement policy, detection method,
> counterfactual result, retrieved document ids, bundle hash, model status."

**Option C — sparse history (S4), if the room is technical:**
> "New category, 52 days of history against the 56 a seasonal baseline needs.
> It won't extrapolate. It tells you to wait four days — and the KPI chart
> shows the series with nothing marked on it, because nothing was found."

---

## Total: 3:00

| Beat | Time | Point |
|---|---|---|
| 1 What moved | 0:20 | Material, not just moved — and the series is shown |
| 2 Why | 0:25 | Numbers are computed, and self-explaining |
| 3 Evidence | 0:25 | Evidence is visible, not counted; reliability caveated inline |
| 4 Action | 0:20 | Bounded scope — request, not rollback |
| **5 Conflict** | **0:30** | **The setup: every competitor picks one** |
| **6 Refuse** | **0:30** | **It stops when it should — the moment to remember** |
| 7 Entitlement / audit | 0:30 | Access control visible, or the trail |

**The differentiator now lands at 1:30 rather than 2:15.** That is the single
structural change from the previous cut, and it exists because the first ninety
seconds are otherwise indistinguishable from a competent BI copilot.

---

## If asked to go deeper — the two-click answer

**"How do I know the model isn't making this up?"** → Method tab.

> "Ten deterministic checks against a frozen, hashed evidence bundle. Ten of
> ten hand-built corrupted narratives were blocked; zero of six valid ones were
> rejected. If any check fails, it retries once, then falls back to a template
> that's itself verified. And the model never sees a database — the request has
> no tools key at all.
>
> One honest boundary: that tests the **verification mechanism**. It is not a
> measurement of live model reliability — no API key is configured here, so no
> real generation has been observed."

**"Can I see the audit trail?"** → Audit tab.

> "Fifteen lineage records, accumulated during the run rather than rebuilt at
> the end. Contract version, entitlement policy, detection method,
> counterfactual result, retrieved document ids, bundle hash, model status."

---

## What not to do

- **Do not open Method or Audit unprompted.** Their existence is the point; their contents are a different conversation.
- **Do not run all eight scenarios.** Two is a story; eight is a test suite.
- **Do not claim business impact.** The recovery range is a measured movement times a configured fraction. Say that.
- **Do not say "accurate" or "production-ready".** Say "measured on synthetic data" and "prototype".
- **Do not hide template mode.** Volunteering it reads as confidence; being caught reads as spin.
- **Do not cold-start S1 live.** 50 seconds of silence is a long time.
