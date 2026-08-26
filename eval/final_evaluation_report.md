# Final evaluation report

Consolidated measured results across every layer. Each metric states its
value, the dataset it was measured on, how it was measured, and its
limitation — because a number without those three is not evidence.

> **All offline figures are `SYNTHETIC_EVALUATION`** unless marked otherwise:
> measured on the generated dataset (seed `20260821`, 535 days, 6 injected
> events), whose ground truth this repository knows by construction. They
> characterise the methods on this dataset. **They are not production
> accuracy.** See `eval/claim_audit.md`.

---

## 1. Detection

**The headline result, stated first because it is the one not guaranteed by
construction:**

> **The detector produced no false positives across the 48 evaluated clean
> slices** in the seeded synthetic evaluation.

That is the meaningful half. The recall figure below is reported second and
deliberately not led with, because the events it recalls are events this
repository injected.

| Metric | Value | Dataset | Method | Limitation |
|---|---:|---|---|---|
| **False positives** | **0** | 48 clean slices of a 64-slice universe | `eval/run_detection_eval.py` | The 64-slice universe is the generated one. Within it, nothing made the detector fire spuriously |
| Injected-event recall | 1.000 | 64 slices, 16 injected events | same | **Methodology limit:** the injected events were constructed to be detectable by this method's own assumptions, so a recall of 1.000 measures internal consistency, not detection skill on real movements |
| Injected-event precision | 1.000 | same | same | Precision over *injected* events |
| False negatives | **0** | same | same | Same construction limit as recall |

**Pipeline:** coverage gate → STL → robust MAD z-score → PELT → materiality.

**Limitation that matters most:** 1.000/1.000 is the single most
overstate-able pair of numbers in the project, which is why this section no
longer leads with them. A real corpus contains movement classes the generator
never produced. What the evaluation does support is the zero-false-positive
result on the 48 clean slices — the harder half, and the half a generator
cannot rig in the detector's favour.

## 2. Attribution

| Metric | Value | Dataset | Method | Limitation |
|---|---:|---|---|---|
| LMDI identity closure | **0.000000000%** | S1 West event | `eval/run_attribution_eval.py` | Exact arithmetic property, not a fit quality — it should be zero, and a non-zero value is a bug |
| Ranking robustness | **STRONG** — top driver held in 100% of 300 resamples | S1 | Moving-block bootstrap | Resampling the same series; not out-of-sample |
| Causal licence | Granted on S1, **denied on S3** | S1, S3 | Difference-in-differences with parallel-trend test | A licence, not a proof. On S3 the control moved with the treated slice, so causal wording is refused |

Reaching exact closure required a real correction: the first implementation
closed to only **94.8%**, traced to a population mismatch between sources and
fixed by ADR-018.

## 3. Retrieval

**Held-out eval split (14 queries) — the authoritative figures.**

| Method | precision@5 | p@5 of achievable | recall@10 | MRR | hard negatives in top 5 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.552 | 0.693 | 0.654 | 0.833 | 2 |
| **Dense** | **0.567** | **0.700** | **0.778** | 0.817 | 3 |
| RRF (hybrid) | 0.552 | 0.693 | 0.697 | **0.838** | 2 |

**Dataset:** 1,336 documents, `BAAI/bge-small-en-v1.5`, corpus hash
`25ca24b4…`. **Method:** `eval/run_retrieval_eval.py` against a generated
relevance benchmark, 21 queries split 7 dev / 14 held-out eval.

**These figures supersede an earlier, easier set** (BM25 p@5 0.810, recall@10
0.957; RRF MRR 0.964) measured when the corpus held only 13 distinct document
texts across 895 records. The realism audit widened it to 30 distinct texts,
and **every score fell**. The lower numbers are the reported ones.

**What the current evaluation supports:**

1. **Corpus realism removed a lexical shortcut.** When almost every document
   was one of thirteen templates, keyword matching was close to a lookup. It
   is not any more, and the drop is the evidence of that.
