# Judge defense

Every answer below distinguishes **measured evidence** from **design
reasoning**, and names the weak ones. An answer marked weak is not a hole to
be hidden — it is the question to prepare for.

---

# Judge A — Business / Product

### A1. Why does this product need to exist?

**Design reasoning.** A BI dashboard tells you *that* net revenue fell 25%. It
does not tell you *why*, *how sure it is*, *what to do*, or — critically —
*when it doesn't know*. The gap between "a number moved" and "someone acted"
is filled today by an analyst spending hours reconciling sources.

**Evidence.** The system closes that loop end to end in 4–50 seconds: movement
→ driver decomposition → corroborating evidence → calibrated reliability →
a specific action with an owner and a monitoring metric.

**The honest framing:** this is not "an AI that explains dashboards". It is a
system that *refuses to explain* when it cannot — 25% of the demo scenarios
end in abstention, which is the feature, not the shortfall.

### A2. Why is this better than Power BI or Tableau?

**It is not a replacement — it is the layer above.** Power BI shows the
movement; it does not rank causes against evidence, license causal language, or
route a decision to a human when two explanations imply different owners.

Three things a BI tool structurally cannot do here:

1. **Reconcile unstructured evidence with the metric.** Support tickets, CRM notes, deploy logs and market events sit outside the cube.
2. **Abstain.** A dashboard always renders. This system declines on 2 of 8 scenarios and says why.
3. **Carry decision rights.** `L_GATEWAY_ESCALATE` is *request* for all three personas, so "automate" means raise the request — never perform the rollback.

**Weak answer flag.** A judge could reasonably say "Power BI Copilot is adding
narrative too". The defensible distinction is not narrative — it is the
**verification gate**. Our narrative is checked against a frozen evidence
bundle by 10 deterministic checks before delivery, and fails closed to a
template. That is the differentiator to lead with, not "we also write prose".

### A3. Who uses it?

Three implemented personas, each with different entitlement and decision
rights: **analytics lead** (method depth), **ops lead** (region-scoped,
action-oriented), **finance director** (larger decision value, no region
filter). Same event, same analysis, three different permitted evidence sets
and three different economics — measured in S1 / S5a / S5b.

### A4. What decision changes?

Concretely, on S1: without the system, a −25% West movement becomes a
multi-hour investigation. With it, within a minute: conversion rate is the
driver, a gateway deploy on 12 Jul is the leading explanation, 7 documents
corroborate, reliability is HIGH on a 12/12 track record, and the action is
"escalate to Engineering" with a 2-day monitoring window on checkout
conversion.

The decision that changes is **who gets paged, and whether anyone is paged at
all** — S7 is a schema rename that looks like +5.9% growth and correctly
produces no alert.

### A5. What is the business value?

**This is where I must be careful, and the honest answer is a limitation.**

No revenue impact, cost saving or time saved is claimed anywhere in this
project — I searched for exactly those terms in the claim audit and found
none. The impact figure the UI shows (622k–800k INR) is explicitly *recovery
potential of a measured movement*, computed as a configured recovery fraction
applied to the detected effect. It is `ILLUSTRATIVE`.

**What can be defended:** the mechanism by which value would arise —
faster triage, fewer false alarms via the materiality gate, and a decision
routed to a human when the expected cost of being wrong exceeds the cost of
review. **What cannot:** any number attached to that, because no real
deployment exists.

**Weak answer flag — this is the weakest answer in the set.** Smallest truthful
improvement: run the system against one real historical incident from a
willing company and report time-to-explanation versus what actually happened.
That converts an argument into a data point.

### A6. Why would a company trust it?

Four structural reasons, all testable:

1. **Every number is computed, never generated.** The narrator has no `tools` key and `Narrative` has no `confidence` field — there is nowhere for a model to invent one.
2. **Every claim is checked before delivery.** 10 deterministic checks against a hashed, frozen evidence bundle; 0 false acceptances across 10 hand-built corrupt narratives.
3. **It says when it doesn't know.** Six typed abstention states; `UNCALIBRATED` where fewer than 10 comparable cases exist.
4. **Every read is audited**, including denials, correlated to the run the user saw.

