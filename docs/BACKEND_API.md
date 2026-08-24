# Backend interfaces

There is no HTTP API. The application is one Python process, and adding
FastAPI would create a network boundary with nothing on the other side of it —
Stage 12 forbids infrastructure added for appearance.

What exists instead is a small set of **typed Python contracts**, each of which
is a real boundary enforced by a test rather than a convention.

---

## The application entrypoint

Everything the UI can do is these three functions. `tests/test_ui.py` asserts
that **only `ui/state.py`** may call them.

```python
from graph.run import InsightRequest, run_insight, resume_review, pending_review

result: RunResult = run_insight(
    InsightRequest(
        persona_id="meera",              # who is asking
        kpi_id="net_revenue",            # what about
        window=Window(start=..., end=...),
        slice_filter={"region": ["West"]},
        cause_date=date(2026, 7, 12),    # optional; anchors the counterfactual
        scenario_id="S1",                # optional; demo provenance
        run_id="",                       # optional; auto-minted if omitted
    ),
    graph=None,          # compiled graph; built if omitted
    index=None,          # embedding index; loaded if omitted
    client=None,         # LLM client; None -> deterministic template
    history_days=229,
    has_stable_baseline=True,
)
```

| Function | Purpose | Returns |
|---|---|---|
| `run_insight(request, …)` | Execute one analysis to a terminal state, or to the human interrupt | `RunResult` |
| `pending_review(run_id, …)` | What a paused run is waiting for, without resuming it | `dict \| None` |
| `resume_review(run_id, response, …)` | Continue a paused run with a typed analyst outcome | `RunResult` |

### Contract notes that are load-bearing

- **`run_id` is fresh per call** unless supplied. Reusing one replays a checkpoint rather than executing (ADR-032). Tests and eval scripts pass explicit ids deliberately, for reproducible fixtures.
- **`client=None` is a supported mode**, not degradation. The graph routes to the verified deterministic template.
- **Runtime handles never enter graph state.** `client` and `index` travel in `config["configurable"]` under a `__` prefix, which LangGraph excludes from checkpoint metadata.

---

## `RunResult` — the only thing the UI consumes

```python
@dataclass
class RunResult:
    run_id: str
    terminal: TerminalState          # one of 11
    terminal_reason: str
    persona_id: str
    kpi_id: str
    scenario_id: str | None

    detection: DetectionResult | None      # present even when no bundle exists
    narrative: Narrative | None
    verification: VerificationReport | None
    confidence: Confidence | None
    recommendations: RecommendationSet | None
    deferral: DeferralDecision | None
    analyst_packet: AnalystPacket | None
    bundle: EvidenceBundle | None

    telemetry: RunTelemetry | None
    lineage: list[LineageRecord]
    interrupted: bool
    thread_id: str

    def as_dict(self) -> dict: ...   # fully JSON-serialisable
```

`detection` is carried separately from `bundle` on purpose: a run that abstains
at the coverage gate has no bundle, but the abstention screen still needs to
say *"52 of 56 days"*. Without it the UI could only say "not enough history"
and not how much was missing.

---

## Module contracts

Each is a typed function with no side effects on the caller's state. This is
the layering the import-graph audit confirms: **0 circular imports**.

| Module | Entrypoint | In | Out |
|---|---|---|---|
| `semantic.gateway` | `guarded_query(kpi_id, window, dims, principal)` | ids + `Principal` | `MetricSeries` |
| `security.entitlements` | `decide(principal, contract)` | `Principal`, `KPIContract` | `AccessDecision` |
| `detection.engine` | `detect(kpi_id, window, principal, …)` | ids + `Principal` | `DetectionResult` |
| `attribution.engine` | `attribute(detection, principal, …)` | `DetectionResult` | `AttributionResult` |
| `retrieval.engine` | `retrieve_evidence(attribution, principal, …)` | `AttributionResult` | `RetrievalResult` |
| `evidence.bundle` | `freeze_evidence_bundle(…)` | all of the above | `EvidenceBundle` (frozen, hashed) |
| `verification.engine` | `verify_narrative(bundle, narrative)` | frozen bundle | `VerificationReport` |
| `confidence.engine` | `compute(bundle)` | frozen bundle | `Confidence` |
| `recommendation.engine` | `recommend(bundle, confidence)` | frozen bundle | `RecommendationSet` |
| `deferral.engine` | `decide(bundle, confidence, recommendations)` | frozen bundle | `DeferralDecision` |

Every one takes a `Principal` or a frozen bundle. None reads global state to
find out who is asking.

---

## Boundaries that are enforced, not merely documented

| Boundary | Enforcement | Test |
|---|---|---|
| One DuckDB caller | no other runtime module imports `duckdb` | `test_gateway_is_the_only_module_importing_duckdb` |
| One query entrypoint | gateway exposes exactly one | `test_gateway_exposes_exactly_one_query_entrypoint` |
| Generator unreachable at runtime | no import edge | `test_generator_is_not_reachable_from_runtime_code` |
| UI computes nothing | `ui/` imports no analytical engine | `test_the_ui_never_imports_the_analytical_layer` (7 modules) |
| One door into the backend | only `ui/state.py` may start a run | `test_only_one_module_can_start_a_graph_run` |
| Backend never imports Streamlit | verified by import scan | *(audit; no backend file imports it)* |
| Graph nodes stay thin | nodes call modules, never compute | reviewed: max 9 statements per node |
| No LLM in routing | predicates asserted against their own **source** | `test_no_routing_predicate_reads_a_narrative` |
| No LangChain | `import langchain` absent from `graph/` | `test_no_direct_langchain_import_anywhere_in_the_graph_package` |
| No agents | no `create_agent`, `ToolNode`, `bind_tools` | `test_no_autonomous_agent_constructs` |

---

## Global state

Three module-level globals exist, all deliberate:

| Global | Module | Justification |
|---|---|---|
| `_conn` | `semantic/gateway.py` | The single DuckDB connection — the chokepoint itself. Guarded by a `threading.Lock`. |
| `_model` | `retrieval/embeddings.py` | Cached sentence-transformer. Read-only after load; loading it twice costs ~60 s. |
| `_RUN_ID` | `security/audit.py` | **`ContextVar`, not a plain global** — changed in Stage 12 after measuring that a module global gave one audit id per *process* rather than per run, and would interleave across Streamlit's per-session threads. |

No other mutable module state exists in the backend packages.

---

## Duplicated business logic

Audited: none found. The near-misses that were checked —

- **Materiality** is decided once, in `detection/`. `graph/routing.py::route_materiality` reads `DetectionResult.outcome` rather than re-deriving it from `pct_delta`, precisely so the two cannot drift.
- **Ambiguity** is computed once. ADR-029 removed the second implementation in Gate 1b after it fired on S2 and discarded the analyst packet the deferral engine would have built.
- **Impact** is *read* from the measured movement in `recommendation/`, never recomputed.
