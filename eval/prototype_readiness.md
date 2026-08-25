# Prototype readiness — 14-area matrix

The goal is not production readiness. It is a **technically credible
competition prototype with a defensible production path** — which means each
area should be either genuinely built, deliberately lightweight, or
deliberately deferred *with the trigger named*.

An area marked `DEFERRED` here is not a gap that was missed. It is a decision
that can be defended in a question.

| # | Area | Verdict | One-line summary |
|---|---|:---:|---|
| 1 | System Design | **REAL** | 26-node state machine, 11 terminals, deterministic/AI boundary enforced by tests |
| 2 | System Architecture | **REAL** | 12 packages, 0 circular imports, single data chokepoint |
| 3 | Frontend | **REAL** | Streamlit decision workspace, 8 scenarios, UX-researched, browser-QA'd |
| 4 | APIs / Backend Logic | **REAL** | Typed contracts; boundaries enforced by tests, not convention |
| 5 | Databases / Storage | **REAL** | 3 separated stores, reproducible, checkpoint round-trip verified |
| 6 | Auth / Permissions | **PARTIAL** | Authorisation real and tested end to end; **authentication absent** |
| 7 | Hosting / Cloud | **LIGHTWEIGHT** | `streamlit run app.py`; no cloud, deliberately |
| 8 | CI/CD / Version Control | **REAL** | GitHub Actions runs the suite; executed on a clean runner, 574/574 passing |
| 9 | Security | **REAL** | 32 tests; 6-stage leak chain with a non-vacuity control |
| 10 | Caching / CDN | **LIGHTWEIGHT** | Three caches, all correct; no CDN, none needed |
| 11 | Error Tracking / Logs | **REAL** | 35 failure-injection tests; append-only audit log |
| 12 | Monitoring / Alerts | **LIGHTWEIGHT** | Per-run telemetry; **no alerting, no retention** |
| 13 | Testing | **REAL** | 571 tests, 0 failures, 8 classes |
| 14 | Scaling | **DEFERRED** | Documented with triggers; nothing implemented |

---

## 1. System Design — REAL

26 nodes, 6 conditional branch points, one bounded cycle, 11 typed terminal
states. Every routing predicate is a pure function of deterministic state, and
`test_no_routing_predicate_reads_a_narrative` asserts that against the
predicate **source** — a predicate that started consulting model output would
pass every behavioural test and still fail this one.

The Mermaid diagram is generated from the compiled graph
(`graph.get_graph().draw_mermaid()`), so the picture cannot drift from the code.

## 2. System Architecture — REAL

12 packages, layered acyclically (verified: **0 circular imports**). One
DuckDB caller. The UI imports only `.types` modules plus the graph entrypoint.
Graph nodes are thin — the largest has 9 statements and none performs
statistics.

Divergences from the aspirational architecture are recorded as ADRs with the
failing case that caused them (ADR-017, 018, 022, 026, 029–032), not silently
absorbed.

## 3. Frontend — REAL

Four tabs named for questions, not modules. Five epistemic classes visually
distinguish measured fact from generated sentence. Nine Growth.Design
principles mapped to specific components and then **audited against rendered
output** — three failed on first render and were fixed.

Independent browser QA (Antigravity, Chrome CDP) returned READY WITH FIXES;
all five findings resolved and regression-tested.

## 4. APIs / Backend Logic — REAL

No HTTP API, deliberately — a network boundary with nothing on the other side
of it would be infrastructure for appearance. What exists is `docs/BACKEND_API.md`:
three application entrypoints and ten typed module contracts, each enforced by
a test.

## 5. Databases / Storage — REAL

Three separated stores. Warehouse reproducible from seed `20260821`
(byte-identical, asserted). Checkpoint interrupt/resume verified with an
**identical bundle hash across the pause**, under strict serialization, with
zero warnings. Index carries model, dimension, corpus hash and build time.

## 6. Auth / Permissions — PARTIAL

**Real:** row filters, column masks, source denials; entitlement applied
*before* retrieval ranking; append-only audit including denials; 32 tests
including a 6-stage leak chain with a non-vacuity control.

**Absent:** authentication. Persona is a dropdown — anyone running the app can
read as anyone. Correct for a local single-user prototype, unacceptable with
real data. The gap is one layer: `security/entitlements.py` takes a
`Principal` and never asks where it came from, so every existing test survives
the addition of a real IdP.

