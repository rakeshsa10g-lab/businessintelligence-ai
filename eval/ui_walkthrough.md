# First-time user walkthrough (Stage 11, Part 24)

Method: not a description of intent. Every screen quoted below is real output
from `scripts/_walkthrough.py`, a Streamlit `AppTest` harness that drives the
actual `app.py` through all eight scenarios end to end — same graph, same
retrieval index, same deterministic template (no `ANTHROPIC_API_KEY` is
configured in this environment). Raw output is saved under
`scripts/_walkthrough_out/*.txt`. Where a claim below is timed, the number is
the harness's own measured wall time for that run, not an estimate of reading
speed.

The exercise: open the app knowing nothing about the implementation, and
within 20–30 seconds answer four questions — what changed, why, how strong is
the evidence, what should I do.

---

## S1 — the finding case

**What the default screen shows, top to bottom, with no scrolling or
clicking:**

```
Net Revenue · West × Web/Mobile App
↓ 25.0%                              MATERIAL MOVEMENT
12 Jul → 26 Jul 2026
52,750 INR against a baseline of 211,204 INR

HYPOTHESIS
a product or platform failure in Web/Mobile App and West.

WHY DID IT MOVE?
ANALYTICAL RESULT
conversion rate is the largest contributor, accounting for more than
the whole movement (109.9%) — other factors moved the opposite way
and partly offset it.
Most affected slice: channel = Web/Mobile App, region = West

EVIDENCE
7 supporting

HOW RELIABLE IS THIS?
High reliability
Correct in 12 of 12 similar past cases.
These cases come from a synthetic evaluation set, not from production history.

RECOMMENDED ACTION
Escalate payment gateway to Engineering
Owner · Engineering Lead
Your authority · you may request this action
Monitor · watch Checkout Conversion Rate for 2 day(s)

EXPECTED RECOVERY IF ACTED ON
622,121 – 799,870 INR
[Raise the request]
```

**Answering the four questions, as a first-time reader:**

1. **What changed?** Net Revenue, West, down 25.0%, 12–26 Jul. Answered by the
   largest text on the page — no reading required, just looking.
2. **Why does the system think it changed?** A product/platform failure in the
   affected channel and region, driven by conversion rate. Answered by the two
   coloured blocks directly below the headline, one labelled HYPOTHESIS and one
   ANALYTICAL RESULT — visibly two different kinds of claim before reading
   either.
3. **How strong is the evidence?** 7 supporting sources; "High reliability,
   correct in 12 of 12 similar past cases" — with the caveat that those cases
   are synthetic sitting in the same block, not hidden in a footnote.
4. **What should I do?** Escalate to Engineering, and a button that does
   exactly that (raises the request; does not attempt the fix itself).

**Time to all four:** under 10 seconds of reading, once the run finishes.
**Time for the run itself:** 53.7s wall time — `attribute` alone costs 13.5s
(LMDI + Adtributor + a 400-resample moving-block bootstrap), visible in the
Audit tab's node-timing table, not on this screen. That gap is the reason
`ui/components/progress.py` exists at all.

**Verdict: pass**, no tab-switching needed for any of the four.

---

## S4 — sparse history (a decline that has to be actionable too)

```
No movement measured                 NOT ENOUGH HISTORY TO ASSESS

Not enough history to judge this yet
This slice is too new for the system to know what normal looks like.
A weekly pattern cannot be separated from a real change until there
is enough history to establish one.

52 days of history are available. A seasonal baseline needs 56.

Extrapolating from a short series would produce a confident number
with nothing behind it, so the system declines instead.

WHAT WOULD CHANGE THIS
About 4 more days of observations. The system will start explaining
this slice on its own once the baseline exists — no action is needed now.
```

A first-time reader gets a direct answer to a fifth, implicit question the
brief's four don't ask but a real user would: *why won't it tell me?* — 52 of
56 days, four days short, no action needed. This is the chip that read wrong
on first render (see the audit below) and was corrected mid-session: it
originally said "Below materiality threshold", which claims a check that never
ran. **Verdict: pass, after one real correction.**

---

## S2 — conflicting evidence, escalated to a person

