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

**It does not just say what moved. It investigates why, shows the evidence,
recommends what to do — and knows when it should not answer.**

## Run it

```bash
pip install -r requirements.txt
python -m data.generate           # builds data/warehouse.duckdb, ~30 s
python -m retrieval.build_index   # builds the embedding index, ~60 s
streamlit run app.py              # the decision workspace
```

Both generated artifacts are reproducible from seed `20260821` and are
deliberately not committed. **`build_index` is required** — the retrieval layer
raises rather than silently degrading if the index is missing.

To run the test suite instead of the app:

```bash
python -m pytest -p no:randomly --tb=short
```

Running **without** an `ANTHROPIC_API_KEY` is a supported mode, not a degraded
one: the graph routes to a verified deterministic template, and the UI labels it
as such. Every number, every piece of evidence and the final decision are
identical either way — only the sentence construction differs. CI runs in
exactly this mode.

## Status

Round 2 prototype **complete**. All stages built and audited.

| Stage | Scope | Status |
|---|---|---|
| 0 | Scaffold, deps, config, base models, test framework | Done |
| 1 | Synthetic dataset, injected events, ground truth | Done |
| 2 | Semantic contracts, entitlements, chokepoint, lineage, audit | Done |
| 3 | Detection (STL, robust z, PELT, materiality, sparse path) | Done |
| 4 | Attribution (LMDI, Adtributor, significance, DiD) | Done |
| 5–8 | Retrieval, evidence bundle, two gates, narration, recommendation | Done |
| 9–10 | Deferral, LangGraph orchestration | Done |
| 11 | Streamlit decision workspace | Done |
| 12–13 | Evaluation, release readiness, competition audits | Done |

**Measured:** 574 tests passing · 8/8 scenarios end to end · 8/8 agreement
between the orchestrated graph and the direct-module path · 32 security tests ·
0 restricted items reaching any stage · LMDI identity closing to 0.000000000%
residual.

**Verified on a clean machine:** CI runs install → generate warehouse → build
index → full suite → credential scan on `ubuntu-latest` / Python 3.13, with no
API key set. **574 passed, 0 failed** in 5m 02s.

Every figure in the submission carries an evidence class — measured, synthetic
evaluation, research-sourced, assumption, or illustrative. No ROI, cost saving,
adoption or production-accuracy claim appears anywhere in this repository;
`eval/claim_audit.md` records the search that confirms it.

## Architecture in one paragraph

Six KPI contracts connected by one identity —
`Net Revenue = Sessions × Conversion Rate × AOV × (1 − Refund Rate)` — spread
across three sources with genuinely different grains and refresh cadences. Every
metric read passes through **one** function, `semantic.gateway.guarded_query()`,
which resolves entitlements, compiles SQL from a versioned YAML contract,
executes it, builds a lineage record and writes an audit row. There is no second
path to the database, and `tests/test_chokepoint.py` asserts that mechanically
rather than trusting convention.

The LLM sits at the end of that chain, not the middle: it receives a frozen,
hashed evidence bundle, has no database access, and its request carries no
`tools` key at all. Ten deterministic checks run against the frozen bundle
before any narrative reaches a user, failing closed to a verified template.

## Layout

```
config/         scoring weights, personas, levers, deferral economics
data/           generator, spec, ground truth, scenario manifest
semantic/       KPI contracts (YAML), registry, compile_sql, gateway, freshness
security/       policy.yaml, entitlement decisions, append-only audit
detection/      STL decomposition, robust MAD z-score, PELT, materiality gate
attribution/    LMDI decomposition, Adtributor, bootstrap, difference-in-differences
retrieval/      BM25 + dense embeddings, reciprocal rank fusion, index builder
evidence/       frozen, hashed EvidenceBundle
llm/            client, typed claim schema
prompts/        narration prompt templates
verification/   Gate 1 sufficiency, Gate 2 ten deterministic checks
confidence/     calibration bands, Laplace smoothing
recommendation/ levers, owners, monitoring plans, automation scope
deferral/       cost-sensitive automate / review / abstain decision
graph/          LangGraph state machine, checkpoints, telemetry, lineage
feedback/       typed analyst outcomes
ui/             Streamlit decision workspace (presentation only)
tests/          18 test modules, 574 tests
eval/           27 evaluation and audit reports
submission/     business proposal, pitch deck, rendered PDF, deck source
docs/           sources of truth, architecture, decision record, deployment
```

