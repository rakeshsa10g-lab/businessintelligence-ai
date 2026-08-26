# Final telemetry report

> **SYNTHETIC_EVALUATION.** All timings below are wall-clock on one developer
> machine (Windows 11, Python 3.13.4), single process, warm caches, against the
> generated dataset — seed `20260821`, 535 days, 6 injected events. They
> characterise *where time goes in this pipeline*; they are not a benchmark and
> they do not predict behaviour under concurrency or on real data volumes.

Source: `python -m eval.run_graph_eval`, which drives all eight scenarios
through the real graph and writes `eval/graph_report.md`. Node latencies are
recorded by the instrumentation wrapper as each node returns — not
reconstructed afterwards.

---

## MEASURED

### Per-scenario runtime

| Scenario | Wall ms | Node ms | Graph overhead | Overhead % | LLM calls |
|---|---:|---:|---:|---:|---:|
| S1 | 49,354 | 49,315 | 38.9 | 0.08% | 0 |
| S2 | 14,414 | 14,383 | 31.8 | 0.22% | 0 |
| S3 | 13,685 | 13,654 | 31.8 | 0.23% | 0 |
| S4 | 46 | 34 | 12.7 | 27.37% | 0 |
| S5a | 4,380 | 4,346 | 34.3 | 0.78% | 0 |
| S5b | 14,602 | 14,563 | 39.7 | 0.27% | 0 |
| S6 | 4,507 | 4,472 | 34.6 | 0.77% | 0 |
| S7 | 301 | 285 | 16.4 | 5.44% | 0 |

### Where the time actually goes

| Stage | Range across scenarios | Note |
|---|---|---|
| **Attribution** | 3,744 – 13,888 ms | Dominant cost. LMDI + Adtributor + a moving-block bootstrap; the bootstrap is the bulk of it. |
| **Retrieval** | 187 – 35,358 ms | Normally ~200 ms. S1's 35 s is the **cold** sentence-transformer model load on the first scenario of the process; every later scenario reuses it. |
| **Detection** | 24 – 446 ms | STL + MAD + PELT. |
| **Hypothesis ranking** | 8 – 77 ms | |
| **Verification (Gate 2)** | < 5 ms | 10 deterministic checks. |
| **Graph orchestration** | **12.7 – 39.7 ms** | Near-constant, independent of scenario. |

### Graph overhead — read the absolute column

Orchestration costs a near-constant **13–40 ms** per run. The percentage is
high exactly where the run is cheapest: S4 abstains in 46 ms total, so a 13 ms
constant is 27% of it. On scenarios that do real work it is 0.08–0.78%.

LangGraph is not a meaningful cost at this size. That is a measurement, not a
defence of the choice.

### Outcome rates across the 8 scenarios

| Rate | Value | Scenarios |
|---|---:|---|
| Automation rate | **50%** (4/8) | S1, S5a, S5b, S6 |
| Review rate | **25%** (2/8) | S2, S3 |
| Abstention rate | **25%** (2/8) | S4 (sparse), S7 (no material event) |
| Template fallback rate | **100%** of narrated runs (4/4) | no API key configured |
| Verification failure rate | **0%** ⚠ | every delivered narrative passed Gate 2 — **but every one took the deterministic template path** (no API key). This measures the template's agreement with the gate, not a model's. Not quoted in any submission-facing material; see `eval/final_evaluation_report.md` §9 |
| Retry count | **0** | no model ran, so no retry was spent |

The scenario set is deliberately balanced to exercise every terminal, so these
rates describe *the demo set*, not a workload. A production mix would be
dominated by `NO_MATERIAL_EVENT`.

### Model accounting

| Metric | Value |
|---|---:|
| LLM calls | **0** |
| Input tokens | **0** |
| Output tokens | **0** |
| Estimated cost | **$0.0000** |
| Cache hit rate | n/a |

Zero because no `ANTHROPIC_API_KEY` exists in this environment, not because
the calls were suppressed. Every narrated run used the verified deterministic
template. The UI labels this **Verified template mode** and states that no
model reviewed the text.

### Test-suite runtime

| | |
|---|---:|
| Tests | **574 passed, 0 failed** |
| Runtime | **785 s (13:05)** |
| Slowest single test | 18.7 s (`test_security_chain` module fixture) |

---

## UNAVAILABLE — requires a live API key

These cannot be measured here and are **not** estimated:

| Metric | Status |
|---|---|
| Live model latency (p50/p95) | `LIVE LLM EVALUATION PENDING` |
| Input / output tokens per insight | `LIVE LLM EVALUATION PENDING` |
| Prompt-cache hit rate | `LIVE LLM EVALUATION PENDING` |
| Cost per insight | `LIVE LLM EVALUATION PENDING` |
| First-pass Gate 2 rate (model output) | `LIVE LLM EVALUATION PENDING` |
| Retry rate under real generation | `LIVE LLM EVALUATION PENDING` |
| Invalid numeric / driver / causal / lever claim rates | `LIVE LLM EVALUATION PENDING` |

`eval/run_llm_eval.py` is implemented and will produce all of them. It prints
a cost estimate with `--plan` and sends nothing without a key.

**What is already known without a key:** the retry cap is enforced (a narrator
that raises on every call terminates on the template after exactly one retry —
`test_a_narrator_that_raises_every_time_still_terminates`), and Gate 2 rejects
all three injected corruption classes with a fake client
(`test_gate_2_catches_each_violation_class_and_never_delivers_it`). What is
unknown is how often a *real* model would trip those checks.

---

## Known measurement limitations

- **One machine, one process, warm caches.** No concurrency was measured, because the prototype is single-process by design.
- **S1's retrieval figure is a cold-start artefact.** 35 s is the embedding model loading, not retrieval work. Steady-state retrieval is ~200 ms. Reported unadjusted rather than quietly excluded.
- **The bootstrap dominates attribution** and its cost scales with `n_resamples` (30 in the harness, 400 by default in `attribution.attribute`). The demo numbers therefore *understate* the default configuration.
- **Outcome rates are properties of the demo scenario set**, which was constructed to hit every terminal at least once.
