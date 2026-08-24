# Error handling and logging report

Every failure mode below is tested by **causing** the fault, not by asserting
a handler exists. A handler with no path to it is untested code that reads as
coverage — which is why `tests/test_graph_failures.py` monkeypatches real
functions to raise, feeds malformed payloads to real clients, and drives real
interrupts.

**35 failure-injection tests. All pass. No raw exception reaches the business
Workspace on any path.**

---

## Layer contract

Each layer carries a `run_id`, handles its own errors, degrades safely, and
exposes technical detail through exactly one channel.

| Layer | `run_id` | Error handling | User-facing behaviour | Diagnostic path | Audit record |
|---|---|---|---|---|---|
| **UI** (`ui/`) | `RunResult.run_id` | `ui/safe.py` — `panel()` per section, `screen()` per tab | A sentence, never a traceback | Audit tab → "Interface diagnostics" | — |
| **Graph** (`graph/`) | minted per run, unique | `instrument()` wrapper catches per node | Typed terminal state | `NodeTelemetry.error` per node | — |
| **Modules** | receive it as a parameter | Typed results, not exceptions, for expected conditions | via the graph | Node telemetry | — |
| **Gateway** (`semantic/`) | `audit.current_run_id()` — now the graph's id | `EntitlementError` is a boundary, not an outage | via the graph | Exception text in Audit | **`audit_log` row per read, including denials** |
| **LLM** (`llm/`) | on the bundle | Failures are **return values**, not exceptions (ADR-025) | Template fallback | `NarrationTelemetry` | — |

The gateway is the only layer that writes an audit record, because it is the
only layer that touches data.

---

## Tested failure modes

| # | Failure | Injection method | Terminal | Test |
|---|---|---|---|---|
| 1 | **Data error** (locked/unreadable warehouse) | real `IOException` observed under DB contention | `ABSTAIN_DATA_QUALITY` | observed in practice; raw text confined to Audit |
| 2 | **Missing/unknown KPI** | request a KPI that does not exist | `CLARIFY_REQUESTED` | `test_unknown_kpi_asks_which_one_rather_than_erroring` |
| 3 | **Broken contract** | monkeypatch `registry.get` to raise | `CONTRACT_ERROR` | `test_a_broken_contract_stays_loud_and_does_not_become_an_abstention` |
| 4 | **Entitlement failure** | force `allowed=False` | `ACCESS_DENIED` | `test_authorization_denial_stops_before_any_data_is_read` |
| 5 | **No material event** | S7, a schema-rename artefact | `NO_MATERIAL_EVENT` | `test_no_material_event_terminates_with_the_numbers` |
| 6 | **Sparse history** | S4, 52 of 56 days | `ABSTAIN_SPARSE_HISTORY` | `test_sparse_history_is_a_path_not_an_error` |
| 7 | **Retrieval error** | monkeypatch `retrieve_evidence` to raise `ConnectionError` | typed terminal; failure on record | `test_retrieval_failure_does_not_take_down_the_run_silently` |
| 8 | **Insufficient evidence** | — | `ABSTAIN_INSUFFICIENT_EVIDENCE` | `test_insufficient_evidence_routes_to_its_own_terminal` |
| 9 | **Conflicting evidence** | S2, two hypotheses within the margin | `REVIEW_REQUIRED` + packet | `test_conflicting_evidence_reaches_review_with_a_packet_not_a_shrug` |
| 10 | **LLM unavailable** | no API key | `VERIFIED_TEMPLATE` | `test_a_missing_llm_is_a_supported_path_not_a_failure` |
| 11 | **LLM API error** | client raises on every call | `VERIFIED_TEMPLATE` | `test_an_api_error_ends_in_the_template_rather_than_an_exception` |
| 12 | **Malformed LLM output** | client returns non-JSON | `VERIFIED_TEMPLATE`, ≤2 calls | `test_malformed_llm_output_falls_back_without_a_third_call` |
| 13 | **Verification failure** (numeric / driver / causal) | three hand-built corrupt narratives | `VERIFIED_TEMPLATE`, 0 hard violations delivered | `test_gate_2_catches_each_violation_class_and_never_delivers_it` |
| 14 | **Retry exhaustion** | persistently bad model | exactly 2 calls, then template | `test_a_persistently_bad_model_is_called_exactly_twice` |
| 15 | **Unbounded retry** (regression) | narrator raises every time | terminates; `gate_2` visited exactly twice | `test_a_narrator_that_raises_every_time_still_terminates` |
| 16 | **Graph runaway** | — | `recursion_limit=40` backstop | `test_the_graph_has_a_recursion_limit_independent_of_the_counter` |
| 17 | **Checkpoint failure** (unserialisable object) | runtime handles on state | handles moved to `config`; strict mode passes | `test_runtime_handles_never_reach_the_checkpoint` |
| 18 | **Stale checkpoint** | re-invoke same scenario | fresh run each time | `test_re_invoking_the_same_scenario_does_not_return_a_stale_run` |
| 19 | **Telemetry failure** | lineage f-string raises | **analysis preserved**, telemetry degraded | `test_a_lineage_failure_degrades_telemetry_and_keeps_the_analysis` |
| 20 | **Human interrupt / resume** | real `interrupt()` on SQLite | same run id, identical bundle hash | `test_every_analyst_outcome_resumes_the_same_run` |

---

## Three principles the tests enforce

### 1. A telemetry failure must never cost the analysis

Found the hard way. A renamed field inside a lineage f-string raised, the
telemetry wrapper marked the node failed, and a perfectly good detection was
discarded into an abstention. Measuring something is not worth losing it.

Lineage construction is now deferred into a closure the wrapper evaluates
inside its own guard: a formatting fault degrades the *record* and the run
continues, with the degradation itself recorded (`lineage degraded: …`).

### 2. A configuration fault must stay loud

An unknown KPI is a question a user can answer → `CLARIFY_REQUESTED`, listing
the real KPIs. A contract that exists but will not parse is a broken
deployment → `CONTRACT_ERROR`. Degrading the second into a polite abstention
would hide a deployment failure behind a conversational message.

### 3. Expected conditions are return values, not exceptions

`llm/client.py` never raises for a model failure — it returns an `LLMResponse`
with a typed `failure_reason` (ADR-025). An expected condition raised as an
exception forces every caller to guess which exceptions are routine.

The same applies at the entitlement boundary: attribution wraps a
`source_reconciliation` call in `try/except EntitlementError`, because a role
that cannot read refund data should get an analysis without that term, not an
outage.

---

## What is *not* covered

- **Disk-full / corrupt-DB.** Not simulated. DuckDB corruption would surface as an exception at the gateway and route to `ABSTAIN_DATA_QUALITY`, but that path was observed opportunistically (under lock contention) rather than deliberately injected.
- **Concurrent-session failures.** The prototype is single-process; concurrency is not tested. The `ContextVar` audit fix removes one known cross-thread hazard, but no multi-session load was exercised.
- **Partial checkpoint corruption.** Deleting the checkpoint file loses paused reviews cleanly; a *truncated* file was not tested.
