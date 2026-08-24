# Three-minute demo script

**One story, two scenarios.** S1 carries the whole arc; S2 exists to show the
system refusing to guess. Everything else stays closed.

Do not demonstrate eight scenarios. Do not open the Method tab unless asked —
its existence is worth more than its contents in three minutes.

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

## Beat 1 — Detect (0:00–0:25)

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

**Do not** explain STL, MAD or PELT. If asked: *"decomposition, robust z-score,
changepoint detection — it's in the Method tab."*

---

## Beat 2 — Attribute (0:25–0:55)

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

## Beat 3 — Evidence (0:55–1:20)

**Show:** `7 supporting`. Click the **Evidence** tab briefly.

> "Seven documents corroborate — support tickets clustering in the affected
> window, a gateway deployment on the 12th, cohort spikes. Note what none of
> them says: no ticket says *'the payment gateway caused a revenue decline'*.
> They're customer complaints — 'card declined', 'checkout spun forever'. The
> cause is inferred by the pipeline, not read off a label."

Return to Workspace. **Twelve seconds maximum in the Evidence tab.**

---

## Beat 4 — Explain and trust (1:20–1:50)

**Show:** the reliability block.

```
High reliability
Correct in 12 of 12 similar past cases.
These cases come from a synthetic evaluation set, not from production history.
```

> "Not a confidence score — a track record. And the caveat is in the same
> block, not a footnote: those twelve cases are synthetic. The system also
> refuses to quote a rate for its medium and low bands, because it has fewer
> than ten cases there. It says **uncalibrated** instead of guessing."

**This is the trust beat.** Land the point that the system limits its own
claims.

---

## Beat 5 — Recommend (1:50–2:15)

**Show:** the recommendation block and the button.

> "Escalate to Engineering. Owner named, monitoring metric named, two-day
> check. Expected recovery is a **range**, and it's read from the movement the
> detector measured — the system doesn't estimate it."

Then point at the button text:

> "And read the button: **Raise the request**. Not 'roll back'. The persona has
> request rights on this lever, not approval rights, so what gets automated is
> raising the request. Rolling back is a different lever that no persona in
> this system can approve and that's on a never-automate list."

**This is the safety beat.** Scope separation is the thing enterprise buyers
actually worry about.

---

## Beat 6 — Stress the trust layer (2:15–2:50)

**Switch to S2 in the sidebar. Click Run.** (~14 s — talk through it.)

> "Same engine, different event. South × Apparel, down 21.9%."

**Show:** the review block.

```
AWAITING YOUR DECISION
Two explanations are equally supported and imply different owners.
Which is it: (competitive pressure on Apparel and South) or
(stock availability in Apparel and South)?

[Accept] [Reject] [Correct] [Request clarification]
```

> "Two explanations, equally supported, and they imply **different owners** —
> one is a pricing problem, one is a supply problem. The system doesn't pick.
> It stops, states the question, and hands it to a person.
>
> That's a real pause, not a message: the graph is interrupted on a durable
> checkpoint. If I resume it, it's the same run with the same evidence hash —
> the analyst's decision attaches to exactly what they reviewed.
>
> And notice the reliability says **uncalibrated**, so the cost arithmetic that
> would justify automating isn't available. It couldn't automate this even if
> it wanted to."

**This is the beat that wins the room.** A system that declines is more
credible than one that always answers.

---

## Beat 7 — Optional, only if time remains (2:50–3:00)

Pick **one**. Do not do both.

**Option A — sparse history (S4):**
> "New category, 52 days of history against the 56 a seasonal baseline needs.
> It won't extrapolate. It tells you to wait four days."

**Option B — entitlement (S6):**
> "Same event as before, read by an ops lead. One CRM note is withheld — and
> the system says so, with a count. A silently shorter list would be worse."

---

## Total: 3:00

| Beat | Time | Point |
|---|---|---|
| 1 Detect | 0:25 | Material, not just moved |
| 2 Attribute | 0:30 | Numbers are computed, and self-explaining |
| 3 Evidence | 0:25 | Cause is inferred, not labelled |
| 4 Explain | 0:30 | Track record, with its own caveat |
| 5 Recommend | 0:25 | Bounded scope — request, not rollback |
| 6 Refuse | 0:35 | It stops when it should |
| 7 Optional | 0:10 | One abstention |

---

## If asked to go deeper — the two-click answer

**"How do I know the model isn't making this up?"** → Method tab.

> "Ten deterministic checks against a frozen, hashed evidence bundle. Zero hard
> violations. If any check fails, it retries once, then falls back to a
> template that's itself verified. And the model never sees a database — the
> request has no tools key at all."

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