2. **Dense retrieval became the stronger single method under paraphrase** —
   recall@10 **0.778 vs 0.654** for BM25, a 19% relative gain on the held-out
   split. This is the first measurement in the project that justifies carrying
   an embedding model at all.

**What it does *not* support, stated because an earlier draft of this report
and of the pitch deck implied it:**

- **Not** "RRF beats BM25" as a general claim. RRF leads on MRR by 0.005
  (0.838 vs 0.833), which is noise at 14 queries, and it *ties* BM25 on
  precision@5.
- **Not** "hybrid beats dense". It does not: RRF recall@10 of **0.697 sits
  between** BM25's 0.654 and dense's 0.778. On this corpus, fusing a weaker
  retriever into a stronger one moved the result toward the weaker one.

**Therefore the defensible position on hybrid retrieval:** it remains
implemented as a **robustness mechanism**, not as a measured improvement.
BM25 cannot match paraphrase; dense cannot reliably match rare exact tokens
(`PG-TIMEOUT-504`), and it carries more hard negatives here (3 vs 2). A real
ticket stream contains both failure modes. The claim is *"hybrid is insurance
we can afford"* — the same claim as before the corpus change, now with the
added and honest caveat that **this evaluation does not prove RRF is superior
to dense retrieval**, and a single-retriever dense configuration would be a
legitimate thing for a pilot to test.

**Limitation:** relevance labels come from a generated benchmark, not human
judgement of usefulness. The 14-query held-out split is small enough that
differences under ~0.05 should not be treated as real.

## 4. Verification (Gate 2)

| Metric | Value | Dataset | Method | Limitation |
|---|---:|---|---|---|
| False acceptance | **0** | 10 hand-written corrupt narratives | `eval/run_verification_eval.py` | Zero of *those* got through — not that no corrupt narrative could |
| False rejection | **0 of 6** | 6 valid narratives | same | |
| Injected violations caught by expected code | **9 / 9** | same | same | |
| Checks executed | 150 | same | same | Deterministic: same inputs → same report, including violation order |

Gate 2 also caught **three real bugs in the project's own deterministic
narrative** during Stage 7 — a missing cohort baseline, hypothesis scores
quoted without backing, and an abstention typed as an observation demanding a
citation for an absence.

## 5. Recommendation and deferral

| Scenario | Confidence | Lever | Decision | Scope |
|---|---|---|---|---|
| S1 | HIGH (0.97) | `L_GATEWAY_ESCALATE` | automate | raise request |
| S2 | UNCALIBRATED (0.95) | `L_MONITOR_ONLY` | review | — |
| S3 | UNCALIBRATED (0.56) | `L_MONITOR_ONLY` | review | — |
| S4 | INSUFFICIENT | — | abstain | — |
| S5a | HIGH (0.95) | `L_GATEWAY_ESCALATE` | automate | raise request |
| S5b | HIGH (0.97) | `L_GATEWAY_ESCALATE` | automate | raise request |
| S6 | HIGH (0.95) | `L_GATEWAY_ESCALATE` | automate | raise request |
| S7 | INSUFFICIENT | — | abstain | — |

**Calibration:** 64 synthetic cases. HIGH 12/12, MEDIUM 1/2, LOW 0/1,
INSUFFICIENT 34/49. Only HIGH clears the ten-case floor, so **MEDIUM and LOW
report `UNCALIBRATED`** — the system says it does not know.

**Limitations, all `ASSUMPTION`:** `p_human` is seeded, not measured; decision
values are placeholders that move the automate/defer boundary directly;
`recovery_fraction` is configured, not fitted.

## 6. Graph orchestration

| Metric | Value | Method | Limitation |
|---|---:|---|---|
| Scenarios agreeing with direct-module path | **8 / 8** | `eval/run_graph_eval.py` runs each scenario twice | The point: orchestration changed no decision |
| Graph overhead | **12.7 – 39.7 ms** | wall clock minus summed node latency | One machine, warm caches |
| Overhead as % on real work | **0.08 – 0.78%** | same | 27% on S4 only because S4 total is 46 ms |
| Retry cap | **exactly 2 calls**, then template | fake client raising every time | |

