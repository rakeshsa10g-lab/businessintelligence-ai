# BusinessIntelligence.ai

A KPI intelligence-to-action engine. It detects material KPI movements, ranks
explanatory drivers, writes persona-specific narratives backed by traceable
evidence, abstains when the evidence does not support a claim, and recommends
actions tied to real business levers.

Accenture Innovation Challenge 2026, Round 2 prototype. Team SouthernHustlers,
Problem Track 3.

> Deterministic SQL and statistics compute every number; a published algorithm
> ranks which dimension moved; hybrid retrieval finds corroborating documents;
> the LLM writes into a validated claim schema it cannot exceed; a deterministic
> verifier checks every number, driver and direction before the words reach a
> human — and when they do not check out, the system abstains rather than
> writing prettier prose.

## Run it

```bash
pip install -r requirements.txt
python -m data.generate     # builds data/warehouse.duckdb, ~30s
pytest -q
```

## Build status

| Stage | Scope | Status |
|---|---|---|
| 0 | Scaffold, deps, config, base models, test framework | Done |
| 1 | Synthetic dataset, injected events, ground truth | Done |
| 2 | Semantic contracts, entitlements, chokepoint, lineage, audit | Done |
| 3 | Detection (STL, robust z, PELT, materiality, sparse path) | Not started |
| 4 | Attribution (LMDI, Adtributor, significance, DiD) | Not started |
| 5-13 | Retrieval, gates, narration, recommendation, graph, UI, eval | Not started |

Stages 1 → 4 are the critical path: they produce a working diagnostic engine
with no LLM at all.

## Architecture in one paragraph

Five KPIs connected by one identity —
`Net Revenue = Sessions × Conversion Rate × AOV × (1 − Refund Rate)` — spread
across three sources with genuinely different grains and refresh cadences. Every
metric read passes through **one** function, `semantic.gateway.guarded_query()`,
which resolves entitlements, compiles SQL from a versioned YAML contract,
executes it, builds a lineage record and writes an audit row. There is no second
path to the database, and `tests/test_chokepoint.py` asserts that mechanically
rather than trusting convention.

## Layout

```
config/      scoring weights, personas, model routing
data/        generator, spec, ground truth, scenario manifest
semantic/    KPI contracts (YAML), registry, compile_sql, gateway, freshness
security/    policy.yaml, entitlement decisions, append-only audit
tests/       chokepoint, entitlements, semantic, data integrity
docs/        the two sources of truth, plus the decision record
```

One package per architectural layer, deliberately flat. Later stages add
`detection/`, `attribution/`, `evidence/`, `llm/`, `trust/`, `recommend/`,
`graph/`, `telemetry/`, `feedback/`, `ui/`.

## The rules that matter

Full set in `CLAUDE.md`. The load-bearing ones:

1. The LLM is never the source of a number.
2. All data access goes through the semantic/entitlement chokepoint.
3. No direct LangChain dependency. LangGraph is orchestration only.
4. No multi-agent architecture, no vector database, no fine-tuning.
5. Architecture changes need evidence of a contradiction, then an ADR.

## Documents

| Path | Role |
|---|---|
| `docs/ROUND2_TECHNICAL_ARCHITECTURE.md` | Technical source of truth |
| `docs/ROUND2_CASE.md` | Requirements source of truth (`R2-*` IDs) |
| `docs/DECISIONS.md` | Architecture decision record |
| `docs/ROUND1_MASTER.md` | Round 1 research, background only |
| `data/SCENARIOS.md` | Generated: dataset stats and the seven demo scenarios |
