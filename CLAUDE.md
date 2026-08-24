# BusinessIntelligence.ai

Accenture Innovation Challenge 2026, **Round 2 prototype**. Team SouthernHustlers, Problem Track 3.

A KPI intelligence-to-action engine: it detects material KPI movements, ranks explanatory drivers, writes persona-specific narratives backed by traceable evidence, abstains when the evidence does not support a claim, and recommends actions tied to real business levers.

## Sources of truth

| Document | Authority |
|---|---|
| `docs/ROUND2_TECHNICAL_ARCHITECTURE.md` | **Technical** source of truth. Implementation decisions come from here. |
| `docs/ROUND2_CASE.md` | **Requirements** source of truth. Acceptance criteria are the `R2-MPE-*` IDs. |
| `docs/DECISIONS.md` | Architectural decision record. Append, do not rewrite history. |
| `docs/ROUND1_MASTER.md` | Round 1 research and framing. Background and citations only, not binding on implementation. |

## Architectural rules

These are not preferences. Violating one is a defect.

1. **The LLM is not the quantitative source of truth.** Every number a user sees is computed by SQL, statistics or a business rule. The model writes prose into a constrained schema; it never produces, adjusts or infers a figure.
2. **No direct LangChain dependency or import.** `langchain-core` may arrive transitively under LangGraph — that is acceptable. `import langchain` is not.
3. **LangGraph is workflow orchestration only.** State machine, conditional routing, checkpointing, interrupts. It is not an agent framework here.
4. **No multi-agent architecture.** No agent may re-query data or negotiate an answer with another agent.
5. **No vector database.** Embeddings are held in memory / on disk as plain arrays. Scale does not justify infrastructure.
6. **Streamlit is presentation only.** No analysis, no business logic, no data access inside a UI callback.
7. **All data access passes through the semantic/entitlement chokepoint** (`semantic/gateway.py`). There is exactly one function that touches DuckDB. `tests/test_chokepoint.py` enforces this.
8. **All important modules have tests.** Detection, attribution, verification, entitlements and routing are not optional to test.
9. **Do not redesign the architecture without explicit evidence of a contradiction.** If the architecture document appears wrong, show the failing case first, then propose the change, then record it in `docs/DECISIONS.md`.

## Working practice

- Follow the build order in Architecture Part 23. Stages 1 → 4 produce a working diagnostic engine with no LLM at all; protect that sequence.
- Build the verifier before the narrator, and the deterministic template before the LLM narrative. Both orderings are deliberate (Part 23).
- Part 24 lists technologies deliberately **not** built. Adding one back requires a DECISIONS entry.
- Repository layout is specified in Part 22 and is deliberately flat: one package per architectural layer.