## 7. UI

| Metric | Value | Method |
|---|---:|---|
| Scenarios rendering without exception | **8 / 8** | `scripts/_walkthrough.py` (Streamlit `AppTest`) |
| Caught-and-hidden exceptions | **0** | grep for the error-boundary message across rendered output |
| Raw Python reprs leaked | **0** | grep for `CheckResult(`, `SourceType.` |
| Independent browser QA | **READY WITH FIXES**, 5 findings, all resolved | Antigravity, Chrome CDP |

## 8. Security

| Metric | Value | Method |
|---|---:|---|
| Security tests | **32** | `test_entitlements` (13) + `test_chokepoint` (10) + `test_security_chain` (9) |
| Leak-chain stages verified | **6** | SQL → retrieval → ranking → bundle → LLM payload → UI |
| Restricted items reaching any stage | **0** | with a non-vacuity control proving a permitted reader *does* see them |
| Hardcoded secrets | **0** | regex scan across all source and config |
| Audit correlation | **fixed** | was 1 id per process; now 1 per run, equal to the graph run id |

## 9. Telemetry

Full detail in `eval/final_telemetry_report.md`.

| Measured | Value |
|---|---:|
| Automated | **4 of 8** scenarios |
| Routed to human review | **2 of 8** |
| Abstained | **2 of 8** |
| Template fallback rate | 100% of narrated runs |
| Retry count | 0 |

**These are counts over the 8 synthetic demonstration scenarios, not rates.**
The set was constructed to hit every terminal state at least once, so the
4/2/2 split is a property of the test design, not a workload measurement. A
production mix would be dominated by `NO_MATERIAL_EVENT`. Expressing them as
"50% / 25% / 25%" without that qualifier attached invites reading them as
production behaviour, so the counts are given first and the percentages only
appear alongside the words *of the demonstration set*.

**On "verification failure rate": deliberately removed from this table.**
The prior revision reported **0%**, which was arithmetically true and
substantively misleading. Every narrated run in this environment took the
deterministic template path, because no `ANTHROPIC_API_KEY` is configured — so
the figure measured the template's agreement with the gate, not a model's.
Presenting it as a headline reliability metric implied that live LLM output
had been observed passing verification. It has not.

What is genuinely measured about the gate is in §4: **10 of 10 corrupted
narratives blocked, 0 of 6 valid narratives wrongly rejected, 9/9 injected
violations caught by the expected check.** Those are properties of the
*verification mechanism*. They are not evidence about *live model
reliability*, and the two must not be conflated.

## 10. LLM

**`LIVE LLM EVALUATION PENDING`** — no `ANTHROPIC_API_KEY` in this
environment.

Not measured and **not estimated**: first-pass verification rate, retry rate
under real generation, latency, tokens, cost, invalid numeric / driver /
causal / lever claim rates.

Known without a key: the retry cap holds under a permanently failing narrator;
Gate 2 rejects all three injected corruption classes; the model never receives
a `tools` key. `eval/run_llm_eval.py` is implemented and prints a cost
estimate with `--plan` without sending anything.

## 11. Test suite

| | |
|---|---:|
| Tests | **574 passed, 0 failed** |
| Runtime | 785 s (13:05) |
| Flaky | **0** — two intermittent failures diagnosed to DuckDB single-writer contention |

---

## What this evaluation does not establish

1. **Production accuracy.** Every offline figure is on a dataset this repository generated.
2. **Live model quality.** No generation has been observed.
3. **Behaviour under concurrency.** Single-process by design; untested.
4. **Calibration beyond HIGH.** MEDIUM and LOW have too few cases and say so.
5. **That the feedback loop works.** It is implemented, typed and routed; it has run zero real cycles.