**Fixed this stage:** the audit log's `run_id` was a module global set once per
*process* — two runs produced 21 rows under one id matching neither. Now a
`ContextVar` bound to the graph run id, which also removes a cross-thread
hazard under Streamlit's per-session threading.

## 7. Hosting / Cloud — LIGHTWEIGHT

`pip install -r requirements.txt && streamlit run app.py`. No Docker, no
cloud, no reverse proxy.

**Fixed this stage:** `requirements.txt` had stages 3–5 and 8 dependencies
**commented out** while their imports were live — a clean `pip install -r`
produced a repository that could not start. The documented path is now
actually the path.

## 8. CI/CD / Version Control — REAL

`.github/workflows/test.yml`: install → generate warehouse → build index → run
suite → check no credential is committed. Generating fixtures in CI doubles as
the cheapest possible check that the documented setup still works.

**Finding:** the repository was **not under version control at all** — no
`.git` directory existed through twelve stages. Initialised in Stage 12 with
a `.gitignore` covering the warehouse, checkpoints (including WAL/SHM), index
and walkthrough output.

**Upgraded from LIGHTWEIGHT after the workflow actually ran.** The repository
was pushed to a remote and the workflow executed for the first time on commit
`3ea18fe`: **all 574 tests passed on a clean `ubuntu-latest` / Python 3.13
runner**, 10m 01s end to end.

| Step | Time | Result |
|---|---:|---|
| `pip install -r requirements.txt` | 3m 11s | pass |
| `python -m data.generate` | 11s | pass |
| `python -m retrieval.build_index` | 25s | pass |
| `pytest -p no:randomly` | 5m 06s | **574 passed, 0 failed** |
| Credential scan | <1s | pass |

Three things this verified that no local run could:

1. **A clean-machine install works.** Every prior run used a Windows environment
   accumulated across thirteen stages. This is the first evidence that
   `requirements.txt` yields a working repository from nothing — the fix for the
   four dependency blocks that were commented out while their imports were live
   is now confirmed rather than assumed.
2. **The documented setup path is the real path.** The generate → index → test
   sequence ran end to end on a machine that had never seen this project.
3. **The no-key path is genuinely green.** CI sets `ANTHROPIC_API_KEY: ""`, so
   all 574 tests pass in the verified-template mode the prototype ships in.

Incidental: the suite took **302s in CI versus ~785s locally**, which indicates
the local slowness is environmental rather than inherent.

**What is still not claimed.** One workflow on one runner is a control, not a
release pipeline. There is no deployment automation, no matrix across Python
versions or operating systems, no branch protection, and no scheduled run — so
this is REAL in the sense that the check exists and executes, not in the sense
that it is a production CI/CD practice.

## 9. Security — REAL

See `eval/security_audit.md`. No hardcoded secrets, no `.env`, key from
environment only, allowlist redaction in telemetry, no stack traces in the
business view, no PII by construction.

Three residual risks stated rather than closed: single-tenant embedding index,
withheld *source names* disclosed by design, and no authentication.

## 10. Caching / CDN — LIGHTWEIGHT

| Cache | Scope | Entitlement-safe? |
|---|---|---|
| Embedding model (`retrieval/embeddings.py::_model`) | process | **Yes** — model weights, no data |
| Compiled graph (`@st.cache_resource`) | process | **Yes** — structure, no data |
| Embedding index (`@st.cache_resource`) | process | **Yes** — filtering happens per-query, after retrieval |
| Config loaders | process | **Yes** — static YAML |

**No cache holds a query result**, so no cache can serve one persona's data to
another. Verified behaviourally, not just by inspection:
`test_repeated_scenario_switching_does_not_bleed_entitlement` runs
restricted → permitted → restricted in one process and asserts the third run
matches the first.

No CDN. There are no static assets and one user.

## 11. Error Tracking / Logs — REAL

35 failure-injection tests, each *causing* the fault. Two-level UI error
boundary; technical detail confined to the Audit tab. Append-only `audit_log`
with a row per read including denials.

The principle that cost the most to learn: **a telemetry failure must never
cost the analysis.** A renamed field in a lineage f-string once discarded a
valid detection into an abstention. Lineage is now built inside a guard —
degrade the record, keep the result.

