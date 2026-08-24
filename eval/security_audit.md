# Security audit

Scope: secrets handling, the entitlement chain, data-access boundaries, and
what reaches a model or a screen. Every finding below was produced by running
a check, not by reading code and forming an impression.

**Verdict: no P0 or P1 issues. One real defect found and fixed (audit
correlation). Three residual risks stated rather than closed.**

---

## 1. Secrets

| Check | Method | Result |
|---|---|---|
| Hardcoded API keys | regex for `sk-ant-`, `sk-[A-Za-z0-9]{20,}`, `api_key=`, `secret=`, `password=` across `.py/.yaml/.yml/.json/.toml/.md` | **Clean.** One match: `print("    export ANTHROPIC_API_KEY=sk-ant-...")` in `eval/run_llm_eval.py` — a usage hint, not a credential |
| `.env` files | `find . -name ".env*"` | **None exist.** Nothing in the codebase reads one |
| Key sourcing | grep for `os.environ` / `getenv` | **Single source:** `llm/client.py:161`, `api_key or os.environ.get("ANTHROPIC_API_KEY")` |
| Key in telemetry | inspected `LLMResponse.raw_request` | **Safe by allowlist** — see below |
| Key in logs | grep for `api_key` across `llm/`, `graph/`, `ui/` | Only the constructor and a truthiness check. Never formatted into a message |

### `_redact` is an allowlist, not a denylist

`llm/client.py::_redact` keeps six fields — model, max_tokens, temperature,
has_tools, and two *counts* — and drops everything else:

```python
return {
    "model": request.get("model"),
    "max_tokens": request.get("max_tokens"),
    "temperature": request.get("temperature"),
    "has_tools": "tools" in request,
    "system_blocks": len(request.get("system") or []),
    "messages": len(request.get("messages") or []),
}
```

This matters more than a denylist would: prompt content and evidence excerpts
cannot leak into telemetry by being forgotten, because nothing is copied
unless it is named. The API key is not in `request` at all — it lives on the
client — so it could not leak even without redaction.

---

## 2. The entitlement chain — tested end to end

`tests/test_security_chain.py` (9 tests) follows one genuinely restricted
source, `crm_notes` (denied to `ops_lead`), through every stage a document
could escape at:

| Stage | Assertion | Result |
|---|---|---|
| Policy | `crm_notes` in `denied_sources` for ops_lead, absent for analytics_lead | ✅ |
| SQL rows | row filter + column mask applied inside the gateway | ✅ (`tests/test_entitlements.py`) |
| Retrieval candidates | filtered **before** BM25/dense scoring | ✅ withheld count > 0 |
| Ranking | no restricted doc influenced any score | ✅ by construction — filtered earlier |
| EvidenceBundle | no restricted `source_type`; no `withheld:` placeholder | ✅ |
| Bundle derived text | permitted reader's restricted ids **and excerpt fragments** absent from the restricted reader's full bundle JSON | ✅ |
| LLM payload | no restricted id or excerpt; source name confined to withheld metadata | ✅ |
| UI | withheld **count** rendered; notice contains no excerpt or id | ✅ |

### The control that makes the above non-vacuous

`test_the_restricted_source_is_genuinely_present_for_a_permitted_reader`
asserts 334 `crm_note` documents exist and that `analytics_lead` retrieves
them. Without it, every absence assertion could pass because the data was
simply missing.

### Filter-before-rank is the load-bearing decision

Filtering after ranking would let a restricted document influence the scores
of everything around it — which leaks information about its existence and
content even when the document itself is dropped. The order is asserted, not
assumed.

### Persona switching does not bleed

`test_repeated_scenario_switching_does_not_bleed_entitlement` runs
restricted → permitted → restricted in one process and asserts the third run
matches the first. A cache serving a permitted result to a restricted reader
would fail here.

---

## 3. Finding: audit correlation was broken (FIXED)

**Severity: medium — audit integrity, not access control.**

`security/audit.py` held `_CURRENT_RUN_ID` as a module global, set lazily on
first use and never reset.

**Measured before the fix:** two graph runs produced 21 audit rows under a
**single** id, and that id matched *neither* run
(`R-9e61038a50`, `R-6a43dfaf7e` vs audit `8c51dd29444f`). The `run_id` column
existed and correlated nothing — the log could not answer "which reads belong
to which analysis", which is most of what an audit log is for.

A second problem the same global carried: Streamlit serves each session on its
own thread, so two concurrent analysts would have interleaved under whichever
id was written last.

**What was never affected:** `actor`, `role`, `decision`, `rows_returned`,
`items_withheld` and `columns_masked` are passed per query from the live
principal. Access control and its record were always correct.

**Fix.** `ContextVar` plus an explicit `set_run_id()`, bound by `graph/run.py`
at the start of every run and every resume.