### A7. How would adoption work?

**Design reasoning, not measured.** Phase 1: read-only on one KPI family,
running alongside existing reporting, with every recommendation reviewed —
the deferral engine already supports forcing review. Phase 2: automation
enabled only for `raise_request` scope levers. Phase 3: calibration accumulates
real outcomes, replacing the synthetic table and the seeded `p_human`.

The prerequisite is enterprise IAM: persona is currently a dropdown, and no
real data should touch this until identity is proven.

---

# Judge B — Technical

### B1. Why not let the LLM query the warehouse?

**Because a model that can query can fabricate a query result, and you cannot
verify what you cannot bound.**

The narration request has **no `tools` key** — absent, not empty — asserted
against the recorded request, not the code that builds it
(`test_the_client_never_offers_tools`). The model receives a frozen JSON
bundle and returns structured output. If a fact is not in the bundle, it does
not exist as far as the narrative is concerned, and Gate 2 rejects any number
that is not in the numeric allowlist derived from that bundle.

This is architectural, not behavioural. No prompt says "do not make things up".

### B2. Why LangGraph?

The workflow is genuinely a state machine: conditional abstention, a bounded
verify-retry cycle, a human interrupt, and a lineage trail. A checkpointed
graph delivers all four from one dependency.

**Measured:** orchestration costs **13–42 ms** per run, 0.08–0.80% of runtime
on scenarios that do real work. It is not a meaningful cost at this size.

**Honest caveat, stated in the architecture:** LangGraph is justified *at this
size* — 26 nodes, one cycle, three interrupt-capable branches. Past ~20 working
nodes or a second cycle, that would be a signal the design got worse, not that
the framework got better.

### B3. Why no LangChain?

LangChain 1.0's value proposition is `create_agent` and its middleware loop —
an agent abstraction this architecture specifically must not have.
`langchain-core` arrives transitively under LangGraph, which is accepted and
annotated. `import langchain` appears nowhere, asserted by a test.

*"LangChain's value is the agent loop. Our central claim is that the model
never chooses what data it sees. So we took LangGraph — the runtime underneath
— and left the agent layer out, on purpose."*

### B4. Why embeddings?

Because BM25 cannot match paraphrase. A ticket saying *"Checkout spins
forever"* and one saying *"Payment page hung and then timed out"* describe the
same failure with no shared content words.

**Newly measured, and this is the strongest version of this answer:** on the
original corpus, dense retrieval did *not* beat BM25 — the corpus had only 13
distinct document texts, so there was no paraphrase to catch. After the Stage
13 realism audit widened the language pools, **dense recall@10 (0.778) now
clearly beats BM25 (0.654)**. The capability was always the justification; it
took a realistic corpus to make it visible.

### B5. Why no vector database?

1,341 documents × 384 dimensions. Brute-force cosine over a numpy array is
exact, ~200 ms, and has no operational surface. A vector DB at this scale is
infrastructure with nothing behind it.

**The trigger for changing that is security, not scale** — the index is a
single artefact spanning all tenants. Brute force is fine to ~10⁵ documents;
the isolation problem appears at customer two.

### B6. How is hallucination controlled?

Five layers, in order of strength:

| Layer | Mechanism |
|---|---|
| **Structural** | No tools. No database handle. No `confidence` field to fill. |
| **Input** | Frozen, hashed `EvidenceBundle`. Nothing can be added after the freeze. |
| **Output** | Gate 2 — numeric allowlist, driver membership, evidence coverage, citation validity, causal licence, lever membership. |
| **Fallback** | Fail closed to a deterministic template that is itself verified. |
| **Bounded** | Exactly one retry, enforced in both the router and the node. |

**Measured:** 0 false acceptances across 10 corrupt narratives; all three
injected corruption classes (numeric, driver, causal) terminate on the
template.

### B7. How are numbers protected?

Every figure a user sees is computed by SQL, statistics, or a business rule.
Gate 2's numeric check extracts every number from the narrative and rejects
any not present in the bundle's allowlist — dates are stripped first so a date
cannot masquerade as a figure.