## 12. Monitoring / Alerts — LIGHTWEIGHT

Per-run telemetry is captured during execution and rendered in the Audit tab:
runtime, per-node latency, graph overhead, model calls, tokens, cost, retries,
terminal state.

**Not built:** alerting, dashboards, retention, aggregation across runs.
Telemetry dies with the process. `NodeTelemetry` already carries what an
OpenTelemetry span needs; it is a span in all but serialisation.

## 13. Testing — REAL

571 tests, 0 failures, 785 s. Eight classes (`eval/test_strategy.md`). No
known flaky tests — two intermittent failures were diagnosed to DuckDB
single-writer contention from concurrent pytest processes, and that diagnosis
is recorded so the signature is not rediscovered.

Vacuous tests are treated as defects: two were found and replaced (one
asserting a config flag rather than the behaviour it configures, one asserting
`x != y or True`).

## 14. Scaling — DEFERRED

Nothing implemented, by instruction. `docs/PRODUCTION_EVOLUTION.md` gives
eight migrations each with a **trigger** rather than a volume.

The honest headline: the binding constraint is **not** CPU. DuckDB permits a
single writer and the audit log is written on every read, so concurrency is a
storage migration, not a worker-count change. Concurrent capacity today is
roughly *two simultaneous users*, and saying "it scales horizontally" would be
false.

---

## Summary — as assessed at Stage 12

| Verdict | Count | Areas |
|---|---:|---|
| **REAL** | 8 | System design, architecture, frontend, backend, storage, security, error handling, testing |
| **PARTIAL** | 1 | Auth (authorisation real, authentication absent) |
| **LIGHTWEIGHT** | 4 | Hosting, CI/CD, caching, monitoring |
| **DEFERRED** | 1 | Scaling |

Nothing is marked REAL that a judge could disprove in one question, and
nothing is marked DEFERRED without a trigger that says when it would stop
being acceptable.

*Superseded twice below: Stage 13 re-assessed and changed nothing, then CI
executed and moved area 8 to REAL. The current matrix is the last one in this
file.*

---

# Stage 13 final re-assessment

Re-checked at submission readiness. **No category was upgraded for having
documentation** — the two changes below both reflect work done, and one
category was re-examined and deliberately *not* upgraded.

## Changes from the Stage 12 assessment

| # | Area | Was | Now | Why |
|---|---|:---:|:---:|---|
| 5 | Databases / Storage | REAL | **REAL** | Unchanged, but re-verified after a full data regeneration: ground truth byte-identical, detection unchanged, all 8 scenario decisions unchanged |
| 13 | Testing | REAL | **REAL** | Strengthened: the suite *caught two real defects* introduced by the Stage 13 data change — a template citing evidence the bundle did not hold, and a brittle literal-count assertion |

## Re-examined and deliberately NOT upgraded

**8 — CI/CD: stays LIGHTWEIGHT.** The workflow is written, valid YAML, and
covers install → generate → build index → test → secret scan. It has **never
executed**, because the repository has no remote. A CI file that has not run is
a plan, not a control, and upgrading it on the strength of its own existence is
exactly what this matrix is supposed to prevent.

> **Superseded after Stage 13** — see "Post-submission: CI executed" below. This
> assessment was correct when written; the condition it named has since been
> met, and the upgrade was made on evidence rather than on documentation.

**12 — Monitoring: stays LIGHTWEIGHT.** Telemetry is captured per run and
rendered in the Audit tab; nothing aggregates, retains or alerts. Writing
`eval/final_telemetry_report.md` did not change what the system does.

**6 — Auth: stays PARTIAL.** Authorisation is real, tested through a six-stage
chain, and now correctly audited per run. Authentication does not exist —
persona is a dropdown. No amount of documentation moves this.

## What Stage 13 actually changed in the product

| Change | Category affected | Effect |
|---|---|---|
| Widened the document corpus (13 → 30 distinct texts) | Testing, Storage | Retrieval metrics fell and became honest; **dense retrieval is now justified by measurement**, not just by argument |
| Fixed `build_deterministic_narrative` citing ids the bundle had dropped | Error handling | The fallback path is now genuinely unfailable rather than unfailable by luck |
| Template node now reports its own Gate 2 failure | Error tracking | A blocked template would previously have been delivered silently |
| Corrected the PII claim in the security audit | Security | An overstatement in our own audit, found by inspecting the schema |