One package per architectural layer, deliberately flat. Verified: **0 circular
imports**, and the UI imports only `.types` modules plus the graph entrypoint.

## The rules that matter

Full set in `CLAUDE.md`. The load-bearing ones:

1. The LLM is never the source of a number.
2. All data access goes through the semantic/entitlement chokepoint.
3. No direct LangChain dependency. LangGraph is orchestration only.
4. No multi-agent architecture, no vector database, no fine-tuning.
5. Architecture changes need evidence of a contradiction, then an ADR.

## Documents

### Submission deliverables

| Path | Role |
|---|---|
| `submission/R2_BUSINESS_PROPOSAL.md` | R2-DEL-1 — business proposal, 17 sections |
| `submission/R2_BUSINESS_PROPOSAL_SOURCE.md` | Every claim mapped to its evidence class and artefact |
| `submission/R2_BUSINESSINTELLIGENCE_PITCH.pdf` | R2-DEL-3 — the rendered 11-slide pitch deck (built and audited in this repo) |
| `submission/R2_PITCH_DECK.md` | Deck build spec, slide by slide |
| `submission/R2_PITCH_SPEAKER_NOTES.md` | Talk track, four timing plans, Q&A index |
| `submission/deck/` | Deck source: HTML slides, vendored design system, render pipeline |
| `submission/wireframe/` | Excalidraw wireframe for the 6-slide official Accenture-template deck submitted through the competition portal — a content/layout plan, not the rendered final |

The prototype itself is R2-DEL-2.

### Reference

| Path | Role |
|---|---|
| `docs/ROUND2_CASE.md` | Requirements source of truth (`R2-*` IDs) |
| `docs/ROUND2_TECHNICAL_ARCHITECTURE.md` | Technical source of truth |
| `docs/FINAL_SYSTEM_ARCHITECTURE.md` | As-built architecture |
| `docs/DECISIONS.md` | Architecture decision record, ADR-001 → ADR-032 |
| `docs/PRODUCTION_EVOLUTION.md` | Production path, each migration with a trigger |
| `docs/DEPLOYMENT.md` | Setup and run |
| `docs/ROUND1_MASTER.md` | Round 1 research, background only |
| `data/SCENARIOS.md` | Generated: dataset stats and the demo scenarios |

### Evaluation

| Path | Role |
|---|---|
| `eval/round2_traceability.md` | Every `R2-*` requirement → code → test → scenario |
| `eval/final_evaluation_report.md` | Consolidated measured results |
| `eval/claim_audit.md` | Every claim classified by what actually backs it |
| `eval/judge_defense.md` | 24 anticipated questions, weak answers flagged |
| `eval/final_demo_script.md` | Three-minute live demo, beat by beat |
| `eval/prototype_readiness.md` | 14-area readiness matrix |
| `eval/product_judge_audit.md` | Independent adversarial product/UX/judge audit — first pass, scored 74/100 |
| `eval/product_judge_audit_v2.md` | Second-pass audit of the current state, scored 79/100 against the same rubric |
| `eval/technical_competition_audit.md` | Independent technical teardown — concurrency, verification, retrieval, performance |
| `eval/final_transmission_audit.md` | Record of the pitch/product transmission-gap fixes made between the two judge audits |

## Known limitations

Stated here rather than discovered later. Full detail in
`eval/prototype_readiness.md` and `submission/R2_BUSINESS_PROPOSAL.md` §15.

- **No authentication.** Persona is a dropdown. Authorisation is real and tested end to end; identity is not. Enterprise IAM is required before any real data.
- **All evaluation is synthetic.** Ground truth is known by construction. These are not production accuracy figures.
- **No live LLM evaluation.** No API key was available; model latency, token usage and cost are unmeasured and deliberately not estimated.
- **No baseline measurement**, so no time-saving or ROI claim is made.
- **Limited concurrent usage.** The prototype is designed for small-scale demonstration workloads. Production deployment requires connection isolation and a server-grade persistence layer.