The impact range is *read* from the measured movement, never estimated by a
model.

### B8. How is causal language controlled?

`causal_language_licensed` is a boolean produced by difference-in-differences
with a parallel-trend test, a specificity floor and temporal precedence. Gate 2
enforces it per-hypothesis.

**Measured on S3:** the licence is **denied** — the control region moved with
the treated slice, consistent with a market-wide movement — and the UI renders
*"Association only — the counterfactual test did not license a causal claim."*
The system demonstrably declines to claim causation when it cannot support it.

### B9. How does security work?

```
Principal → policy → SQL row/column filter → retrieval candidate filter
         → ranking → EvidenceBundle → LLM payload → UI
```

Entitlement is applied **before** ranking, which is the load-bearing detail:
filtering after ranking lets a restricted document influence the scores of its
neighbours, leaking information about its existence even when the document is
dropped.

**Measured:** 32 security tests, including a 9-test chain asserting absence at
all six stages — with a *non-vacuity control* proving a permitted reader does
retrieve the same document, so no assertion passes because the data is simply
missing.

### B10. What happens if evidence is missing?

It abstains, with a typed reason and a remedy. `ABSTAIN_INSUFFICIENT_EVIDENCE`
names the missing source. Six states exist because each has a different fix:
sparse history needs *time*, insufficient evidence needs a *source*,
conflicting evidence needs a *person*.

---

# Judge C — Skeptical

### C1. Isn't the dataset synthetic?

**Yes, entirely, and every metric is labelled `SYNTHETIC_EVALUATION` in the
reports themselves** — not in a footnote, in a banner above the numbers.

The case explicitly says teams are not expected to have real proprietary data.
What matters is whether the synthetic data makes the problem *trivial*, which
is C2.

### C2. Doesn't the synthetic setup favour your detector?

**Partly yes, and I found a concrete instance of it and fixed it.**

The honest position on detection's 1.000/1.000: recall over *injected* events
is not recall over reality. The events were constructed to be detectable by
this method's assumptions. The report says exactly that. What the figure does
support is the harder half — **0 false positives across the 48 slices with no
injected event.**

**What the Stage 13 audit found:** the document corpus had only 13 distinct
texts across 895 tickets — 1.5% lexical diversity, every document a verbatim
template repeat. That *was* making retrieval trivially easy.

**What was done:** the generator's language pools were widened (ground truth
byte-identical, verified by diff). Retrieval scores **fell sharply and
honestly** — BM25 p@5 0.810 → 0.552, recall@10 0.957 → 0.654 — and hard
negatives appeared in the top 5 for the first time. The weaker numbers are the
more truthful ones.

**Remaining limitation, stated:** 3.4% diversity is still far below a real
ticket stream. The corpus is more honest than it was; it is not real.

### C3. Is Adtributor appropriate here?