## Final matrix

| # | Area | Verdict |
|---|---|:---:|
| 1 | System Design | **REAL** |
| 2 | System Architecture | **REAL** |
| 3 | Frontend | **REAL** |
| 4 | APIs / Backend Logic | **REAL** |
| 5 | Databases / Storage | **REAL** |
| 6 | Auth / Permissions | **PARTIAL** — authorisation real, authentication absent |
| 7 | Hosting / Cloud | **LIGHTWEIGHT** |
| 8 | CI/CD / Version Control | **LIGHTWEIGHT** — workflow present, never executed |
| 9 | Security | **REAL** |
| 10 | Caching / CDN | **LIGHTWEIGHT** |
| 11 | Error Tracking / Logs | **REAL** |
| 12 | Monitoring / Alerts | **LIGHTWEIGHT** |
| 13 | Testing | **REAL** |
| 14 | Scaling | **DEFERRED** |

**8 REAL · 1 PARTIAL · 4 LIGHTWEIGHT · 1 DEFERRED** — unchanged from Stage 12,
which is the correct outcome. Stage 13 was an audit stage; it found and fixed
defects, and it did not add capability. A matrix that improved during an audit
would be the suspicious result.

---

# Post-submission: CI executed

The repository was pushed to a GitHub remote. This changed exactly one category,
and it changed it because something *ran*, not because something was written.

## The one upgrade

**8 — CI/CD: LIGHTWEIGHT → REAL.** Stage 13 refused this upgrade and named the
precise condition that would justify it: *"A CI file that has not run is a plan,
not a control."* The workflow has now run. On commit `3ea18fe`, on a clean
`ubuntu-latest` / Python 3.13 runner: **574 tests passed, 0 failed**, 10m 01s
end to end, including a from-scratch dependency install, warehouse generation
and index build. Detail in section 8 above.

The upgrade is on the strength of an execution log, which is what the Stage 13
note asked for.

## Re-examined and still NOT upgraded

**7 — Hosting/Cloud: stays LIGHTWEIGHT.** A GitHub remote is version control,
not hosting. Nothing is deployed; the app still runs only as `streamlit run
app.py` on one machine.

**12 — Monitoring: stays LIGHTWEIGHT.** A CI run producing logs is not
monitoring. Nothing aggregates, retains or alerts on production telemetry.

**6 — Auth: stays PARTIAL.** Unchanged and unchangeable by this event.

## A defect this exposed

Pushing made `README.md` the repository landing page, which surfaced that it had
not been touched since **Stage 2**. It claimed stages 3–13 were "Not started"
and — more seriously — its run instructions **omitted `python -m
retrieval.build_index`**, which produces a failing test run because
`retrieval/embeddings.py` raises rather than degrading when the index is absent.

Worth recording *why* the Stage 12/13 audits missed it: both verified the
commands in `docs/DEPLOYMENT.md` and neither diffed them against the different,
shorter set in the README. "Deployment commands work" was checked against one
document, not against every document that claims to document deployment.

## Final matrix

| # | Area | Verdict |
|---|---|:---:|
| 1 | System Design | **REAL** |
| 2 | System Architecture | **REAL** |
| 3 | Frontend | **REAL** |
| 4 | APIs / Backend Logic | **REAL** |
| 5 | Databases / Storage | **REAL** |
| 6 | Auth / Permissions | **PARTIAL** — authorisation real, authentication absent |
| 7 | Hosting / Cloud | **LIGHTWEIGHT** |
| 8 | CI/CD / Version Control | **REAL** — workflow executed, 574/574 on a clean runner |
| 9 | Security | **REAL** |
| 10 | Caching / CDN | **LIGHTWEIGHT** |
| 11 | Error Tracking / Logs | **REAL** |
| 12 | Monitoring / Alerts | **LIGHTWEIGHT** |
| 13 | Testing | **REAL** |
| 14 | Scaling | **DEFERRED** |

**9 REAL · 1 PARTIAL · 3 LIGHTWEIGHT · 1 DEFERRED.**
