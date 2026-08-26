# Test strategy

**574 tests · 574 passed · 0 failed** — full suite,
`python -m pytest -p no:randomly`.

---

## Classification

| Class | Files | Tests | What it protects |
|---|---|---:|---|
| **Unit** | `test_semantic`, `test_detection`, `test_adtributor`, `test_attribution`, `test_verification`, `test_recommendation` | ~206 | One function's contract in isolation |
| **Integration** | `test_evidence`, `test_retrieval`, `test_llm` | ~166 | Modules composed, real data, real index |
| **Security** | `test_entitlements`, `test_chokepoint`, **`test_security_chain`** | 32 | Policy, the DuckDB chokepoint, and the full leak chain |
| **Scenario** | `test_evidence`, `test_recommendation`, `test_ui` (parametrised over S1–S7) | 8 × several | Every demo scenario reaches its intended terminal |
| **Failure injection** | `test_graph_failures` | 35 | 20 fault modes, each *caused* rather than asserted-about |
| **Graph routing** | `test_graph_routing` | 27 | Every branch, terminal, the retry cap, the LLM-free routing guarantee |
| **UI / application** | `test_ui` | 38 | Rendering, vocabulary, honesty of the template-mode label |
| **Evaluation** | `test_data` | 20 | Dataset reproducibility and the scenario manifest |

Counts are `def test_` counts; the collected total (574) is higher because of
`@pytest.mark.parametrize` expansion.

---

## What the suite is actually designed to catch

Three properties recur, and each came from a bug that got through:

### 1. Tests assert *rendered behaviour*, not that a function exists

Stage 11 found three defects that were correct code producing an incorrect
sentence — a 110% share with no explanation, a materiality verdict for a check
that never ran, an analyst question cut in half by a regex. None was reachable
by reading code. The regression tests assert the produced string.

### 2. Absence tests carry a non-vacuity control

`test_security_chain.py` asserts a restricted document is absent at six
stages. Every one of those would pass if the document simply did not exist, so
a paired test asserts a *permitted* reader does retrieve it.

### 3. Vacuous tests are treated as defects

Two were found and replaced in Stage 9: one asserted a config flag rather than
the behaviour it configures (it would have passed with the override deleted
from the engine), and one asserted `x != y or True` — a tautology.

---

## Runtime and the slow tests

| Test | Time | Why it is slow, and why that is acceptable |
|---|---:|---|
| `test_every_scenario_is_demoable[S1]` | 66.2 s | Module fixture: runs all 8 scenarios through the real graph once, then shares them |
| `test_s1_produces_one_clearly_separated_hypothesis` | 50.8 s | Module fixture: cold embedding-model load |
| `test_same_seed_produces_identical_output` | 38.1 s | **Regenerates the entire dataset and diffs it.** The only honest way to test determinism |
| `test_scope_is_none_unless_the_decision_actually_automated` | 32.5 s | Module fixture across four scenarios |
| `test_re_invoking_the_same_scenario_does_not_return_a_stale_run` | 28.7 s | Two full graph runs — the point of the test is that they are two |

Expensive fixtures are module-scoped. A single real run costs 4–50 s of
detection, attribution and retrieval, and nothing about it changes between
assertions.

---

## Flaky tests

**None currently.** Two intermittent failures were seen during development and
both were diagnosed to a cause outside the tests:

| Symptom | Root cause | Resolution |
|---|---|---|
| Mass errors, suite finishing in ~120 s instead of ~780 s | **Two pytest processes running concurrently**, contending for the DuckDB file lock | Environmental. Run the suite alone; verified by re-running clean |
| `MemoryError` allocating 31.3 MB in `test_same_seed_produces_identical_output` | Memory pressure from a concurrent process regenerating 821,760 rows | Same cause; not reproducible in isolation |

Both are **DuckDB single-writer contention**, not test flakiness. They are
recorded here rather than dismissed because the symptom (`571 → 439 collected,
3 failures`) looks exactly like a broken suite and would waste an evening if
rediscovered.

One transient Windows access violation was also observed during Stage 10, in
LangGraph's checkpointer thread. It was traced to a genuine bug — an unbounded
verify/retry cycle caused by a counter that failures did not advance
(ADR-030) — and has not recurred since the fix.

---

## Known exclusions

| Not tested | Why |
|---|---|
| **Live LLM generation** | No `ANTHROPIC_API_KEY`. Fake clients cover the retry cap, malformed output and all three Gate 2 violation classes; what is untested is how often a *real* model trips them |
| **Concurrency** | Single-process prototype by design. The `ContextVar` audit fix removes one known cross-thread hazard, but no multi-session load was run |
| **Streamlit widget interaction** | `AppTest` drives the app headlessly and covers rendering. Actual browser click-paths were covered separately by the Antigravity QA pass |
| **Disk-full / corrupt DB** | Not simulated. A truncated checkpoint file specifically was not tested |
| **Cross-platform** | Developed on Windows 11; CI runs Ubuntu. No OS-specific code, but the Ubuntu path has not been observed passing yet |

---

## Running it

```bash
python -m pytest -p no:randomly              # full suite, ~13 min
python -m pytest tests/test_security_chain.py -p no:randomly   # security only, ~85 s
python -m pytest -p no:randomly -k "not slow"                  # skip regeneration
```

`-p no:randomly` matters: the suite shares expensive module-scoped fixtures,
and random ordering makes a fixture-related failure much harder to attribute.

**Run one pytest process at a time.** DuckDB permits a single writer, and a
second concurrent run produces the mass-error signature described above.