It was designed for multi-dimensional anomaly localisation in telemetry
(Bhagwan et al., NSDI '14) — cube-shaped data with additive measures, which is
what a KPI × region × channel × segment cut is.

**Where it needed correction:** the paper's surprise formulation admitted
degenerate qualifications on our data, so a floor was added (ADR-019). That is
documented rather than hidden.

**What justifies it over a simpler alternative:** `rank_by_contribution_only`
is implemented as a strawman and picks a *different* driver. The comparison is
runnable, not asserted.

### C4. Is DiD really proving causality?

**No, and the system never claims it is.** It licenses *wording*, not truth.

DiD with a parallel-trend test and a specificity floor is a quasi-experimental
design that supports a causal claim under assumptions that are checkable but
not guaranteed — no unobserved confounder moving only the treated slice.

**The strongest evidence that this is honest:** on S3 the licence is denied
and the narrative degrades to associative language. A system that always
granted the licence would be a rubber stamp.

### C5. What happens when the system is wrong?

Three answers at different levels:

1. **When it is uncertain, it does not act** — cost-sensitive deferral compares expected loss with and without review, so an expensive decision defers even at high confidence.
2. **When it acts, the scope is bounded** — `L_GATEWAY_ESCALATE` raises a request; it never performs a rollback. `L_CHECKOUT_ROLLBACK` is on a never-automate list *and* no persona can approve it.
3. **When it is wrong anyway** — the analyst has five typed feedback outcomes, and `accepted`/`escalated` update calibration and `p_human` live.

**Weak answer flag.** The third leg has never run a real cycle. Calibration is
seeded from 64 synthetic cases and `p_human` is an assumption. Smallest truthful
improvement: state that the loop is *implemented and wired*, not *validated*.

### C6. Are confidence levels genuinely calibrated?

**Only HIGH, and only on synthetic data.** 64 cases: HIGH 12/12, MEDIUM 1/2,
LOW 0/1. MEDIUM and LOW fall below the ten-case floor and therefore report
**`UNCALIBRATED`** rather than quoting a rate.

Two details that show this is taken seriously rather than decorated:

- **12/12 is not treated as 100%.** Raw 1.0 made the deferral rule degenerate to "always automate" at every decision value. Laplace smoothing gives 0.929 for the arithmetic while the display still shows the honest raw counts.
- **The UI never shows a bare number.** It shows "correct in 12 of 12 similar past cases" with "these cases come from a synthetic evaluation set, not from production history" in the same block.

### C7. What happens when the model is unavailable?

**Everything except the wording still works — and that is the mode this
prototype currently ships in.**

With no `ANTHROPIC_API_KEY`: detection, attribution, retrieval, ranking, the
frozen bundle, verification, confidence, recommendation and deferral all run
identically. The narrative comes from the deterministic template and is put
through the same Gate 2. The UI labels it **Verified template mode** and states
that no model reviewed the text.

**Measured:** a narrator that raises on every call terminates on the template
after exactly one retry.

### C8. What prevents harmful automation?

Four independent guards:

1. **Never-automate list** — `L_CHECKOUT_ROLLBACK`, `L_PRICING_REVIEW`.
2. **No rights, no automation** — a persona with neither approval nor request rights never has a lever automated on their behalf.
3. **Scope separation** — `AutomationScope` distinguishes *raise the request* from *execute the action*. For every persona in this system, `L_GATEWAY_ESCALATE` is request-only.
4. **`UNCALIBRATED` always defers** — with no observed hit rate there is no `p_model`, so the arithmetic that would justify automating is unavailable.

**Found by testing, not by design:** `L_PRICING_REVIEW` rests on a *single*
guard — `finance_director` is both a persona the system runs as and an approver
— where `L_CHECKOUT_ROLLBACK` has two. Correct today, single point of failure
tomorrow, and now locked by a test that fails if the asymmetry changes.

---

## Weak answers, ranked

| # | Question | Why weak | Smallest truthful improvement |
|---|---|---|---|
| 1 | **A5 — business value** | No real-world impact number exists, and none can be manufactured | One historical incident from a willing company: time-to-explanation vs what actually happened |
| 2 | **C5 / OBJ-7 — feedback loop** | Implemented and wired; zero real cycles run | Say "implemented, not validated". Do not imply it has learned anything |
| 3 | **A2 — vs BI Copilot** | "We add narrative" is not a differentiator | Lead with the verification gate and abstention, not the prose |
| 4 | **C6 — calibration** | One band calibrated, on 64 synthetic cases | Already handled correctly by reporting `UNCALIBRATED`; resist the urge to quote MEDIUM |
| 5 | **All LLM quality claims** | No live evaluation exists | `LIVE LLM EVALUATION PENDING`. Do not claim prompt or model superiority |

## The three questions most likely to be asked

1. **"Your data is synthetic — how do I know any of this works?"** → C1 + C2. Lead with the fact that the audit *found* a realism problem, fixed it, and the numbers got worse. Self-correction is the credible answer.
2. **"How do I know the LLM isn't making it up?"** → B1 + B6. No tools key, frozen bundle, 10 deterministic checks, fail closed to template.
3. **"What happens when it's wrong?"** → C5 + C8. Bounded scope, cost-sensitive deferral, four automation guards, and — honestly — a feedback loop that has not yet run.