**Measured after:** 2 runs → 2 distinct audit ids, exactly equal to the graph
run ids. Three regression tests, including one that runs two threads and
asserts they do not share an id.

---

## 4. What reaches a model

| Control | Mechanism | Test |
|---|---|---|
| No tool access | The request has **no `tools` key** — absent, not empty | `test_the_client_never_offers_tools` |
| No database handle | `llm/` imports `evidence` and `verification` only; never `semantic.gateway` | import-graph audit: 0 cycles, no edge |
| No confidence invention | `Narrative` has **no `confidence` field** | `tests/test_verification.py` |
| No lever invention | `validate_lever_id` raises `LeverHallucination` on an unknown id | `tests/test_recommendation.py` |
| No number invention | Gate 2 numeric allowlist checks every figure against the frozen bundle | `tests/test_verification.py` |
| Frozen input | Payload built from a hashed, immutable `EvidenceBundle` | `verify_hash` |

A model that cannot query cannot fabricate a query result. This is
architectural rather than behavioural, which is why LangChain's agent layer is
excluded (CLAUDE.md rule 2; `test_no_autonomous_agent_constructs`).

---

## 5. No stack traces in the business view

`ui/safe.py` provides two boundaries — `panel()` per section and `screen()`
per tab. A failure renders a sentence and records the traceback for the Audit
tab. Verified across all 8 scenarios: zero occurrences of
"could not be displayed" in the rendered walkthrough output, and zero raw
`CheckResult(...)` / `SourceType.` reprs.

Stage 11's QA also removed the two remaining paths that printed raw detector
strings on the Workspace (P2-03).

---

## 6. PII

**Corrected in Stage 13.** This section previously claimed the dataset has
"no names, emails, addresses". That was an overstatement, found by inspecting
the schema rather than trusting the claim.

`fact_orders` carries a **`customer_email`** column — 91,329 distinct values of
the form `cust_ea50249@example.com`. What is true:

- Every value is synthetic, generated from the seed.
- `example.com` is **RFC 2606 reserved** and non-routable, so no value can correspond to a real mailbox.
- The column is **not** in any KPI contract's `column_map`, so it is never selected by `guarded_query` and cannot reach an analysis, a bundle, an LLM payload or the UI.

What remains true as originally stated: accounts are opaque ids (`A1234`,
`C00001`), and there are no names, addresses, payment details or free-text
personal information. `distinct_accounts` is rendered as a **count**, never a
list.

The honest summary is therefore "no real personal data, and one
email-shaped synthetic column that never leaves the warehouse" — not "no PII
fields exist".

`distinct_accounts` appears on cohort cards as a **count**, never as a list.

---

## 7. Residual risks — stated, not closed

### 7.1 The embedding index is single-tenant

`data/embedding_index/` contains vectors for all 1,341 documents, including
334 `crm_note` records restricted from `ops_lead`.

**Why this is acceptable here:** the index stores **doc ids and 384-dim
vectors only — no text**. Excerpts live in DuckDB behind the gateway. An
attacker holding the index file gets ids and float arrays, not content. Access
control is enforced at query time before ranking, and tested.

**Why it would not be acceptable in production:** embedding inversion attacks
can recover approximate text from vectors, and the artefact is a single file
crossing all tenants. `docs/PRODUCTION_EVOLUTION.md` names per-tenant indexes
or a vector store with row-level security as the migration, and the trigger:
the first real customer with contractual data-isolation requirements.

### 7.2 Withheld source *names* are disclosed

The UI and the LLM payload state that *n* items from `crm_note` were withheld.

This is deliberate — Architecture 7.6 treats the withheld count as a stronger
trust signal than a silently shorter list — and `security/policy.yaml` carries
no non-disclosure rule. But if a future policy classified source *names* as
sensitive, this would need a per-source `disclose: false` flag. The
capability does not exist today.

### 7.3 No authentication

Persona is chosen from a dropdown. There is no login, no session identity, no
authorisation of the *choice* of persona — anyone running the app can read as
any persona.

This is correct for a single-user local prototype and completely unacceptable
in production. The entitlement engine is real and tested; what is missing is
proof that the caller *is* who they claim. Production evolution: enterprise
IAM supplying a verified identity to `Principal`, at which point every existing
entitlement test continues to apply unchanged.

---

## Summary

| Category | Status |
|---|---|
| Hardcoded secrets | **None** |
| `.env` leakage | **None** — no such file exists |
| Credentials in logs/telemetry | **None** — allowlist redaction |
| Restricted data in SQL / attribution / ranking / bundle / payload / UI | **None** — 9-test chain, with a non-vacuity control |
| Stack traces in business UI | **None** — two-level error boundary |
| LLM database or tool access | **None** — architecturally impossible |
| Unnecessary PII | **None** — synthetic, opaque ids |
| Audit correlation | **Was broken, now fixed and tested** |
| Authentication | **Absent by design** — documented residual risk |
