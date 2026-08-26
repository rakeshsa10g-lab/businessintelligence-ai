# BusinessIntelligence.ai — End-of-Stage-11 Browser-Based QA Report

**Date:** 2026-08-24  
**Evaluator:** Antigravity Browser QA Agent  
**Environment:** Chrome 151.0 (Headless & CDP), Streamlit 1.40+, Windows 10/11  
**Target Application:** [`app.py`](file:///c:/Users/rakes/dev/businessintelligence-ai/app.py) (Decision Workspace)  
**Test Scope:** Live interactive browser execution across all 8 scenarios (**S1, S2, S3, S4, S5a, S5b, S6, S7**), statefulness, security, accessibility, telemetry, and Growth.Design UX mapping.

---

## 1. Application Launch & Lifecycle Verification

| Evaluation Check | Status | Live Observation |
|---|:---:|---|
| **Startup Cleanliness** | **PASS** | Server boots cleanly via `streamlit run app.py` on default port `8501`/`8503` with Uvicorn backend. |
| **Initial Render** | **PASS** | Default landing view loads `S1` (`Meera · Analytics Lead`) on the `Workspace` tab with full masthead, KPI movement, driver breakdown, evidence summary, reliability card, and recommended action. |
| **Navigation & Tabs** | **PASS** | All 4 tabs (`Workspace`, `Evidence`, `Method`, `Audit`) switch instantaneously (<0.2s) without re-triggering backend analysis. |
| **Scenario Selection** | **PASS** | Sidebar selectbox updates scenario cleanly. |
| **Persona Selection** | **PASS** | Dynamically scopes available personas to the chosen scenario. |
| **Reruns & Stale State** | **PASS** | Scoped widget keys (`persona_pick_{scenario.id}`) prevent session state retention bugs across scenario transitions. |

---

## 2. Comprehensive Scenario Evaluation (The 5 Business Questions)

Each scenario was executed in the live browser and evaluated against the five core questions a business decision-maker asks:

```
1. What changed?  →  2. Why?  →  3. Evidence?  →  4. How reliable?  →  5. What next?
```

| Scenario ID & Title | 1. What changed? | 2. Why did it move? | 3. What evidence supports it? | 4. How reliable is it? | 5. What should happen next? |
|---|---|---|---|---|---|
| **S1: West Revenue (High Confidence)** | Net Revenue in `West × Web/Mobile App` fell **25.0%** (12 Jul → 26 Jul 2026; 52.8k INR drop). | Conversion rate accounted for **109.9%** of movement (offset by basket size/sessions). | 7 supporting items (gateway deploy changelog + checkout failure tickets). | **High reliability** (12/12 synthetic calibration cases; caveat stated inline). | **Raise request:** Escalate payment gateway to Engineering Lead (622k–800k INR recovery). |
| **S2: South × Apparel (Conflicted Evidence)** | Net Revenue in `South × Apparel` fell **21.9%** (02 Jun → 16 Jun 2026; 12.5k INR drop). | Conversion rate accounted for **100.5%** of movement. Two competing hypotheses (*competitor promo* vs *stockout*). | 6 supporting · 1 contradicting (early competitor discount note). | **Uncalibrated** (only 2 comparable past cases; hit rate not quoted). | **Human Review:** Analyst chooses between competing hypotheses via LangGraph interrupt. |
| **S3: East × SMB (Thin Evidence)** | Net Revenue in `East × SMB` fell **18.6%** (08 Aug → 11 Aug 2026; 12.7k INR drop). | Conversion rate accounted for 82% of movement; data-definition change hypothesis unverified. | 1 supporting · 1 contradicting. | **Uncalibrated** (insufficient empirical history). | **Human Review / Abstain:** Names missing data source needed to establish causal link. |
| **S4: NewLaunch (Sparse History)** | **No movement measured** (52 days available vs 56 needed for seasonal baseline). | Cannot separate weekly seasonality from real movement without baseline. | None (sparse gate tripped before retrieval). | Not assessed (coverage gate rejected). | **Wait:** ~4 more days of observations until baseline converges automatically. |
| **S5a: West Revenue (Priya · Ops Lead)** | Net Revenue in `West × Web/Mobile App` fell **25.0%**. | Platform/gateway failure impacting checkout conversion. | 7 supporting items. | High reliability (12/12 cases). | **Raise request:** Operational escalation to Engineering Lead. |
| **S5b: West Revenue (Arjun · Finance Director)** | Net Revenue in `West × Web/Mobile App` fell **25.0%**. | Platform/gateway failure impacting checkout conversion. | 7 supporting items. | High reliability (12/12 cases). | **Evaluate & Request:** Evaluates financial stakes with director-level loss threshold. |
| **S6: West (Priya · CRM Withheld)** | Net Revenue in `West × Web/Mobile App` fell **25.0%**. | Platform failure in checkout flow. | Permitted sources displayed; **CRM notes withheld**. | High reliability (12/12 cases). | **Raise request:** Operational ticket raised without exposing restricted CRM records. |
| **S7: Marketplace Rename (Schema Change)** | Net Revenue in `Marketplace` rose **5.9%** (**Below materiality threshold**). | Channel renamed `marketplace` → `Marketplace` on 14 Jun 2026 (data artifact). | Schema changelog recorded. | Not applicable (no business movement). | **No action:** Quiet screen confirms no operational or marketing intervention needed. |

---

## 3. First-Time-User Experience (S1 30-Second Test)

* **Test Subject Perspective:** Business Executive / Analyst seeing the tool for the first time.
* **Landing Screen:** S1 default Workspace tab.
* **30-Second Glance Results:**
  * **KPI Movement:** **Instantly obvious.** `↓ 25.0%` in 3.1rem high-contrast type alongside segment and dates.
  * **Materiality:** **Instantly obvious.** `Material movement` pill adjacent to the percentage.
  * **Primary Driver:** **Instantly obvious.** Blue `ANALYTICAL RESULT` card naming `conversion rate`.
  * **Evidence:** **Partially obvious.** Summary counter (`7 supporting`) visible; detailed ticket excerpts require switching to the Evidence tab.
  * **Reliability:** **Instantly obvious.** Dedicated `High reliability` card with inline synthetic caveat.
  * **Action:** **Instantly obvious.** Amber `RECOMMENDATION` banner with owner, monitor period, and expected recovery.
* **Verdict:** **PASS.** All primary questions answered on the default screen without tab switching.

---

## 4. Visual QA & Aesthetics

* **Typography & Hierarchy:** Clear typographical scale. Level 1 movement headline (`3.1rem`) dominates, followed by section markers (`.bi-sec`, uppercase 0.7rem), and claim cards (`.bi-claim`).
* **Color Discipline:** Strict adherence to epistemic palette:
  * **Purple (`#6b4e9e`):** `HYPOTHESIS`
  * **Blue (`#1f4788`):** `ANALYTICAL RESULT` / Primary Accent
  * **Amber (`#8a5a1f`):** `RECOMMENDATION` / `CAUTION`
  * **Green (`#2f6f4e`):** Supporting Evidence / High Reliability
  * **Red (`#a33a3a`):** Strictly reserved for `CONTRADICTS` evidence chips and hard verification failures.
    > **Corrected after the product/judge audit.** This was false at the time it was written: `ui/components/drivers.py` also paints negative contribution bars red, which the S1 hero screenshot shows plainly. The rule is now the broader and accurate one — **red = adverse** (negative contribution, or evidence arguing against the hypothesis). See `eval/growth_design_ux_mapping.md`. Left in place rather than rewritten, because what this QA pass actually checked is part of the record.
* **Driver Visualization:** Zero-anchored horizontal bars correctly represent contribution shares. For S1 (109.9% conversion rate), offsetting negative factors are explicitly drawn and annotated.
* **Abstention Screens:** S4 and S7 render visibly quieter surfaces (no noisy charts or fake action blocks).

---

## 5. Interaction & Statefulness QA

* **Tab Switching:** Instantaneous re-rendering from `st.session_state` without re-running backend SQL/retrieval.
* **Rapid Scenario Switching:** Tested transitions `S1 → S6 → S1 → S5a → S7 → S2`. Scoped widget keys (`persona_pick_{scenario.id}`) properly reset the persona dropdown to scenario defaults (e.g. S1 defaults to Meera, S6 defaults to Priya).
* **No Stale Widget / Run-ID Bleed:** Analysis results accurately match the active scenario ID in the masthead and run metadata.

---

## 6. S6 Security & Entitlement Chokepoint Audit

* **Security Policy Rule:** Priya (`ops_lead`, `West`) is prohibited from viewing `crm_notes`.
* **DOM & Source Inspection:**
  * **Zero CRM notes appear in the rendered HTML/DOM on Workspace or Evidence tabs.**
  * No tooltips, title attributes, or hidden elements contain CRM text.
  * Evidence summary and Audit tab explicitly record: `"0 permitted, 2 withheld by entitlement"`.
  * Lineage metadata confirms filtering occurred *before* vector ranking at `security/entitlements.py`.

---

## 7. S2 & S3 Human Review Interaction

* **Terminal State:** `REVIEW_REQUIRED` pauses execution via LangGraph checkpoint interrupt.
* **Decision Screen:** Renders `AWAITING YOUR DECISION` banner clearly distinguishing review from failure.
* **Review Controls:** Interactive radio selection offering 4 typed resume options:
  1. *Approve leader hypothesis*
  2. *Override primary driver*
  3. *Dismiss finding as non-actionable*
  4. *Request additional telemetry*
* **Resumption:** Clicking `"Submit and resume the run"` resumes execution at the interrupted checkpointer.

---

## 8. S4 Sparse History Semantic Invariant

* **Materiality Invariant:** **PASSED.** The UI does **not** assert a materiality verdict. Both `Material movement` and `Below materiality threshold` chips are suppressed.
* **Coverage Feedback:** States `52 days available vs 56 days required` and provides actionable guidance to wait ~4 days for baseline convergence.

---

## 9. S7 Schema Anomaly Negative Invariant

* **Anomaly Invariant:** **PASSED.** Correctly classified as a data artifact (`Below materiality threshold` / `No material event`).
* **Noise Suppression:** Suppresses false root cause explanations, false operational alerts, and unwarranted recommendations.

---

## 10. Verified Template Mode Disclosure

* **Disclosure Rule:** When `ANTHROPIC_API_KEY` is not present, narratives are produced by the deterministic template engine.
* **Verification:**
  * Sidebar carries explicit notice: *"No ANTHROPIC_API_KEY is configured in this environment, so narratives come from the verified deterministic template."*
  * Method and Audit tabs display `Verified template mode` chip with zero hallucinated LLM calls (`llm_calls = 0`).

---

## 11. Method & Audit Views

* **Lineage & Contract:** Displays 15-step cryptographic trace (KPI contract version, entitlement decision, detection method, DiD counterfactual stats, RRF retrieval weights, Gate 2 verification checks).
* **Node Timings:** Detailed execution breakdown table (`attribute` ~13.8s, `retrieve` ~23.9s, `detect` ~0.4s).
* **Cleanliness:** No unhandled Python object reprs or internal memory addresses leaked to the user.

---

## 12. Growth.Design UX Principles Audit

| Principle | Implemented Mechanism | Live Product Verification |
|---|---|:---:|
| **Absent Uncertainty Markers** | Inline qualifiers on all reliability figures | **YES.** `HIGH RELIABILITY` paired with `Correct in 12 of 12 similar past cases (synthetic set)`. |
| **Colour Discipline** | Restrained palette; red reserved for contradiction | **YES at the time — since corrected.** This pass concluded red was used *only* for `CONTRADICTS` chips and hard verification failures. It missed the driver chart, which paints negative bars red. The rule is now **red = adverse**; see the note above and `eval/growth_design_ux_mapping.md`. |
| **Proportional Scale** | Zero-anchored driver axis representing actual share | **YES.** Offset effects over 100% are explicitly visualized and annotated. |
| **Recognition over Recollection** | Level 1 movement headline dominates visual hierarchy | **YES.** `↓ 25.0%` is the single largest element on the page. |
| **Actionability Gap** | Every state names a concrete next step | **YES.** Findings offer buttons; abstentions name wait times or missing sources. |
| **Habituation through Irrelevance** | Non-events render visibly quieter | **YES.** S4/S7 omit noisy charts and fake action blocks. |
| **Show Work Honestly** | Real execution stages ticked as they complete | **YES.** Progress panel reflects actual graph nodes in business language. |
| **Paradox of Choice** | Limit visible options (3 drivers, 2–3 hypotheses) | **YES.** Top 3 drivers shown with expandable drill-down. |
| **Mental Models** | Tab order structured around user questions | **YES.** Sequence is *Workspace → Evidence → Method → Audit*. |
| **Framing of Ranges** | Expected recovery expressed as range | **YES.** Renders `622,121 – 799,870 INR` with recovery basis explained. |
| **Zeigarnik Effect** | Unfinished review states remain open and actionable | **YES.** `REVIEW_REQUIRED` stays open until resumed via typed action. |

---

## 13. Accessibility & Usability

* **Readability:** Base font sizes 0.85rem–1.05rem with 1.5–1.6 line height.
* **Color Independence:** All semantic badges combine color with explicit text labels (`SUPPORTS`, `CONTRADICTS`, `MATERIAL MOVEMENT`).
* **Visual Focus:** Streamlit native focus rings remain active across selectboxes and primary buttons.

---

## 14. Performance & Telemetry

* **Application Startup:** ~2.5s (cached embedding index and checkpointer).
* **S1 End-to-End Execution:** ~53.7s (LMDI attribution + 400-resample bootstrap + dense embedding retrieval).
* **S4 / S7 Execution:** <0.6s (rapid abstention gate exit).
* **Tab & View Rerenders:** <0.2s (in-memory session state).

---

## 15. Captured Visual Artifacts

The following live screenshots were captured via Chrome DevTools Protocol:
* [s1_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s1_workspace.png) — S1 Workspace View (Finding, Driver, Recovery)
* [s1_evidence.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s1_evidence.png) — S1 Evidence Tab (Deploy Logs & Support Tickets)
* [s2_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s2_workspace.png) — S2 Review Required & Competing Hypotheses
* [s3_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s3_workspace.png) — S3 Thin Evidence & Uncalibrated Reliability
* [s4_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s4_workspace.png) — S4 Sparse History Quiet Screen
* [s5a_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s5a_workspace.png) — S5a Operations Lead Perspective
* [s5b_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s5b_workspace.png) — S5b Finance Director Perspective
* [s6_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s6_workspace.png) — S6 Security Entitlement Redaction View
* [s7_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s7_workspace.png) — S7 Schema Change Anomaly Screen

---

## 16. Systematic Issue Log

### P0 — Submission Blockers
* **None identified.** No runtime crashes, security breaches, hallucinated figures, or blocking interaction defects exist.

---

### P1 — Important (Functional & Reliability)

#### [P1-01] LangGraph Checkpointer Emits Pandas Timestamp Deserialization Warnings
* **Severity:** P1
* **Scenario:** S2, S3, and checkpointed review resumption
* **Reproduction:** Route any run to `REVIEW_REQUIRED` or restore state from the SQLite checkpointer (`graph_checkpoints.sqlite`).
* **Expected:** Checkpointer cleanly serializes and restores graph state without unpickling safety warnings.
* **Actual:** `langgraph-checkpoint-sqlite` logs stderr warnings: `Blocked deserialization of method call pandas.Timestamp.fromisoformat - not in allowed methods set.` due to LangGraph 1.2+ security allowlist restrictions.
* **Artifact / Log:** `task-263.log`
* **Recommended Fix:** In `graph/build.py` / `graph/run.py`, ensure all timestamp fields stored in graph state are serialized as ISO-8601 strings or native Python `datetime.date`/`datetime.datetime` before passing to the checkpointer.

---

### P2 — Polish (UX & Visual Hierarchy)

#### [P2-01] Raw Mathematical Inequality Rendered on Workspace Tab
* **Severity:** P2
* **Scenario:** S1, S5a, S5b (Workspace Tab)
* **Reproduction:** Open S1 and inspect the bottom of the `Recommended action` section.
* **Expected:** Expected loss rationale should be presented in plain business language on the primary Workspace tab.
* **Actual:** Displays raw mathematical formula: `E[loss|model] 53,571 < E[loss|human]+review 128,250 INR; review would cost more than the accuracy it buys`.
* **Artifact:** [s1_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s1_workspace.png)
* **Recommended Fix:** Translate the inequality into plain business prose on the Workspace tab (e.g., *"Automated action approved: estimated delay and review costs exceed decision risk"*), confining raw mathematical notation to the Method/Audit tabs.

#### [P2-02] Blank Cohort Cards Rendered on Workspace Tab
* **Severity:** P2
* **Scenario:** S1, S2, S6 (Workspace Tab)
* **Reproduction:** Scroll down to the Evidence summary section on the Workspace tab.
* **Expected:** Cohort cards should only render when populated with summary counts, or be confined to the Evidence tab.
* **Actual:** Blank cohort containers (`payment tickets`, `gateway CRM notes`, etc.) appear with empty metadata and body blocks.
* **Artifact:** [s1_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s1_workspace.png)
* **Recommended Fix:** In `ui/components/evidence.py` (`render_summary`), suppress cohort cards that lack body content or count metrics.

#### [P2-03] Raw Diagnostic String Displayed on S7 Abstention Screen
* **Severity:** P2
* **Scenario:** S7 (Schema Change)
* **Reproduction:** Select scenario S7 in the sidebar and view the Workspace tab.
* **Expected:** Clean styled `No material event` abstention card.
* **Actual:** Below the abstention card, an unstyled diagnostic debug string is rendered: `net_revenue [channel=Marketplace]: statistical_signal=True, business_materiality=False -> NO_MATERIAL_FINDING. not material: |effect| 105,986 below 250,000 INR and |relative| 3.30% below 9.0%`.
* **Artifact:** [s7_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s7_workspace.png)
* **Recommended Fix:** Remove raw diagnostic text output from `ui/components/abstention.py` / `movement_view.render` and confine diagnostic output to the Audit tab.

#### [P2-04] Verified Template Mode Sidebar Caption Contrast
* **Severity:** P2
* **Scenario:** All Scenarios (when `ANTHROPIC_API_KEY` is not configured)
* **Reproduction:** Inspect the sidebar caption and Method tab narration badge.
* **Expected:** High-contrast disclosure that the narrative is generated via the verified deterministic template rather than an unconstrained LLM.
* **Actual:** The sidebar caption is rendered in low-contrast light grey (`#8b95a5`), which can be overlooked by evaluators.
* **Artifact:** [s1_workspace.png](file:///C:/Users/rakes/.gemini/antigravity/brain/c2fd5c7b-0afa-4570-995e-cb4c226fcb24/s1_workspace.png)
* **Recommended Fix:** Elevate the deterministic template badge to a visible pill in the masthead or sidebar header.

---

## Top 5 Issues

1. **[P1-01] LangGraph SQLite Checkpointer Timestamp Deserialization Warnings:** Checkpointed resumes emit serialization safety warnings for `pandas.Timestamp` types (`Blocked deserialization of method call pandas.Timestamp.fromisoformat`).
2. **[P2-01] Raw Mathematical Inequality in Workspace Tab:** `E[loss|model] < E[loss|human]` is too technical for general decision-makers.
3. **[P2-02] Empty Cohort Cards on Main Workspace Screen:** Blank card containers rendered in the evidence summary section.
4. **[P2-03] Unstyled Diagnostic Debug Output on S7 Screen:** Raw backend gate diagnostic string is printed beneath the abstention container.
5. **[P2-04] Verified Template Mode Sidebar Caption Contrast:** Low visual hierarchy for template narration disclosure in headless/unkeyed environments.

---

### Overall Verdict

### **READY WITH FIXES**

The prototype meets all functional, statistical, and security requirements across scenarios S1–S7. All core invariants (chokepoint enforcement, no hallucinated numbers, persona-based entitlement redaction, and strict abstention criteria) are fully operational and verified in the live browser. Addressing the minor presentation and checkpointer serialization items listed above will achieve complete production-grade polish.

---

## 17. Resolution status — all five findings

Applied 2026-08-24, after the browser QA above. Every fix carries a regression
test; the verification quoted here is measured output, not intent.

| ID | Finding | Status | Fix |
|---|---|:---:|---|
| **P1-01** | `pandas.Timestamp` deserialization warnings on checkpoint resume | **RESOLVED** | Normalised at the type boundary, not the serialiser |
| **P2-01** | Raw expected-loss inequality on Workspace | **RESOLVED** | Business prose on Workspace; exact notation moved to Method |
| **P2-02** | Blank cohort cards | **RESOLVED** | Cards read the real fields; empty cohorts are not rendered |
| **P2-03** | Raw diagnostic string on S7 | **RESOLVED** | Removed from Workspace; raw reason surfaced in Audit |
| **P2-04** | "Verified template mode" too subtle | **RESOLVED** | Telemetry-driven chip replacing a static grey caption |

---

### P1-01 — root cause and fix

**Root cause.** `pandas.Timestamp` subclasses `datetime.datetime`, so Pydantic
accepts it for a field annotated `datetime` and silently keeps the pandas
type. `EvidenceRef.timestamp` and `EvidenceItem.timestamp` are populated from
rows read through pandas, so seven Timestamp objects per S2 run reached graph
state. LangGraph's allowlist then refused to deserialise them on every restore
and fell back — nothing crashed, which is why it survived two stages.

**Fix.** `semantic.types.PlainDateTime` — an annotated `datetime` carrying a
`BeforeValidator` that converts any `datetime` *subclass* to an exact
`datetime`, preserving the instant and `tzinfo`. Applied to the fields whose
values originate in pandas (`retrieval.types.EvidenceItem.timestamp/as_of`,
`RetrievalResult.retrieved_at`, `evidence.types.EvidenceRef.timestamp` and the
four `as_of` fields). The warning is not suppressed — the value that produced
it no longer exists.

Writing the test found a second defect in the fix itself: `pd.NaT` is *not* a
`Timestamp` subclass (it is `NaTType`) but *is* an `isinstance` of `datetime`,
and all its components are `nan`. The first ordering of the branches sent NaT
into the reconstruction path and raised
`'float' object cannot be interpreted as an integer`. NaT is now checked first.

**Verification** (validation harness, both serialization modes):

```
S2:  reached review True · interrupted True · question shown True
     resumed same run id True (QA-S2) · bundle hash identical True
     pandas.Timestamp in checkpointed state: NONE
S3:  reached review True · interrupted True · question shown True
     resumed same run id True (QA-S3) · bundle hash identical True
     pandas.Timestamp in checkpointed state: NONE

Blocked-deserialization warnings, normal mode : 0
Blocked-deserialization warnings, strict mode : 0
Bundle hashes identical under strict mode     : yes (no silent degradation)
Full 8-scenario walkthrough warning count     : 0
```

Four regression tests: a whole-state scan asserting no `pandas.Timestamp` can
reach the checkpoint (it scans everything, so a *future* field that starts
carrying one fails here); an instant/timezone-preservation test including the
NaT case; and a live-run assertion on `EvidenceRef.timestamp`.

*No ADR was written.* This is an implementation fix — a value normalised to
the type its own annotation already declared. It changed no architecture, no
routing, no analytical logic, and no decision.

---

### P2-01 — business language on the Workspace

`decision.rationale` is written for an audit trail and uses
conditional-expectation notation. Exact, and it asks a business reader to
parse that notation before they can tell whether the system is acting or
asking them to.

`ui/components/recommendation.py::business_rationale()` restates the *same
figures* as money and consequence. Nothing is recomputed:

> **Acting now carries less risk than waiting.** Sending this for manual
> review would cost about **53,250 INR** in analyst time and delay — more than
> the review would be expected to save by catching a wrong call.
>
> Weighing the chance of being wrong against what being wrong would cost:
> acting now is worth about **53,571 INR** of expected risk, against
> **128,250 INR** if this waited for a person — a difference of roughly
> **74,679 INR** in favour of acting.

The exact notation moved to a new **Method** card ("Decision rule
(cost-sensitive deferral)") alongside `p_model`, `p_human`, cost of error and
policy version. Verified in the rendered walkthrough: every occurrence of the
raw inequality across all eight scenarios is inside the Method card or the
Audit "Terminal reason (raw)" row — none on Workspace.

A guardrail case is handled separately: when `override_applied` is set the
arithmetic did not decide, so the prose says so rather than quoting figures
that were not what determined the outcome.

---

### P2-02 — cohort cards

The panel read `document_count`, `count`, `change_vs_baseline` and `summary`
through `getattr` defaults. None are fields on `CohortEvidence` — the real
names are `incident_count`, `baseline_count`, `ratio`, `label`. Every lookup
returned its fallback, so every card rendered as an empty box.

`cohort_is_renderable()` now gates on a label *and* a non-zero
`incident_count`; `_cohort_card()` reads the real fields. Rendered result:

```
payment tickets
35 documents in the event window · none in the 8-week baseline · 35 distinct account(s)

gateway CRM notes   [New in this window]
5 documents in the event window · none in the 8-week baseline · 5 distinct account(s)
```

Two regression tests: one for the suppression rule, one asserting the card
reads only fields that exist on `CohortEvidence`.

---

### P2-03 — raw diagnostics off the Workspace

Removed the `terminal_reason` expander from `no_material_event`, and the
appended raw string from `data_quality` (which on a locked warehouse renders a
literal `IOException`). Both were the only Workspace paths exposing internal
gate names and enum values.

The business screen already carried the numbers a reader needs, phrased as the
threshold actually missed — S7 now ends at:

> The movement was **105,986 INR**, below the **250,000 INR** minimum.

The raw string is now a first-class Audit row, `Terminal reason (raw)`, so
nothing is lost. Verified: the only occurrences of `statistical_signal=` in
S7's rendered output are in the Audit row and the Method caption.

---

### P2-04 — narration status

The sidebar caption was low-contrast grey **and** a static string asserting
that no API key was configured — a claim about the environment rather than
about the run, which would have been actively false had a key been present.

Replaced with a chip in the existing palette, rendered into a sidebar slot
after the run and driven by `narration_mode(result)` — the same function the
Audit tab uses, so all three states stay in lockstep:

| Condition | Chip | Style |
|---|---|---|
| `llm_calls > 0` | `Model-generated, verified` | `support` (green) |
| `llm_calls == 0`, silent terminal | `LLM not required` | `quiet` |
| `llm_calls == 0`, narrative produced | `Verified template mode` | `caution` (amber) |

The template text still ends "No model reviewed this text", so it cannot be
read as implying a model was involved. Live-LLM mode is covered by a test
using a telemetry stub, since no API key exists in this environment.

**Measured:** S1 → `llm_calls=0`, label `Verified template mode`, kind
`caution`, implies-live-model `False`.

---

### What remains unchanged

No analytical logic, detection, attribution, retrieval, LangGraph routing or
`EvidenceBundle` *structure* was modified. The only type-level change is the
`PlainDateTime` annotation, which normalises a value to the type its field
already declared. No dependencies were added.