```
South × Apparel
↓ 21.9%                              MATERIAL MOVEMENT

HYPOTHESIS
competitive pressure on Apparel and South.

[...why/evidence/confidence render identically to S1...]

HOW RELIABLE IS THIS?
Uncalibrated
Only 2 comparable case(s) have been recorded — below the minimum
needed to quote a hit rate.

HUMAN REVIEW
AWAITING YOUR DECISION
Two explanations are equally supported and imply different owners.
Which is it: (competitive pressure on Apparel and South) or (stock
availability in Apparel and South)?

[Accept] [Reject] [Correct] [Request clarification]
```

The question a reader is shown is a genuine question, not a symptom of a
crash — the review block uses the accent colour, not the contradiction
colour, and there is no dismiss control. It reads as an open task, which
is what it is: a real LangGraph `interrupt()` paused on a durable
checkpoint. **Verdict: pass.** (This screen's question also failed on first
render — see below.)

---

## S7 — a non-event, deliberately quiet

```
Marketplace rename - schema change
↑ 5.9%                               BELOW MATERIALITY THRESHOLD

Nothing here needs your attention
The system looked and found no movement large or sustained enough
to act on.

This is a result, not a failure. Reporting every small fluctuation
is how a system trains people to ignore it.
```

No driver chart, no reliability chip, no action block — deliberately
less screen than S1, not the same screen with a different label. A reader
spends less time here, which is correct: there is nothing to decide.
**Verdict: pass.**

---

## Where the exercise found real bugs

Running the actual harness — not reading the code and imagining what it would
show — surfaced three defects a code review would not have caught, because
each one was correct *code* producing an incorrect *sentence*:

1. **The over-100% driver share read as an error.** S1's rendered chart
   originally said "accounting for 110% of the movement" with no explanation
   — a first-time reader's most likely reading is "that's a bug", not "other
   factors partly offset it", which is what a share above 100% actually means
   in an exact multiplicative decomposition. Fixed to state the offset
   explicitly and render one decimal place, so "100%" can never appear next
   to a claim that something exceeds the whole.

2. **The sparse-history chip claimed a check that never ran.** S4 originally
   showed "Below materiality threshold" — a specific claim that the
   materiality rule was evaluated and failed. Detection actually stops at the
   coverage gate for a sparse slice, before materiality is ever reached. A
   first-time reader has no way to know the difference, which is exactly why
   showing the wrong one is a comprehension failure, not a cosmetic one.

3. **The analyst's question was cut in half.** S2's review question is two
   parenthetical clauses — `(cause A) or (cause B)` — and the first version
   of the slice-notation cleanup swallowed everything from the middle of the
   first clause to the middle of the second, because nothing told it to stop
   at a closing parenthesis. A reader would have been asked to choose between
   half a sentence and a garbled one.

None of these were found by reading source code; all three were found by
generating the actual sentence and reading it as a stranger would. All three
now have regression tests that assert the *rendered text*, not that a function
exists (`tests/test_ui.py`, `tests/test_graph_failures.py`).

---

## A fourth bug the exercise found, of a different kind

Pretending to be a first-time user surfaced one more failure that is not a
wording problem: **clicking through the scenario list without touching the
persona selector silently defeated S6.**

S6 exists specifically to demonstrate entitlement withholding for an
`ops_lead` reader. Streamlit's widget model ignores a changed `index=`
argument on a keyed widget once that key already has a session value — so
loading the app (default persona `meera`, analytics_lead), then simply
picking "S6" from the scenario dropdown without also touching the persona
dropdown, ran the analysis **as meera**, who is not the persona the scenario
was built to restrict. The withheld-evidence notice never appeared. A
first-time user following the obvious path — scan the scenario list, pick
one, run it — would never see the one screen built to prove the entitlement
gate does something.

Fixed by scoping the persona selector's widget key to the scenario id, so
each scenario's default persona actually takes effect when selected. Verified
in the walkthrough output: S6 now renders `Priya · Ops Lead` and `1 item
withheld`. Structurally guarded by
`test_the_persona_selector_key_is_scoped_per_scenario`.

---

## What remains a known limitation, not fixed here

