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

| Metric | Value | Dataset | Method | Limitation |
|---|---:|---|---|---|
| Precision | **1.000** | 64 slices, 16 injected events | `eval/run_detection_eval.py` | Precision over *injected* events |
| Recall | **1.000** | same | same | Recall of 1.000 means every injected event was found — the injected events were constructed to be detectable by this method's own assumptions |
| False positives | **0** | same | same | The 64-slice universe is the generated one |
| False negatives | **0** | same | same | |

**Pipeline:** coverage gate → STL → robust MAD z-score → PELT → materiality.

**Limitation that matters most:** this is the single most overstate-able number
in the project. A real corpus contains movement classes the generator never
produced. What the figure does support: the pipeline does not fire on the 48
slices with no injected event, which is the harder half.

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

| Method | precision@5 | p@5 of achievable | recall@10 | MRR | hard negatives in top 5 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.810 | 0.971 | 0.957 | 0.964 | 0 |
| Dense | 0.781 | 0.943 | 0.933 | 0.929 | 0 |
| **RRF (hybrid)** | 0.795 | 0.957 | **0.957** | **0.964** | 0 |

**Dataset:** 1,341 documents, `BAAI/bge-small-en-v1.5`, corpus hash
`a36a851…`. **Method:** `eval/run_retrieval_eval.py` against a generated
relevance benchmark.

**The honest finding, kept rather than buried:** hybrid retrieval did **not**
beat BM25 on this corpus. It matches on recall@10 and MRR and is slightly
behind on precision@5. Both retrievers are kept because BM25 cannot match
paraphrase and dense cannot match rare exact tokens (`PG-TIMEOUT-504`), and a
real ticket stream has both. The claim is *"hybrid is insurance we can
afford"*, not *"hybrid improved our numbers"*.

**Limitation:** relevance labels come from a generated benchmark, not human
judgement of usefulness.

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
| Automation rate | 50% (4/8) |
| Review rate | 25% (2/8) |
| Abstention rate | 25% (2/8) |
| Template fallback rate | 100% of narrated runs |
| Verification failure rate | 0% |
| Retry count | 0 |

Rates describe **the demo scenario set**, which was built to hit every
terminal. A production mix would be dominated by `NO_MATERIAL_EVENT`.

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
| Tests | **571 passed, 0 failed** |
| Runtime | 785 s (13:05) |
| Flaky | **0** — two intermittent failures diagnosed to DuckDB single-writer contention |

---

## What this evaluation does not establish

1. **Production accuracy.** Every offline figure is on a dataset this repository generated.
2. **Live model quality.** No generation has been observed.
3. **Behaviour under concurrency.** Single-process by design; untested.
4. **Calibration beyond HIGH.** MEDIUM and LOW have too few cases and say so.
5. **That the feedback loop works.** It is implemented, typed and routed; it has run zero real cycles.