- **No live model generation has been observed.** Every screen above shows
  "Verified template mode" in the Audit tab, honestly labelled, because no
  `ANTHROPIC_API_KEY` exists in this environment. The narrative wording comes
  from `verification.build_deterministic_narrative`, not a model. If a key is
  supplied later, the same screens render the model-generated path — the
  Audit tab's `narration_mode()` branches on `telemetry.llm_calls`, not on a
  UI flag — but that branch is untested against a live run.
- **The loading panel's "real-time" ticking was checked structurally
  (`test_the_loading_panel_uses_business_language_not_node_names`,
  `Progress.finish()` only ticking nodes present in telemetry), not observed
  mid-flight** — the harness waits for completion before reading anything, so
  a genuinely stuck stage (a slow retrieval call, say) has not been watched
  live to confirm it stops advancing rather than silently completing.

---

## Post-QA corrections (independent browser QA, 2026-08-24)

An independent browser-based QA pass (`eval/antigravity_ui_qa.md`) drove the
running app through Chrome and returned **READY WITH FIXES** — five findings,
none of them blockers. Four changed screens described above. The corrected
observations:

### S1 / S5a / S5b — the "why automated" disclosure

**Was:** the expander under *Recommended action* printed the audit-trail
rationale verbatim — conditional-expectation notation on the primary business
screen.

**Now:** the same figures as consequence. Rendered:

> **Acting now carries less risk than waiting.** Sending this for manual
> review would cost about **53,250 INR** in analyst time and delay — more than
> the review would be expected to save by catching a wrong call.
>
> Weighing the chance of being wrong against what being wrong would cost:
> acting now is worth about **53,571 INR** of expected risk, against
> **128,250 INR** if this waited for a person — a difference of roughly
> **74,679 INR** in favour of acting.

The exact notation is now a Method card, with `p_model`, `p_human`, cost of
error and policy version beside it. Nothing was removed from the product; it
moved to the tab whose job is method.

### S1 / S2 / S6 — cohort cards

**Was:** empty containers. The panel read four field names that do not exist
on `CohortEvidence`, so every card rendered blank — which reads as data that
failed to load, not as a cohort with nothing to say.

**Now:**

```
payment tickets
35 documents in the event window · none in the 8-week baseline · 35 distinct account(s)

gateway CRM notes   [New in this window]
5 documents in the event window · none in the 8-week baseline · 5 distinct account(s)
```

Cohorts with no documents are not rendered at all.

### S7 — the no-material screen

**Was:** the styled abstention card, then an expander containing the raw
detector string — gate names, enum values, `->` transitions.

**Now:** the screen ends at the business sentence, which already carried the
numbers a reader needs:

> Nothing here needs your attention
> The system looked and found no movement large or sustained enough to act on.
> **The movement was 105,986 INR, below the 250,000 INR minimum.**
> This is a result, not a failure. Reporting every small fluctuation is how a
> system trains people to ignore it.

The raw string is now an Audit row (`Terminal reason (raw)`). The same fix
applies to the data-quality screen, which could otherwise print a literal
`IOException` at a reader.

### Every screen — narration status

**Was:** a low-contrast grey sidebar caption asserting that no API key was
configured. Subtle enough to miss, and a claim about the *environment* rather
than about the run — it would have been wrong had a key been present.

**Now:** a chip driven by the run's own telemetry, in the existing palette:
`Verified template mode` (amber) when a narrative was produced without a
model, `LLM not required` (quiet) when the run ended before narration, and
`Model-generated, verified` (green) when a model actually ran. One function
feeds both this chip and the Audit tab, so they cannot disagree.

### Not a screen — checkpoint serialization

The QA pass also caught `pandas.Timestamp` deserialization warnings on S2/S3
resume. Fixed at the type boundary; S2 and S3 still interrupt and resume on
the same run id with an identical bundle hash, and the warning count is now
zero in both normal and strict serialization modes. Full detail in
`eval/antigravity_ui_qa.md` §17.

### Still true after the fixes

Everything in the walkthrough above still holds: 8/8 scenarios render without
exception, the four first-time-user questions are answerable on the default
screen without switching tabs, restricted evidence never reaches the UI, and
no live model has been observed because no API key exists in this environment.
