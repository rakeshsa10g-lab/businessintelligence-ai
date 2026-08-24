# BusinessIntelligence.ai — Round 2 Technical Architecture
**Accenture Innovation Challenge 2026 · Problem Track 3 · Team SouthernHustlers**
Decision document for the Round 2 working prototype. Written 2026-08-21.

> **Scope note.** This document decides architecture, stack, data design, UX and build order. It does **not** re-open the product concept — the Round 1 concept (Detect → Attribute → Explain → Recommend → Verify, two-gate trust, evidence-ranked hypotheses, cost-sensitive deferral) is treated as settled and carried forward intact. Where I change something from Round 1, it is flagged **[CHANGE]** with the technical reason.

---

## 0. THE ANSWER, UP FRONT

You asked the hard question last. I am answering it first, because every other section follows from it.

**Does LangChain + LangGraph + embeddings + Streamlit genuinely strengthen BusinessIntelligence.ai, or is it technology decoration?**

**Three of the four are justified. One is decoration. Use LangGraph, embeddings and Streamlit. Do not use LangChain.**

| Technology | Verdict | One-line reason |
|---|---|---|
| **LangGraph** | **Essential for Round 2** | Your system is a state machine with conditional routing, two verification gates, a bounded retry cycle, an abstention branch and a human interrupt. That is exactly what LangGraph is for — and its checkpointer gives you the run trace, audit trail and lineage record for free, which are three separate Round 2 requirements. |
| **Embeddings** | **Essential — but only over ~1,500 unstructured documents, nothing else** | Support tickets and CRM notes describe the *same* failure in a dozen phrasings ("card declined", "payment failed", "gateway timeout"). Keyword-only retrieval misses that, and evidence recall is the difference between a supported hypothesis and an abstention. Embeddings go nowhere near KPI metadata, semantic definitions, changelog rows or numbers. |
| **Streamlit** | **Essential for Round 2, explicitly temporary** | The only way you get a multi-persona, multi-state analytical UI built and demo-stable in the time available. It is not the right long-term answer and you should say so on the roadmap slide. Build a decision workspace, not a chatbot. |
| **LangChain** | **Technology decoration — skip it** | Your LLM surface is three narrow, schema-constrained calls over frozen inputs. LangChain 1.0's value proposition is the `create_agent` middleware loop — an agent abstraction you specifically must *not* have, because a model that can re-query data is the exact thing this architecture exists to prevent. `langchain-core` arrives transitively under LangGraph; that is fine. Importing `langchain` itself buys nothing and costs auditability. |

**The sharpest thing you can say to a judge is the fourth row.** Every other team will have bolted all four on. Walking in and saying *"we deliberately removed LangChain, here is the architectural reason, and here is what we used instead"* signals engineering judgment more loudly than any diagram. Selection is the signal, not accumulation.

And the one-line architecture:

> Deterministic SQL and statistics compute every number; a published algorithm (Adtributor, NSDI '14) ranks which dimension moved; hybrid retrieval finds corroborating documents; the LLM writes into a validated claim schema it cannot exceed; a deterministic verifier checks every number, driver and direction before the words reach a human — and when they do not check out, the system abstains rather than writing prettier prose.

---

## PART 1 — WHAT IS ALREADY DECIDED, AND WHAT IS NOT

Sources read: `BusinessIntelligence_AI_AIC2026_MASTER.md`, all nine docs in `04_Research_Docs/`, the Round 1 deck content spec, and the Round 2 case PDF.

### 1.1 Already decided — carried forward unchanged

| Decision | Origin | Status |
|---|---|---|
| Five-stage funnel: Detect → Attribute → Explain → Recommend → Verify | CIRCLES "Cut through prioritization" | **Locked.** Spine of both the prototype and the UI. |
| Statistical detection owns "is this real"; the LLM never detects | Trade-offs table; CALM caveat (arXiv 2508.21273) | **Locked.** |
| STL-style seasonality removal *before* changepoint detection | Li et al. 2019; Elicit §13.1 | **Locked.** |
| Minimum business-effect / materiality gate on top of statistical significance | Elicit §13.1; the Round 2 case names it explicitly | **Locked.** Your best answer to signal-vs-noise, and the case asks for it by name. |
| Driver-tree decomposition before hypothesising why | CIRCLES "List Solutions" §2 | **Locked**, upgraded in Part 10. |
| Internal/External cause buckets **including a schema/definition-change bucket** | r/BusinessIntelligence §9.4 | **Locked.** Nobody else will have this bucket. |
| Unstructured evidence aggregated at cohort/account level, not per-ticket | IBM/UVic escalation study, D7 | **Locked** — becomes a retrieval constraint in Part 11. |
| Two-gate trust: pre-generation data-quality gate + post-generation fidelity gate (membership / direction / coverage) | arXiv 2608.08126 fidelity audit; D5 | **Locked**, hardened substantially in Part 13. |
| Ranked 2–3 hypotheses instead of one answer | Cresswell et al. 2024 (ICML); AgentRCA Top-1 40% → Top-2 61.5% | **Locked.** |
| Cost-sensitive deferral, not a confidence threshold | Mozannar & Sontag 2020 (ICML) | **Locked.** Implementation in Parts 12 and 14. |
| Calibrated confidence shown with reliability context, not a bare percentage | Fregosi et al. 2026 (AAAI); Zhang et al. 2020 (FAT*) | **Locked** — drives a specific UI component in Part 18. |
| Narrow initial scope: regional revenue anomalies for ops leads | Copilot "wrong job" analysis, D8 | **Locked.** Also happens to be the correct prototype scope. |
| Attribution scores are never proof of causation | Elicit §13.2 | **Locked**, and now *enforced in code* rather than asserted as a principle (Part 6, causal-language gate). |

### 1.2 Still ambiguous — decided in this document

1. **What the driver tree actually computes.** Round 1 states `Revenue = Volume × Price × Conversion` but never says how a change is split across those factors, nor how the dimensional drill-down picks a winner. → **Part 10** (LMDI decomposition + Adtributor).
2. **Which detection methods actually ship.** Round 1 names STL, PELT, CUSUM and Bayesian online detection. Four methods is three too many for a prototype. → **Part 9**.
3. **What the semantic layer *is*.** Named as a need (from the Tableau review quote §9.1), never specified. → **Part 8**.
4. **How confidence is produced.** "Confidence 0.82" appears in the Round 1 worked example with no derivation. This is the single biggest credibility risk in the deck — a judge will ask. → **Part 13.4**.
5. **What "the system learns" means.** Round 1 says "log resolved cases as training signal." That is precisely the vague version the Round 2 case penalises. → **Part 15**.
6. **Personas and entitlements.** Round 1 names three segments but no access model; Round 2 mandates one. → **Parts 7.6 and 21**.

### 1.3 Needs technical validation before you trust it

- **"Confidence 0.82."** Any number on screen must come from a documented function. If you cannot derive it live, do not show it. Part 13.4 gives you a derivation that fits on a slide.
- **Adtributor's single-dimension assumption.** The paper explicitly restricts itself to a Boolean expression over one dimension, having found multi-dimension root causes to be rare in practice. Usually true, not always. → Part 10.4 handles the exception honestly instead of hiding it.
- **Embedding quality is not MTEB rank.** In-domain benchmarks have found MTEB top-3 models placing 5th/7th/2nd on real data while an 11th-ranked model won ([Milvus, 2026](https://milvus.io/blog/choose-embedding-model-rag-2026.md)). → Part 11.6 forces a 20-pair in-domain retrieval eval before you trust any embedding choice.
- **LLM-as-judge is not a guarantee.** CALM (arXiv 2508.21273) improved detection AUC by up to +0.351 but *degraded* it on other datasets. → the verifier's primary checks are deterministic; the LLM judge is advisory only (Part 13.3).

### 1.4 Must be simplified for the prototype

| Round 1 ambition | Round 2 prototype form | Why |
|---|---|---|
| Four detection algorithms | Two (STL + robust z-score, PELT) plus a coverage gate | CUSUM needs a stream you do not have; BOCPD needs tuning that buys no demo value. |
| "Causal inference" | Difference-in-differences against a matched control slice | A real, checkable counterfactual in ~40 lines. Full causal discovery (PC, LiNGAM, DoWhy) is a research project, not a prototype. |
| Real-time alerting | Batch run plus on-demand "explain this" | Halves the surface area, loses nothing in the demo. |
| "The engine learns" | Five typed feedback outcomes updating five named artifacts, none of which is an LLM | Specific beats magical; the case asks for the mechanism. |
| Live news / external events feed | 40 hand-authored market-event records in the corpus | You need the *evidence type*, not a live news API. |

---

## PART 2 — THE CORE TECHNICAL QUESTION, ANSWERED PROPERLY

The intern's advice is not wrong so much as *undifferentiated* — it is the default stack for any LLM project in 2026. The question is which parts survive contact with your specific problem: a system whose central claim is that **the LLM is not the source of quantitative truth.**

That claim has a direct architectural consequence: **the LLM must not be able to fetch data.** Every framework feature designed to let a model decide what to retrieve next is, for you, a liability rather than a feature. That single test decides three of the four calls below.

### 2.1 LangChain — Unnecessary / technology decoration

**What LangChain 1.0 actually is now.** LangChain and LangGraph both reached v1.0 in October 2025. In v1, LangGraph was promoted from sibling library to *runtime*, and `langchain` became an opinionated, middleware-driven high-level API on top of it. `initialize_agent` and `AgentExecutor` moved to `langchain-classic`, `create_react_agent` was deprecated, and everything collapsed into `create_agent` with a middleware array (`before_model`, `wrap_tool_call`, `after_model`, …). ([What's new in LangChain v1](https://docs.langchain.com/oss/javascript/releases/langchain-v1) · [v1.0 announcement](https://blog.langchain.com/langchain-langgraph-1dot0/))

So LangChain's 2026 value proposition is *a well-instrumented agent loop*. Evaluate that against the four candidate uses you listed:

| Candidate use | Verdict | Reason |
|---|---|---|
| **Agent loop / tool calling** | Actively harmful | Your narrator must be a pure function of a frozen evidence bundle. It must not hold tools. An agent abstraction is the inverse of your central design claim. |
| **Model abstraction** | Not needed | One primary model, two routes. A 15-line `llm/client.py` adapter gives you swap-ability with total transparency; the framework abstraction hides the exact request you want to show a judge. |
| **Structured outputs** | Not needed | The Anthropic SDK does this natively (`output_config.format` / `messages.parse()`) validated against your Pydantic schema. Wrapping it puts a layer between you and the schema violation you specifically need to see. |
| **Prompts** | Not needed | Your prompts are versioned text files. `str.format()` is a feature, not a limitation. |
| **Ingestion / document loading / splitting** | Marginal | `langchain-text-splitters` is fine in isolation. But your documents are already short, atomic records (one ticket, one CRM note) — **you should not chunk them at all** (Part 11.3). The use case disappears once retrieval is designed correctly. |
| **Retrieval abstraction** | Not needed | You need hybrid retrieval with an entitlement pre-filter and *visible per-signal scores in the UI*. Twenty lines of NumPy + `rank_bm25` gives you that; a retriever object hides the scores you want to display. |

**Verdict: skip it.** `langchain-core` will install transitively under LangGraph — unavoidable and harmless. Do not `import langchain`.

**How to say it to a judge:** *"LangChain's 2026 value is the agent loop. Our architecture's central claim is that the model never chooses what data it sees. So we took LangGraph — the runtime underneath LangChain — and left the agent layer out, on purpose."*

### 2.2 LangGraph — Essential for Round 2

This is the one people will assume is decoration. It is not, and here is the test I applied: *would you otherwise hand-write this?*

Field guidance is consistent — reach for LangGraph when the workflow needs cycles, conditional branching, persistent state or human review checkpoints; if it is a linear sequence with no branches, retries or approval gates, a plain pipeline is enough ([LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) · [Mastra: LangGraph guide](https://mastra.ai/articles/langgraph)).

Your workflow has **all four**, and not by contrivance — the Round 2 case mandates them:

| Requirement (verbatim from the case) | Control-flow shape it forces |
|---|---|
| "Communicates uncertainty and **abstains** when evidence is insufficient or contradictory" | Conditional branch that exits without producing the main output |
| Two-gate verification with fallback to a deterministic template | A **cycle**: narrate → verify → (fail) → narrate-with-violations → verify → (fail) → template |
| "Mechanism to learn from analyst and business-user feedback" | A **human interrupt** that pauses and resumes a run |
| "Detects and **prioritises** material KPI movements" | Early-exit branch on `not material` |
| "One role-based security or entitlement scenario" | Early-exit branch on `access denied` |
| "Runtime telemetry covering latency, model calls, token usage and estimated cost" | Per-node instrumentation over a persisted run |
| "Evidence showing source freshness, analytical method, contribution, confidence and **lineage**" | A durable, inspectable record of every step |

The last two are where LangGraph stops being orchestration sugar and starts paying rent. **A checkpointed LangGraph run *is* your audit trail.** One `SqliteSaver` gives you three things the case asks for separately: the lineage record, the telemetry substrate, and a resumable human-in-the-loop escalation. Hand-rolling that is a day of work and a reliable source of demo-day bugs.

**The honest caveat, which you should state out loud:** LangGraph is justified *at this size* — roughly 14 nodes, one typed state object, one cycle with a hard retry cap, three terminal branches. If the graph grows past ~20 nodes or acquires a second cycle, that is a signal the design got worse, not that the framework got better.

**What LangGraph must NOT do here:** it must not become multi-agent. No supervisor, no agent handoffs, no `Send` fan-out to autonomous workers. Every node is either a deterministic Python function or exactly one constrained LLM call. The graph is a **workflow**, not an agent society.

### 2.3 Embeddings — Essential, but narrowly scoped

The question is not "should we use embeddings," it is "**over what?**" Round 2 requires reconciling business context across heterogeneous sources, which makes retrieval unavoidable. But most of what you would be tempted to embed should not be embedded.

| Data | Embed? | Reason / what to use instead |
|---|---|---|
| **Support tickets** (subject + body) | **Yes** | The core case. Eight customers describe one gateway failure eight ways. Lexical search on "payment" misses "card keeps getting rejected." This is where dense retrieval earns its place. |
| **CRM / sales-call notes** | **Yes** | Free prose, domain vocabulary, paraphrase-heavy ("evaluating a competitor" vs "mentioned they're in an RFP"). |
| **Market / competitor news items** | **Yes** | Same argument, plus you want topical rather than exact matching. |
| **Changelog / deploy events** | **No** | Structured events with timestamps. Retrieved by `WHERE deployed_at BETWEEN … AND service IN (…)`. A vector search over a deploy log is strictly worse than a SQL join and much harder to explain. |
| **Schema-change log** | **No** | Same. Exact join on table/column name and date. |
| **KPI metadata and business definitions** | **No** | This is your semantic contract — a small, closed, authoritative set. It is *loaded*, not *retrieved*. Embedding a source of truth and fuzzy-matching against it is how the wrong KPI definition gets into a narrative. Exact ID lookup, always. |
| **Documentation / runbooks / lever catalogue** | **No (Round 2)** | Closed catalogue of ~20 levers keyed by `driver_id`. Deterministic lookup. Embedding it lets the model reach a lever that does not apply — the exact failure Part 14 exists to prevent. |
| **The KPI values themselves** | **Absolutely not** | Numbers go through SQL. Embedding a metric value is the "LLM as quantitative source of truth" failure in its purest form. |

**Net: roughly 1,500 documents are embedded, out of ~60,000 rows in the system.** That ratio is itself a talking point — *"4% of our data is in the vector index, and we can tell you exactly why each of the other sources is not."*

### 2.4 Streamlit — Essential for Round 2, explicitly temporary

Right tool, wrong century, and that is fine. For a Python-native analytical prototype that must be demo-stable in weeks, Streamlit wins on the axes that matter now: no frontend build, native dataframe and chart rendering, and a session model simple enough not to surprise you on stage.

The 2026 features you will actually lean on: `st.fragment` (re-render one panel without re-running the analysis — critical, since your pipeline is expensive), `st.dialog` (escalation and feedback modals), `st.Page`/`st.navigation` (persona-scoped pages), and `@st.cache_data` / `@st.cache_resource` (pin the DuckDB connection and the embedding model). Note `st.experimental_dialog` and `st.experimental_fragment` have been removed — use the stable names ([Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)).

**Its real limitation shapes your UI design.** Streamlit re-runs the script top-to-bottom on every interaction. So the rule is: **the analysis pipeline must never run inside a widget callback.** One button triggers one graph run; the result is a serialisable `InsightBundle` in `st.session_state`; every later interaction renders *from* that bundle. This is not a workaround — it is the same separation the architecture already demands (compute once, narrate from frozen evidence), and it makes the UI honest: what you see is always exactly one run's output.

**Say the roadmap line out loud:** *"Streamlit is the Round 2 demo surface. Production is an embedded panel inside the BI tool the leader already has open — because a tool that needs a second login to explain the first tool's number does not get used."* That converts your one obvious weakness into evidence of product judgment, and it lands directly on the Copilot "wrong job" finding you already hold (D8).

---

## PART 3 — FINAL TECH STACK, RESEARCHED

### 3.1 LLM selection

**What this system actually asks of a model.** Not long-context reasoning over raw data — the opposite. Three narrow jobs, each with small inputs because the hard work already happened deterministically:

| Job | Input size | What matters | Frequency |
|---|---|---|---|
| **A. Intent resolution** — "why did West revenue drop?" → `{kpi_id, window, dimensions}` | ~600 tokens | Cheap, fast, strict schema adherence. Reasoning depth irrelevant. | 1 call / query |
| **B. Narrative synthesis** — ranked hypotheses + evidence bundle → persona-specific claims | ~4–6K tokens | Factuality under pressure, instruction adherence, refusing to embellish. **This is where a wrong output costs the most.** | 1 call / insight |
| **C. Verification second opinion** — narrative + evidence → unsupported-claim flags | ~5K tokens | Adversarial reading, precision over fluency | 1 call / insight (advisory only) |

Note what is absent: no long-context ingestion, no multi-turn agent loop, no code generation, no tool-calling marathon. **Total ~12K tokens per insight.** That reshapes the cost calculation entirely — at these volumes, the per-token price is not the lever. As the pricing surveys put it, per-token price explains a minority of real spend; retries, agent loops and retrieval multiply usage far more than provider choice does ([Spheron LLM API pricing 2026](https://www.spheron.network/blog/llm-api-pricing-comparison-gpt-claude-deepseek-2026/)). Your architecture already eliminates the loop and the retries, so you can afford the good model on the one call that matters.

**Current landscape, August 2026.** Frontier list prices cluster at ~$5 / $25–30 per million tokens (GPT-5.6 Sol, Claude Opus 5); premium reasoning above that (Claude Fable 5 at $10/$50); mid tier at ~$1.50–3 in / $7.50–15 out (GPT-5.6 Terra, Claude Sonnet 5, Gemini 3.6 Flash); high-volume tier at $0.20–1 in / $1.20–5 out (GPT-5.6 Luna, Claude Haiku 4.5). Cache hits cost roughly 10% of input price; the Batch API cuts ~50%. ([IntuitionLabs](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025) · [AI Magicx](https://www.aimagicx.com/blog/llm-api-pricing-comparison-2026))

#### Recommendation — a three-route model policy, not a single model

| Route | Model | Model ID | Price (in/out per 1M) | Why this one |
|---|---|---|---|---|
| **Primary — narration + verification (jobs B, C)** | **Claude Opus 5** | `claude-opus-5` | $5 / $25 | Best factuality-under-instruction on the one call where a fabricated driver reaches a human. Native structured outputs (`output_config.format`) and strict tool schemas; adaptive thinking with an `effort` dial so you can tune quality/cost per call site; prompt caching so the frozen system prompt + semantic contract costs ~10% on repeat runs; 1M context you will not need but which removes truncation as a failure class. |
| **Cheap route — intent resolution (job A)** | **Claude Haiku 4.5** | `claude-haiku-4-5` | $1 / $5 | Schema-constrained classification. Using Opus here would be waste you cannot defend. 200K context is ample. |
| **Fallback — availability / refusal** | **Claude Sonnet 5** | `claude-sonnet-5` | $3 / $15 ($2/$10 promo to 2026-08-31) | Same API surface, same structured-output support. Wire the server-side `fallbacks` parameter so a refusal or outage degrades instead of erroring on stage. |

**Why Claude rather than GPT-5.6 or Gemini 3.6 here, stated fairly:** the deciding factors are (1) native structured outputs validated against your Pydantic claim schema, which is the mechanism that stops free-form prose; (2) prompt caching economics on a system prompt that never changes across runs, which is what makes "cost per insight" a defensible number rather than a guess; (3) `effort` control, letting you run narration at high effort and intent resolution at low effort within one provider and one telemetry schema. GPT-5.6 Terra and Gemini 3.6 Flash are legitimate substitutes on quality and cheaper on paper; **the architecture is model-agnostic behind a 15-line adapter and you should say so** — the defensible claim to a judge is that model choice is a routing decision your telemetry can re-evaluate, not a religious one. Do not claim a model is "better"; claim your system measures which one is better for you (Part 20).

**Do not use:** Claude Fable 5 ($10/$50) — its capability advantage is on long-horizon agentic work you deliberately do not do. Paying premium reasoning rates to narrate a table you already computed is exactly the "technology decoration" trap, one layer down.

#### Cost per insight (defensible arithmetic for the telemetry panel)

Assuming ~2K cached system+contract tokens, ~4K fresh evidence tokens, ~900 output tokens for narration; ~600 in / ~120 out for intent; ~5K in / ~300 out for verification.

| Call | Model | Input | Output | Cost |
|---|---|---|---|---|
| Intent | Haiku 4.5 | 600 | 120 | ~$0.0012 |
| Narration | Opus 5 | 2K cached + 4K fresh | 900 | ~$0.0236 |
| Verification | Opus 5 | 2K cached + 3K fresh | 300 | ~$0.0161 |
| **Total** | | | | **≈ $0.041 per insight (≈ ₹3.5)** |

Put that number on a slide next to *"a two-day analyst investigation."* It is the strongest single economic line in your deck, and it is arithmetic, not a claim.

### 3.2 Embedding model

**Recommendation: `BAAI/bge-small-en-v1.5`** (384-dim, 33M params) via `sentence-transformers`, running locally.

| Criterion | Why it wins here |
|---|---|
| Corpus size | ~1,500 short documents. Embedding the whole corpus takes seconds on CPU. Larger models buy accuracy you cannot measure at this scale. |
| Reproducibility | Runs offline, no API key, no rate limit, no network dependency on demo day. **This matters more than one benchmark point.** |
| Determinism | Same input → same vector, forever. Judges can re-run your notebook. |
| Licence | MIT-compatible, no commercial ambiguity. |
| Latency | Query embedding in ~5ms; keeps the interactive path under budget. |

**Named alternatives and when to switch:** `BAAI/bge-m3` if you add multilingual or long documents (it is the MIT-licensed workhorse covering 100+ languages with dense, sparse and multi-vector retrieval in one model, and most production RAG stacks in 2026 default to BGE-M3 plus BGE-reranker-v2). `nomic-embed-text` if you need an 8,192-token context. Hosted options (Gemini Embedding 001, Voyage) are better on English leaderboards but add a network dependency to your demo for a gain you cannot measure on 1,500 docs. ([BentoML: open-source embedding models](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models) · [Milvus: choosing an embedding model, 2026](https://milvus.io/blog/choose-embedding-model-rag-2026.md))

**The caveat that becomes a differentiator:** MTEB rank does not predict in-domain performance — one legal-retrieval evaluation found the leaderboard's top-3 placing 5th, 7th and 2nd on real data while an 11th-ranked model won. So **do not defend your embedding choice with a leaderboard.** Defend it with the 20-pair in-domain retrieval eval in Part 11.6. "We measured it on our own data" beats "it is top of MTEB" in front of any technical judge.

### 3.3 Vector database — **none. This is a deliberate decision, not an omission.**

Run the numbers before reaching for infrastructure: 1,500 documents × 384 dimensions × 4 bytes = **2.3 MB**. That is a NumPy array. Exhaustive cosine similarity over it takes ~2 ms. Every ANN index, every service, every Docker container in this space exists to solve a problem you do not have.

| Option | Verdict for Round 2 |
|---|---|
| **NumPy matrix + `rank_bm25`, persisted alongside DuckDB** | **Chosen.** Zero services. Fully reproducible. And decisively: **it lets you display the dense score, the BM25 score and the fused rank for every retrieved document in the evidence panel** — which is a Round 2 requirement ("evidence showing … analytical method"). A vector DB hides exactly the numbers you want on screen. |
| **Chroma** | Reasonable fallback if you want a named component. Community consensus in 2026 is Chroma for new prototypes, migrating to Qdrant/pgvector as filtering and scale grow. Costs you the visible scoring. Use only if the team is faster with it. |
| **pgvector** | The right *production* answer, especially since it is where your entitlement filters would live as SQL predicates. Wrong prototype answer: a Postgres dependency for 2.3 MB of vectors. Put it on the V2 slide. |
| **FAISS** | It is a similarity-search library, not a database — designed for in-process search in batch jobs and experiments. At 1,500 vectors it is strictly more machinery than NumPy for identical results. |
| **Pinecone / Weaviate** | Managed infrastructure, network dependency, cost, and a live service between you and your demo. No. |

([Redis: open-source vector DB comparison 2026](https://redis.io/blog/best-open-source-vector-databases-comparison/) · [Chroma vs pgvector 2026](https://pecollective.com/tools/chroma-vs-pgvector/) · [MarkTechPost: vector DBs 2026](https://www.marktechpost.com/2026/05/10/best-vector-databases-in-2026-pricing-scale-limits-and-architecture-tradeoffs-across-nine-leading-systems/))

**Judge-facing line:** *"We sized the corpus first. 2.3 megabytes of vectors does not need a database — and skipping it let us put the retrieval scores on screen, which a vector store would have hidden."*

### 3.4 Database / storage layer — **DuckDB, single file**

One embedded analytical database holds: the KPI fact tables, the dimension tables, the document metadata, the entitlement policy tables, the audit log, the feedback log and the telemetry log. A DuckDB database is a single portable file that ships with the app, giving a completely self-contained tool with no external connections ([MotherDuck: DuckDB + Streamlit](https://motherduck.com/ecosystem/streamlit/)).

Why it is the right call and not just the easy one:
- **Real SQL.** Window functions, CTEs, `QUALIFY`. Your semantic layer compiles to genuine analytical SQL — which is the point, since the case asks you to show when you use SQL and why.
- **Row- and column-level security is expressible.** Entitlements become SQL predicates and column projections at a single chokepoint (Part 21).
- **Grain reconciliation is a join, visibly.** Daily warehouse × hourly product analytics × weekly finance is a SQL problem, and doing it in SQL makes the reconciliation auditable.
- **Reproducible.** `git clone && streamlit run` with no infrastructure. Judges can run it.

`langgraph.checkpoint.sqlite.SqliteSaver` writes to a separate SQLite file — keep graph state and analytical data separate so a corrupted run never touches your data.

### 3.5 Statistical / ML libraries

| Need | Library | Note |
|---|---|---|
| Seasonal-trend decomposition | `statsmodels` (`STL`, `MSTL`) | Weekly seasonality on daily revenue. `MSTL` if you also want an annual component. |
| Changepoint detection | `ruptures` (PELT with an L2 cost, BIC-style penalty) | The reference Python implementation; PELT uses pruning to find the optimal segmentation at near-linear cost ([ruptures](https://github.com/deepcharles/ruptures) · [arXiv 1801.00826](https://arxiv.org/pdf/1801.00826)). |
| Significance tests, baseline forecasts | `scipy.stats`, `numpy` | Two-proportion z-test, Welch's t-test, seasonal-naïve baseline. |
| Attribution | **your own `attribution/adtributor.py`** | ~120 lines. Deliberately not a dependency — see Part 10. |
| Retrieval | `sentence-transformers`, `rank_bm25`, `numpy` | |
| Schemas | `pydantic` v2 | The contract that makes the LLM's output checkable. |
| Orchestration | `langgraph`, `langgraph-checkpoint-sqlite` | |
| LLM | `anthropic` | Official SDK. Do not use raw `requests`. |
| UI | `streamlit`, `plotly` | Plotly for the waterfall and driver tree; Streamlit natives elsewhere. |

**Deliberately absent:** scikit-learn (nothing here is a supervised model), Prophet (a forecasting library for a problem that needs a baseline, not a forecast), DoWhy/EconML (see Part 24), pandas is present but keep transformations in SQL where the lineage is visible.

### 3.6 What LangChain does — nothing

Already argued in 2.1. Concretely, in the repo: `langchain` appears in no import statement. `langchain-core` appears in `requirements.txt` only as a transitive dependency of `langgraph`, and you should annotate it as such so nobody thinks it was a decision you forgot to make.

### 3.7 What LangGraph does — the complete list

| Responsibility | Why LangGraph specifically |
|---|---|
| Node sequencing and conditional routing | Five branch points (entitlement, quality gate, materiality, sufficiency, verification) declared as edges, not buried in `if` statements |
| The narrate → verify → re-narrate cycle | A bounded cycle with a hard cap — the canonical case for a graph over a pipeline |
| Human-in-the-loop escalation | `interrupt()` pauses a run and returns a resumable checkpoint; the analyst's decision resumes it |
| Durable state | One typed `InsightState`; every node's mutation recorded |
| Audit trail / lineage | The checkpoint history *is* the lineage record — you render it, you do not rebuild it |
| Telemetry substrate | Per-node timing and token accounting wrapped once, uniformly |

**What LangGraph does not do:** it does not decide anything analytical. Every routing predicate is a pure function of deterministic state (`state.materiality.passed`, `state.verification.violations == []`). No LLM ever chooses an edge. That sentence belongs on your architecture slide.

### 3.8 What Streamlit does

It renders a **decision workspace**, not a chat interface. Full design in Part 18. The architectural rule that keeps it honest: Streamlit owns presentation and one button; it owns no analysis. Every panel renders from a single frozen `InsightBundle`.

---

## PART 4 — RESEARCH GROUNDING: PAPER → FINDING → RELEVANCE → CONSEQUENCE

Only papers that changed a decision in this document are listed. **Provenance is marked honestly**, because a judge may ask where a citation came from:
**[V]** = I fetched and read the primary source during this session. **[R]** = carried over from your existing research docs (§4/§8/§11/§13 of `Research_Findings.md`), not re-verified here.

### 4.1 Signal detection

**`[V]` Truong, Oudre & Vayatis — *ruptures: change point detection in Python* ([arXiv:1801.00826](https://arxiv.org/pdf/1801.00826))**
→ **Finding:** PELT performs exact penalised multiple-changepoint detection with a pruning rule that discards most candidate indices, retaining optimality at near-linear cost; the penalty term is the explicit overfit-vs-miss control.
→ **Relevance:** the penalty is *the* signal/noise knob you were looking for — it is a tunable, defensible parameter rather than a magic threshold.
→ **Consequence:** PELT on the STL residual is the level-shift test. The penalty is a field in the KPI semantic contract (`detection.pelt_penalty`), so different KPIs get different noise tolerances *by contract* — and you can show the contract on screen.

**`[R]` Aminikhanghahi & Cook (2016), *A Survey of Methods for Time Series Change Point Detection*, KAIS; Li et al. (2019) on Bayesian MDL structural breaks**
→ **Finding:** methods differ along change/cost model × search algorithm × penalty; and trend/seasonality should be modelled and removed *before* detecting breaks in the residual.
→ **Consequence:** the STL → residual → PELT ordering is a sourced design decision, not a convenience. It is also why a naive "8% is a big drop" rule fails: 8% may be Tuesday.

**`[R]` Lukassen et al. (2026), *LLM-Augmented Changepoint Detection* ([arXiv:2601.02957](https://arxiv.org/abs/2601.02957))**
→ **Finding:** pairs an ensemble of classical changepoint algorithms with an LLM layer that explains each detected changepoint, optionally RAG-grounded over your own documents.
→ **Consequence:** direct external validation of your two-stage split — statistics decide *whether*, the LLM narrates *why*. Cite it as prior art for the architecture shape, not as a method you implement.

**`[R]` CALM (2025) ([arXiv:2508.21273](https://arxiv.org/html/2508.21273v1))**
→ **Finding:** an LLM judge classifying anomalies as sustained vs transient improved AUC by up to +0.351 on the best dataset — but degraded results on others, and is less reliable than a formal statistical guarantee.
→ **Consequence:** **this is why the LLM judge in Gate 2 is advisory only** (Part 13.3). Use this as your trade-offs-slide honesty moment: you know the failure mode of the technique you did not adopt.

### 4.2 Attribution — the strongest and most under-used research line available to you

**`[V]` Bhagwan, Kumar, Ramjee, Varghese, Mohapatra, Manoharan & Shah — *Adtributor: Revenue Debugging in Advertising Systems*, USENIX NSDI '14, Microsoft ([paper](https://www.usenix.org/conference/nsdi14/technical-sessions/presentation/bhagwan))**

This is the most valuable citation in your entire deck and it is not currently in it. I read the paper this session; here is what it actually says.

→ **Finding.** Given forecast `F` and actual `A` for a measure, broken down by dimensions (advertiser, data centre, device type…), find the dimension and set of elements that best explains the deviation. Three ingredients:
  1. **Explanatory power** `EP_ij = (A_ij − F_ij) / (A − F)` — the fraction of the total change contributed by element *j* of dimension *i*. EPs within a dimension sum to 100%.
  2. **Succinctness** — Occam's razor: prefer the smallest element set that clears a threshold `T_EP` of the change, with a per-element floor `T_EEP`.
  3. **Surprise** — how much the element's *share* shifted, measured as Jensen-Shannon divergence between prior `p_ij = F_ij/F` and posterior `q_ij = A_ij/A`. JS is used rather than KL because it is symmetric and finite when a share goes to zero (e.g. a campaign is paused).
  The algorithm sorts elements by surprise, greedily accumulates those above `T_EEP` until `T_EP` of the change is explained, then picks the dimension with the highest total surprise.
→ **Why surprise matters — the paper's own worked example, which is worth putting on a slide.** Revenue falls $100 → $50. Data centre X alone explains **94%** of the drop, so a pure explanatory-power method blames X. But X also *produced* 94% of forecast revenue — it is big, not broken. Meanwhile device type PC went from 50% of forecast revenue to 98% of actual, and Mobile/Tablet from 25% to 0%. The true cause was a config error killing mobile ads. **Surprise finds it; explanatory power alone does not.**
→ **Reported results:** overall accuracy 95% (122/128 real incidents) versus **20%** for the succinctness-only strawman, and troubleshooting time cut by an order of magnitude.
→ **Relevance:** this is *literally your case*. Not an analogy — a Microsoft production system for "revenue moved, which dimension is to blame," published, evaluated, and deterministic.
→ **Architectural consequence:** `attribution/adtributor.py` is a ~120-line deterministic function. It is the core of your Attribute stage. **No LLM is involved in ranking drivers.** And you get a killer demo beat: run your data with surprise disabled, watch it blame the biggest region; re-enable it, watch it find the actual broken segment. That is a 30-second live demonstration that your system is doing real analysis.

**`[V]` Sun et al. — *HotSpot: Anomaly Localization for Additive KPIs with Multi-Dimensional Attributes*, IEEE Access 2018 ([PDF](https://netman.aiops.org/wp-content/uploads/2018/12/sunyq_IEEEAccess2018_HotSpot.pdf))**
→ **Finding:** extends Adtributor to root causes spanning *combinations* of dimensions, via a ripple-effect propagation model and Monte-Carlo tree search over attribute combinations; reports F-score >90% on 95% of case types.
→ **Consequence:** name it as your V2 upgrade path and as the honest answer when a judge asks "what if the cause is region *and* channel together?" Do not implement it in Round 2 — MCTS over the attribute lattice is days of work for a case your demo dataset does not need.

**`[V]` Li et al. — *Squeeze: Generic and Robust Localization of Multi-Dimensional Root Causes*, ISSRE 2019 ([PDF](https://netman.aiops.org/~peidan/ANM2022/8.AnomalyLocalization/LectureCoverage/2019ISSRE_Squeeze.pdf))**
→ **Finding:** clusters "deviation scores" bottom-up then searches within clusters; best F1 in most cases, beating prior approaches by ~0.4 on average at ~10 s per run.
→ **Consequence:** the credible third point on your "this is a real research field" slide, and the reference implementation to benchmark against if you ever build ground-truth attribution evaluation properly.

**`[V]` CMMD: *Cross-Metric Multi-Dimensional Root Cause Analysis* ([arXiv:2203.16280](https://arxiv.org/pdf/2203.16280))**
→ **Finding:** localising root causes for *derived* metrics (ratios like conversion rate) is improved by using the fundamental metrics they are computed from.
→ **Consequence:** directly shapes Part 10.2 — when Conversion Rate moves, attribute on Sessions and Orders (the fundamental measures), not on the ratio. This is a real trap: ratios are non-additive, so explanatory power over a ratio is not well-defined. Adtributor's own §4 makes the same point about derived measures.

**`[R]` Tellius (production system): variance decomposition + Shapley-ranked drivers + dimensional traversal with significance testing at each node**
→ **Consequence:** confirms the shape is commercially validated. But note the verified G2 review from that same product — *"automated insights … occasionally surface correlations that aren't actually meaningful without manual review"* — which is your wedge: they rank, you rank **and then require corroborating evidence plus a counterfactual check before the language is allowed to become causal.**

**`[R]` Multimodal causal RCA survey (2026); Elicit §13.2**
→ **Finding:** *"prediction is not intervention"* — and *"SHAP, attention, saliency and feature importance can prioritize signals, but they do not by themselves establish that changing a feature would change the outcome."*
→ **Consequence:** the causal-language gate in Part 6.4 exists because of this line. It is the difference between a system that says "conversion fell in the West" (always allowed) and one that says "the gateway change caused the fall" (allowed only when a counterfactual check passed).

**`[R]` AgentRCA (2026) ([arXiv:2607.22385](https://arxiv.org/html/2607.22385v1))**
→ **Finding:** zero-shot agentic RCA maintaining a ranked hypothesis table: 87.6% Top-1 on a 17-variable facility; 40.0% Top-1 but **61.5% Top-2** on a harder 52-variable process.
→ **Consequence:** the quantitative justification for showing 2–3 hypotheses rather than one. The Top-1→Top-2 jump is the number to cite when someone asks why you do not just show the best answer.

### 4.3 Retrieval

**`[V]` Hybrid retrieval with Reciprocal Rank Fusion — 2026 practice**
→ **Finding:** BM25 excels at exact matches (product codes, rare terms) but fails on paraphrase; dense retrieval handles paraphrase but underweights rare exact terms. RRF fuses ranked lists *by rank, not score*, sidestepping the score-incompatibility that makes naive weighted averaging fail. Basic RRF reached NDCG 0.7068 on WANDS versus 0.6983 (BM25) and 0.6953 (KNN); reported best `k` around 10–60 depending on corpus. ([Hybrid search reference 2026](https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026) · [AppScale: hybrid search & reranking](https://appscale.blog/en/blog/hybrid-search-and-reranking-production-rag-bm25-dense-cross-encoder-2026))
→ **Relevance:** your corpus contains both kinds of query. "gateway timeout" is paraphrase-heavy; `SKU-4471` and `ORD-88213` are exact-match.
→ **Consequence:** hybrid BM25 + dense with RRF (`k=10`) is the Round 2 retriever. **Cross-encoder reranking is V2** — it targets top-100 of a 200-candidate fused list, which is meaningless when your entitlement-filtered candidate pool is ~40 documents.

### 4.4 Trust, uncertainty and abstention

**`[R]` AbstentionBench — Kirichenko, Ibrahim, Chaudhuri, Bell (2025) ([arXiv:2506.09038](https://arxiv.org/pdf/2506.09038))**
→ **Finding:** reasoning-tuned models abstain **24% worse on average** than their non-reasoning counterparts.
→ **Consequence:** the single most important paper for your design posture. The capability you want for causal reasoning actively degrades the model's willingness to say "I don't know." Therefore **abstention must be a deterministic graph edge, never a model decision.** In your graph, the model is never asked whether it is confident; the evidence-sufficiency gate decides, in Python, before the model is called at all.

**`[R]` arXiv 2608.08126 — narrative fidelity audit of LLM-generated credit-risk explanations**
→ **Finding:** the model inverted the risk direction on 3 of 4 factors even under constrained prompting and greedy decoding, asserting drivers the attribution had scored the opposite way, omitting the true dominant driver, and naming a feature never supplied. Prescribed mitigation: check **membership**, **direction** and **coverage** post-generation and fall back to a deterministic template on failure.
→ **Consequence:** Gate 2 exists because of this paper, and Part 6.3's numeric allowlist extends it. The mechanism it names — model priors overriding supplied evidence — is the reason the verifier is deterministic rather than a second prompt.

**`[R]` Mozannar & Sontag (2020), ICML — learning to defer**
→ **Finding:** selective prediction asks *is the model confident enough?*; learning to defer asks the better question — *who is more likely to be right on this case, and is review worth its cost?*
→ **Consequence:** the deferral rule in Part 14.4, and the reason your escalation logic reads `expected_loss(model) < expected_loss(human) + review_cost` rather than `confidence < 0.7`.

**`[R]` Cresswell et al. (2024), ICML — conformal prediction sets**
→ **Finding:** showing a small set of plausible answers with a coverage guarantee measurably improved human decision accuracy in a preregistered randomised study.
→ **Consequence:** validates the 2–3 ranked hypotheses UI as a *measured* improvement, not a hedge.

**`[R]` Fregosi et al. (2026), AAAI; Zhang et al. (2020), FAT\***
→ **Finding:** well-calibrated confidence improved decision accuracy ~20%; miscalibrated confidence gave ~2% and increased automation bias. But a bare confidence score can improve trust calibration without improving joint accuracy.
→ **Consequence:** you never render a naked "0.82." You render a **reliability band with its historical base rate** — "High confidence · in 34 similar past cases this call was correct 29 times" — which is Part 18's `ConfidenceChip` component. The design principle to quote: *optimize for helping users know when to trust it, not for making them trust it.*

### 4.5 Evaluation

**`[V]` RAGAS metric family — faithfulness, answer relevancy, context precision, context recall ([RAG evaluation 2026](https://benchmarkingagents.com/rag-eval/) · [datavlab](https://datavlab.ai/post/rag-evaluation-methods-metrics-2026-guide))**
→ **Finding:** faithfulness = proportion of claims in the answer verifiable against retrieved context; context precision = proportion of retrieved chunks that are relevant; context recall = proportion of needed information present.
→ **Consequence:** you get faithfulness **for free and deterministically** — your verifier already computes claim-level evidence coverage, so "faithfulness" is `verified_claims / total_claims`, not an LLM-judged score. That is a better number than RAGAS gives you, and you should say so. Context precision/recall come from the 20-pair labelled retrieval set (Part 20).

---

## PART 5 — SYSTEM ARCHITECTURE, LAYER BY LAYER

### 5.0 Two changes to the pipeline you proposed

**[CHANGE 1] Entitlement enforcement moves to position 2, before any data is read.** You had security as an ambient concern. It must be the second thing that happens, because entitlements change *which rows exist* for this user — and therefore change detection, attribution and the evidence set. Applying security at render time is the classic mistake: the model has already seen restricted data and can leak it in prose even if the table is masked. **Filter at the source, once, at a single chokepoint.**

**[CHANGE 2] A counterfactual check sits between attribution and hypothesis ranking.** Without it, "correlation → action" is a slogan. With it, you have a checkable test that decides whether the narrative is *allowed* to use causal language. This is the cheapest large credibility gain available to you.

### 5.1 The architecture

```
                         ┌──────────────────────────────────────────┐
                         │  L0  DATA SOURCES (simulated, seeded)    │
                         │  warehouse · product analytics · finance │
                         │  tickets · CRM notes · changelog · news  │
                         └────────────────────┬─────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L1  SEMANTIC + ENTITLEMENT LAYER          DETERMINISTIC                 │
   │  KPI contracts (YAML→Pydantic) · SQL compiler · guarded_query() chokepoint│
   │  row filters · column masks · source allowlist · freshness registry       │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L2  DETECTION ENGINE                      STATISTICAL                    │
   │  coverage gate → STL → robust z → PELT → materiality gate                 │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L3  ATTRIBUTION ENGINE                    DETERMINISTIC + STATISTICAL    │
   │  LMDI identity decomposition → Adtributor (EP + JS surprise)              │
   │  → significance test per node → difference-in-differences control check   │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L4  EVIDENCE LAYER            DETERMINISTIC JOIN + RETRIEVAL (embeddings)│
   │  structured: changelog/schema-diff join on slice × window                 │
   │  unstructured: BM25 + dense → RRF, entitlement-prefiltered, cohort-rolled │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L5  HYPOTHESIS RANKER                     DETERMINISTIC SCORING          │
   │  contribution × significance × corroboration × precedence × counterfactual│
   │  → EvidenceBundle (frozen, immutable, the LLM's ONLY input)               │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌───────────────────── GATE 1 (pre-generation, deterministic) ─────────────┐
   │  freshness · completeness · schema stability · evidence sufficiency       │
   │  FAIL → abstain / request clarification. The LLM is never called.         │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L6  NARRATIVE SYNTHESIS                   LLM (Opus 5, structured out)   │
   │  persona-conditioned claims, each with evidence_ids + metric_refs         │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌───────────────────── GATE 2 (post-generation, deterministic) ────────────┐
   │  numeric allowlist · driver membership · direction · coverage             │
   │  · citation validity · causal-language licence                            │
   │  FAIL → 1 retry with violations → FAIL again → deterministic template     │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L7  RECOMMENDATION           BUSINESS RULES + LLM PHRASING ONLY          │
   │  driver → eligible levers (catalogue) → computed impact → owner → monitor │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L8  CONFIDENCE + DEFERRAL                 DETERMINISTIC + CALIBRATION    │
   │  bucketed reliability from history → cost-sensitive defer rule            │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L9  DELIVERY / ESCALATION / FEEDBACK      HUMAN                          │
   │  Streamlit decision workspace · analyst packet · 5 typed feedback outcomes │
   └──────────────────────────────────────────┬───────────────────────────────┘
                                              ↓
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L10 TELEMETRY + AUDIT + EVAL              DETERMINISTIC                  │
   │  per-node latency · tokens · cost · gate outcomes · lineage · eval suite  │
   └──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Layer specification

| # | Layer | Technology | Input | Output | Core logic | Failure mode | Depends on | AI? |
|---|---|---|---|---|---|---|---|---|
| L0 | Sources | DuckDB tables + JSONL docs, seeded by `data/generate.py` | seed + scenario config | 5 KPI facts, 3 doc corpora, event logs | Deterministic generator with **injected ground-truth events** | Unrealistic data undermines the whole demo → mitigate with seeded reproducibility and a visible `scenario_manifest.json` | — | No |
| L1 | Semantic + entitlement | Pydantic + YAML + DuckDB SQL | `kpi_id`, `persona`, `window` | `MetricSeries` + `LineageRecord` + `AccessDecision` | Contract → compiled SQL; row filter, column mask, source allowlist applied here **only** | A second code path querying DuckDB directly bypasses security → mitigate with a lint test asserting `duckdb.execute` appears in exactly one module | L0 | No |
| L2 | Detection | statsmodels, ruptures, scipy | `MetricSeries` | `DetectionResult{is_anomaly, changepoint_date, effect_size, p_value, method, coverage}` | coverage gate → STL → robust z on residual → PELT → materiality | Too few observations for STL → **coverage gate routes to sparse-history path** rather than erroring | L1 | No (statistics) |
| L3 | Attribution | own `adtributor.py`, numpy, scipy | `DetectionResult` + dimensional facts | `AttributionResult{identity_split, ranked_dimensions[], significance, did_estimate}` | LMDI → Adtributor EP+surprise → per-node significance → DiD control check | Sparse cells give unstable EP → floor on cell volume; cells below it are pooled into `Other` and flagged | L1, L2 | No (deterministic + statistics) |
| L4 | Evidence | sentence-transformers, rank_bm25, numpy, DuckDB | winning slice + window + entitlements | `Evidence[]` with per-signal scores | structured join (exact) + hybrid retrieval (RRF) + cohort roll-up | Retrieval returns plausible-but-irrelevant docs → time-window hard filter + slice filter + relevance floor | L1, L3 | **Yes — embeddings only** |
| L5 | Hypothesis ranker | pure Python | attribution + evidence | `Hypothesis[]` (2–3) + `EvidenceBundle` | Weighted deterministic score; bundle is frozen and hashed | Weights become arbitrary → they are versioned config, tuned only from labelled feedback (Part 15) | L3, L4 | No |
| G1 | Pre-gate | pure Python | bundle + freshness registry | `GateVerdict` | freshness SLA, null rate, schema stability, evidence sufficiency | Over-strict gate abstains constantly → thresholds in the KPI contract, per-KPI | L1–L5 | No |
| L6 | Narration | Anthropic SDK, Opus 5, structured outputs | frozen bundle + persona profile | `Narrative{claims[]}` | One call. No tools. No data access. | Fabrication → caught by Gate 2, never by trust | G1 | **Yes — LLM** |
| G2 | Post-gate | pure Python (+ optional advisory LLM) | narrative + bundle | `VerificationReport{violations[]}` | numeric allowlist, membership, direction, coverage, citations, causal licence | Verifier too strict → violations are typed and counted; only `hard` types block | L6 | Mostly no |
| L7 | Recommendation | YAML lever catalogue + LLM phrasing | top hypothesis + persona | `Recommendation[]` | Deterministic lever lookup; computed impact; LLM phrases only | LLM invents a lever → `lever_id` must exist in catalogue or the recommendation is dropped | L5, G2 | Partly |
| L8 | Confidence + deferral | pure Python + calibration table | full state | `Confidence` + `DeferralDecision` | bucketed historical reliability; cost-sensitive defer rule | No history at demo time → ship a seeded calibration table from the synthetic eval run, and label it as such | L2–L7 | No |
| L9 | Delivery | Streamlit | `InsightBundle` | rendered workspace | Renders only; never computes | Analysis in a callback → architectural rule: one button, one run | all | No |
| L10 | Telemetry | DuckDB tables + LangGraph checkpoints | every node | run records, eval reports | Wrapped once around node execution | Telemetry that nobody reads → it is a first-class UI tab, not a log file | all | No |

### 5.3 The two artifacts everything hinges on

**`EvidenceBundle` (frozen after L5).** Everything the LLM will ever see. Immutable, hashed, stored with the run. Contains: metric facts with values and provenance, ranked hypotheses, evidence items with IDs and excerpts, the persona profile, and the allowed lever list. **If a fact is not in the bundle, it does not exist as far as the narrative is concerned.** This single object is what makes Gate 2 mechanically checkable instead of aspirational.

**`InsightBundle` (output of the graph).** Everything the UI will ever render: the evidence bundle, the narrative claims, the verification report, confidence, recommendations, the deferral decision, lineage, telemetry. Serialisable. One run in, one screen out.

---

## PART 6 — HARD RULES: WHAT THE LLM MAY NOT DO

This is the section judges will remember, because it is the part most teams state as a principle and none enforce as a mechanism. **Every rule below is a line of code, not a sentence in a prompt.**

### 6.1 Division of responsibility

| Deterministic / SQL / business rules own | Statistics & ML own | Retrieval owns | The LLM owns | Humans own |
|---|---|---|---|---|
| KPI formulas and every computed value | Seasonality decomposition | Locating candidate evidence | Interpreting *already-computed* findings | Accepting / rejecting / correcting |
| Variance and contribution arithmetic | Anomaly significance (`p`, effect size) | Ranking documents by relevance | Persona-appropriate wording and depth | Resolving ambiguity when deferred |
| Materiality thresholds | Changepoint location | Surfacing changelog / schema events | Explaining what uncertainty *means* here | Approving lever changes |
| Percentages, deltas, currency, dates | Contribution significance tests | Cohort roll-up of tickets | Selecting among **eligible** levers | Owning the action |
| Freshness, lineage, row counts | Difference-in-differences estimate | — | Composing the summary sentence | Final decision, always |
| Entitlements and masking | Confidence calibration | — | — | — |
| Lever eligibility and decision rights | — | — | — | — |

### 6.2 The five hard prohibitions

The LLM must not invent, and is mechanically prevented from emitting: **(1)** any numeric value, **(2)** any KPI calculation, **(3)** any causal claim without a passed counterfactual check, **(4)** any driver ranking, **(5)** any evidence content, confidence value or business rule.

### 6.3 The enforcement mechanisms — in order of strength

**Rule 1 — The narrator has no tools and no data access.** This is the strongest guarantee, and it is architectural rather than behavioural. The narration call passes a frozen JSON bundle and receives structured output. No tool definitions. No database handle. No retrieval. A model that cannot query cannot fabricate a query result. *This is precisely why LangChain's agent layer is excluded.*

**Rule 2 — The LLM writes into slots, not paragraphs.** The output schema is claims, not prose:

```python
class Claim(BaseModel):
    text: str
    claim_type: Literal["observation", "attribution", "causal", "recommendation", "uncertainty"]
    evidence_ids: list[str]      # must exist in bundle.evidence
    metric_refs: list[str]       # must exist in bundle.metric_facts
    direction: Literal["up", "down", "flat", "n/a"]

class Narrative(BaseModel):
    headline: str
    claims: list[Claim]          # 3–7
    caveats: list[str]
```

Prose is assembled from validated claims. The reverse — generating prose and then trying to check it — is the failure mode arXiv 2608.08126 documents.

**Rule 3 — Numeric allowlist.** Extract every number from every claim with a regex; each must match a value in `bundle.metric_facts` within rounding tolerance. Unmatched number → `HARD` violation.

```python
ALLOWED = {round(f.value, 2) for f in bundle.metric_facts} | {round(f.delta_pct, 1) for f in bundle.metric_facts}

def check_numbers(claim: Claim) -> list[Violation]:
    found = [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", claim.text.replace(",", ""))]
    return [Violation("UNGROUNDED_NUMBER", claim, str(n)) for n in found
            if not any(abs(n - a) <= max(0.05, abs(a) * 0.005) for a in ALLOWED)]
```

**Rule 4 — Driver membership + direction + coverage** (the three checks arXiv 2608.08126 prescribes). Every driver named must be an ID in `bundle.hypotheses`; the asserted direction must match the computed sign; the largest-contribution driver must appear in at least one claim.

**Rule 5 — Causal-language licence.** A claim typed `causal`, or containing a causal verb, is permitted only if its referenced hypothesis has `counterfactual.passed == True` and `temporal_precedence == True`. Otherwise it is a `HARD` violation and the retry prompt instructs associative phrasing. This is the mechanism behind *"SHAP does not establish that changing a feature changes the outcome."*

```python
CAUSAL = re.compile(r"\b(caused?|because of|due to|drove|resulted in|led to|triggered)\b", re.I)
```

**Rule 6 — Confidence is injected, never generated.** The confidence value is computed in L8 and rendered by the UI. It is **not** in the narrator's output schema, so there is no field for the model to hallucinate into.

**Rule 7 — Levers are IDs, not text.** The recommendation schema requires `lever_id`; a value not in the catalogue means the recommendation is dropped and logged. The model chooses among eligible levers; it cannot author one.

### 6.4 The failure ladder when Gate 2 fails

1. **First failure** → re-narrate once, with the typed violations appended as explicit correction instructions. (Cap = 1. A second retry is where cost and latency go to die.)
2. **Second failure** → **deterministic template.** A fully mechanical narrative rendered from the bundle by `f`-string. Less fluent, completely faithful. The UI labels it: *"Generated in verified template mode — the drafted narrative failed 2 checks."*
3. **Structural failure** (bundle itself insufficient) → abstain. Show the ranked hypotheses and the evidence, with no narrative.

**Note that the template mode is a feature, not a fallback you hide.** Being able to show a judge the moment the system refuses to let a fluent sentence through is the single most persuasive demo beat you have.

---

## PART 7 — DATA DESIGN FOR THE ROUND 2 PROTOTYPE

**Business setting:** a mid-market omnichannel D2C retailer in India, ~₹40 Cr annual revenue, 18 months of history. Chosen because it is the narrow scope Round 1 committed to (regional revenue anomalies for ops leads), and because it naturally produces heterogeneous grains without contrivance.

### 7.1 The five connected KPIs

The connection is a **single identity**, which is what makes multi-factor movement demonstrable:

```
Net Revenue = Sessions × Conversion Rate × Average Order Value × (1 − Refund Rate)
```

| # | KPI | Grain | Source | Refresh / lag | Type |
|---|---|---|---|---|---|
| K1 | **Net Revenue** (₹) | day × region × segment × product_category × channel | S1 warehouse | daily 06:00, T-1 | Fundamental (additive) |
| K2 | **Orders** | day × region × segment × product_category × channel | S1 warehouse | daily 06:00, T-1 | Fundamental (additive) |
| K3 | **Average Order Value** (₹) | derived = Gross Revenue / Orders | S1 warehouse | daily 06:00, T-1 | **Derived (ratio — non-additive)** |
| K4 | **Checkout Conversion Rate** (%) | **hour** × region × channel × funnel_step | S2 product analytics | hourly, T-2h | **Derived (ratio), different grain — no product dimension** |
| K5 | **Refund Rate** (%) | **week** × region × product_category | S3 finance | weekly Mon, **T+3 days** | **Derived (ratio), different cadence, lagging** |

**Why this exact set.** It satisfies "3–5 connected KPIs" with a real identity rather than five unrelated metrics; it forces genuine grain reconciliation (K4 has no `product_category`, so attribution on K4 can only descend to `region × channel` — and the system must *say so* rather than silently pretending otherwise); and K5's T+3 lag creates an honest freshness problem where the most recent week's refund data does not exist yet, which is exactly the kind of real complication the case asks for.

**K3/K4/K5 are ratios, which matters.** Per CMMD and Adtributor §4, explanatory power over a ratio is not well-defined — attribute on the fundamental numerator and denominator instead. Your semantic contract encodes this as `additive: false` + `attribute_via: [orders, sessions]`, and the engine *enforces* it. This is a small detail that will land hard with a technical judge, because it is the kind of thing only someone who actually implemented attribution knows.

### 7.2 Dimensions and hierarchy

```
region      : North · South · East · West                 (4)
segment     : Enterprise · SMB · Consumer                 (3)
product_cat : Apparel · Electronics · Home · Beauty · NewLaunch  (5)
channel     : Web · Mobile App · Marketplace · Retail Partner    (4)
```
240 cells per day × ~550 days ≈ 132,000 fact rows. Large enough to be real, small enough to be instant in DuckDB.

Hierarchy for drill-down: `region → segment → product_cat → channel`, but **Adtributor evaluates all four dimensions independently first** and only then descends into the winner. This is the Adtributor design and it is why it beats greedy top-down drill-down: a top-down walk commits to the biggest region before it has looked at channel at all.

### 7.3 Sources — exactly three, with genuinely different characteristics

| ID | Source | Contents | Grain | Cadence | Quality quirk (deliberate) |
|---|---|---|---|---|---|
| **S1** | `warehouse` (DuckDB) | `fact_orders`, `dim_*`, `schema_change_log` | daily, full dimensionality | daily 06:00, T-1 | One deliberate schema change: `channel` value `"marketplace"` renamed `"Marketplace"` on 2026-06-14, splitting a series. **This is the Round 1 differentiator made real.** |
| **S2** | `product_analytics` | `fact_sessions`, `fact_funnel_steps` | hourly, **no product dimension** | hourly, T-2h | 3.5% null `region` (VPN/unknown geo). Forces an explicit completeness check. |
| **S3** | `ops_context` | `support_tickets`, `crm_notes`, `market_events`, `deploy_changelog`, `finance_adjustments` | per-document / per-event; finance weekly | tickets near-real-time; CRM weekly; finance **T+3** | Ticket volume itself has a weekday pattern — a naive count comparison mis-reads Monday spikes as signal. |

### 7.4 Document corpus (the only thing embedded)

| Corpus | Count | Fields | Embedded |
|---|---|---|---|
| `support_tickets` | ~900 | id, created_at, account_id, region, segment, channel, category, subject, body, severity, resolved_at | **Yes** (`subject + "\n" + body`) |
| `crm_notes` | ~350 | id, note_date, account_id, region, segment, author_role, body | **Yes** (body) — **restricted source** |
| `market_events` | ~120 | id, event_date, region, category, headline, body, source_name | **Yes** (`headline + "\n" + body`) |
| `deploy_changelog` | ~180 | id, deployed_at, service, component, summary, risk_level, rollback_at | **No** — exact join on time × service |
| `schema_change_log` | ~25 | id, changed_at, table, column, change_type, actor, note | **No** — exact join |
| `finance_adjustments` | ~80 | week, region, product_cat, refund_amount, reason_code | **No** — a fact table |

**~1,370 embedded documents.** Documents are short and atomic — **do not chunk them** (Part 11.3).

### 7.5 Ground-truth event injection — your biggest evaluation advantage

The generator writes `data/ground_truth.json` recording every event it injected: date, affected slice, true driver, magnitude, and which evidence documents were planted as genuine corroboration versus which are decoys. Because you know the answers, **you can report real detection precision/recall and real Top-1/Top-2 attribution accuracy in the demo.** Almost no competing team will be able to quote a measured accuracy number. Make sure yours is on a slide.

Six injected events, one per demo scenario:

| Event | Date | Slice | True driver | Evidence planted | Decoys planted |
|---|---|---|---|---|---|
| E1 | 2026-07-12 | West × Web + Mobile App | Payment gateway degradation | 34 tickets (payment category), 1 deploy record | 1 unrelated market event same week |
| E2 | 2026-06-02 | South × Apparel | Ambiguous: competitor promo **vs** stockout | 6 market events, 11 CRM notes, 1 inventory note — **genuinely balanced** | — |
| E3 | 2026-08-05 | East × SMB | Unknown / thin evidence | 2 vague tickets only | — |
| E4 | 2026-07-20 | All × NewLaunch | New product, 23 days of history | 4 CRM notes | — |
| E5 | 2026-06-14 | All × Marketplace | **Schema change**, not a business event | 1 schema_change_log row | 12 tickets (coincidental) |
| E6 | 2026-07-12 | (same as E1) | Same event, viewed by two personas | CRM notes visible to Finance only | — |

### 7.6 Personas and entitlements

| Persona | Role | Row access | Column access | Source access | Wants |
|---|---|---|---|---|---|
| **Priya Nair** | Regional Ops Lead, West | `region = 'West'` only | no `margin`, no `refund_reason_detail` | S1, S2, tickets, changelog. **No CRM notes.** | What broke, who fixes it, by when |
| **Arjun Mehta** | Finance Director | all regions | all columns incl. `margin` | all sources incl. CRM notes | ₹ impact, margin effect, quarter risk |
| **Meera Rao** | Analytics Lead (escalation target) | all regions | all columns | all sources **+ method/diagnostics panel** | Method, gate results, lineage, whether to override |

**Why this specific design earns its keep:** on event E1, Priya and Arjun see the *same detected movement* but different narratives, different recommended actions, different owners — and Priya's evidence panel shows *"2 evidence items withheld — source `crm_notes` not permitted for role `ops_lead`"*. The entitlement rule visibly changes the answer, not merely the styling. That is a far stronger demonstration than a greyed-out column.

### 7.7 Lineage record

Every metric value carries provenance, produced by the semantic layer, not reconstructed later:

```python
class LineageRecord(BaseModel):
    metric_id: str
    source_id: str                 # S1 | S2 | S3
    source_table: str
    compiled_sql: str              # the actual SQL executed
    as_of: datetime                # source watermark
    computed_at: datetime
    freshness_lag_hours: float
    row_count: int
    null_rate: float
    filters_applied: list[str]     # incl. entitlement predicates
    columns_masked: list[str]
    contract_version: str
```

---

## PART 8 — THE KPI SEMANTIC LAYER

The Tableau reviewer in your own corpus named the problem precisely: *"Due to the lack of a semantic layer, it frequently results in inconsistent data reported."* The semantic layer is the thing that makes lineage, materiality, entitlements and attribution-method selection **data rather than code**, and it is where the Round 2 phrase "lightweight KPI or semantic contract" is satisfied literally.

### 8.1 Representation: YAML on disk → Pydantic in memory → SQL at the boundary

YAML because a judge (and a business owner) can read it. Pydantic because it must be validated, versioned and typed. SQL compiled from it because that is the only way every number in the system provably comes from one definition.

```yaml
# semantic/kpis/net_revenue.yaml
id: net_revenue
version: "1.2.0"
name: Net Revenue
definition: >
  Gross order value less returns, discounts and cancellations, for orders
  with status in (shipped, delivered). Excludes internal test accounts.
  Recognised on order date, not shipment date.
formula:
  expression: "SUM(gross_amount - discount_amount - return_amount)"
  base_table: s1.fact_orders
  filters: ["order_status IN ('shipped','delivered')", "is_test_account = FALSE"]
unit: INR
additive: true                 # fundamental measure → EP is well-defined
grain: [date, region, segment, product_category, channel]
dimensions:
  - {name: region,           cardinality: 4, hierarchy_level: 1}
  - {name: segment,          cardinality: 3, hierarchy_level: 2}
  - {name: product_category, cardinality: 5, hierarchy_level: 3}
  - {name: channel,          cardinality: 4, hierarchy_level: 4}
drivers:                       # the identity, used by LMDI decomposition
  identity: "sessions * conversion_rate * average_order_value * (1 - refund_rate)"
  children: [sessions, conversion_rate, average_order_value, refund_rate]
detection:
  seasonality_period: 7
  method: stl_robust_z_pelt
  z_threshold: 3.0
  pelt_penalty: 12.0
  min_history_days: 56         # 8 weekly cycles; below this → sparse-history path
materiality:
  min_abs_effect_inr: 250000
  min_rel_effect_pct: 2.0
  min_duration_days: 3
  rule: "(abs_effect >= min_abs_effect_inr OR rel_effect >= min_rel_effect_pct) AND duration >= min_duration_days"
freshness:
  cadence: daily
  expected_lag_hours: 30
  stale_after_hours: 48
lineage:
  source_id: S1
  upstream: [s1.raw_orders, s1.raw_returns]
  owner: "data-platform@company.example"
security:
  classification: internal
  row_filter_by_role:
    ops_lead: "region = :user_region"
    finance_director: "TRUE"
    analytics_lead: "TRUE"
  restricted_columns:
    margin: [finance_director, analytics_lead]
business_owner: "VP Revenue Operations"
allowed_levers: [L_GATEWAY_ESCALATE, L_PROMO_RESPONSE, L_INVENTORY_EXPEDITE, L_PRICING_REVIEW]
```

And the derived-ratio case, which encodes the CMMD lesson:

```yaml
# semantic/kpis/conversion_rate.yaml  (abridged)
id: conversion_rate
additive: false                       # ratio → do NOT run Adtributor on this directly
attribute_via: [orders, sessions]     # attribute on the fundamentals instead
grain: [hour, region, channel, funnel_step]
grain_note: "No product_category. Attribution cannot descend below region × channel."
detection: {seasonality_period: 24, method: stl_robust_z_pelt, min_history_days: 21}
materiality: {min_abs_effect_pp: 0.8, min_rel_effect_pct: 5.0, min_duration_days: 2}
freshness: {cadence: hourly, expected_lag_hours: 2, stale_after_hours: 6}
```

### 8.2 The loader and the chokepoint

```python
# semantic/contract.py
class KPIContract(BaseModel):
    id: str; version: str; name: str; definition: str
    formula: Formula; unit: str; additive: bool
    grain: list[str]; dimensions: list[Dimension]
    drivers: Drivers | None; detection: DetectionConfig
    materiality: MaterialityRule; freshness: FreshnessRule
    lineage: LineageSpec; security: SecuritySpec
    business_owner: str; allowed_levers: list[str]
    attribute_via: list[str] | None = None

    def compile_sql(self, window, dims, access: AccessDecision) -> tuple[str, LineageRecord]: ...

# semantic/gateway.py  — THE ONLY MODULE THAT TOUCHES DuckDB
def guarded_query(kpi_id: str, window: Window, dims: list[str], principal: Principal) -> MetricSeries:
    contract = registry.get(kpi_id)
    access   = entitlements.decide(principal, contract)      # row filter + column mask + source allowlist
    sql, lineage = contract.compile_sql(window, dims, access)
    df   = conn.execute(sql).df()
    audit.write(principal, kpi_id, sql, len(df), access)     # append-only, always
    return MetricSeries(df=df, contract=contract, lineage=lineage, access=access)
```

**Enforce the chokepoint with a test, not a convention:**

```python
def test_single_data_access_path():
    hits = [p for p in Path("src").rglob("*.py")
            if "conn.execute" in p.read_text() and p.name != "gateway.py"]
    assert not hits, f"Direct DuckDB access outside the gateway: {hits}"
```

That five-line test is worth showing to a judge. It is the difference between claiming governance and having it.

### 8.3 What the semantic layer buys you, concretely

1. **Lineage is automatic**, because every read produces a `LineageRecord` including the exact SQL.
2. **Materiality is per-KPI and inspectable** — the UI shows the rule that fired, so "why did you alert me?" has a literal answer.
3. **Entitlements cannot be bypassed** — one code path, enforced by test.
4. **Attribution method selection is declarative** — `additive: false` routes to `attribute_via`, and no one has to remember the ratio rule.
5. **Contracts are versioned** — a definition change is a semver bump recorded on every insight generated under it, which is the honest answer to the "Marketing redefined the lead bucket" problem from your Reddit evidence.

---

## PART 9 — DETECTION ENGINE

### 9.1 Method selection — what ships and what does not

You listed six candidates. Here is the honest cut, with reasons for the rejections, because *what you leave out* is the part that shows judgment.

| Method | Ships? | Reason |
|---|---|---|
| **Coverage gate** (history sufficiency) | ✅ **Yes — runs first** | Nothing downstream is valid without it, and it is what makes the sparse-history scenario a designed path rather than a crash. |
| **STL decomposition** | ✅ **Yes** | Weekly seasonality dominates daily retail revenue. Without it, every Monday is an anomaly. Sourced requirement: remove trend/seasonality *before* break detection. |
| **Robust z-score on residual (MAD-based)** | ✅ **Yes** | Point-anomaly test with an interpretable effect size. MAD rather than standard deviation because a single outlier inflates σ and masks the next one. |
| **PELT changepoint on residual** | ✅ **Yes** | Distinguishes a *sustained regime shift* from a one-day blip — which is the actual business question. The penalty term is the tunable signal/noise control, per contract. |
| **Minimum business-effect gate** | ✅ **Yes** | The case names it. Also the single best answer to "meaningful vs noise." |
| **CUSUM** | ❌ **No — named, not built** | CUSUM is an *online* monitor for abrupt persistent mean shifts on a stream. Your prototype is batch-plus-on-demand; there is no stream to monitor. Building it adds a method with no visible demo behaviour. **Named on the production roadmap.** |
| **Bayesian online changepoint detection** | ❌ **No — named, not built** | The right tool for slow drift, but it needs hazard-rate tuning per KPI to behave, and slow drift is not one of your six scenarios. Adding it means one more thing that can misfire on stage for zero narrative gain. |
| **Fixed control limits / flat % thresholds** | ❌ **Rejected outright** | This is the thing you are arguing against. Say so explicitly: *"an 8% drop in a volatile metric may be noise; a 2% drop in a stable one may be real"* — that sentence justifies the whole layer. |

**Round 1 said four methods; Round 2 ships two plus two gates. [CHANGE]** Defend it as scope discipline: *"we implemented the two that change the answer and named the two that would matter in production. Shipping four half-tuned detectors would have been decoration."*

### 9.2 The exact flow

```
raw KPI series (from semantic layer, entitlement-filtered)
   │
   ├─ 0. COVERAGE GATE ─────────────────────────────────────────────
   │     n_observations >= contract.detection.min_history_days ?
   │     ├─ NO  → SPARSE-HISTORY PATH (9.4)  ← Scenario 4 lives here
   │     └─ YES → continue
   │
   ├─ 1. PREPROCESS ────────────────────────────────────────────────
   │     calendar align · impute single-day gaps by seasonal median ·
   │     flag imputations · apply schema_change_log stitching ·
   │     hard-fail if >10% of window imputed
   │
   ├─ 2. DECOMPOSE ─────────────────────────────────────────────────
   │     STL(period = contract.detection.seasonality_period, robust=True)
   │     → trend, seasonal, residual
   │
   ├─ 3. POINT ANOMALY ─────────────────────────────────────────────
   │     robust_z = (residual - median(residual)) / (1.4826 * MAD(residual))
   │     candidate if |robust_z| >= contract.detection.z_threshold
   │
   ├─ 4. REGIME SHIFT ──────────────────────────────────────────────
   │     ruptures.Pelt(model="l2").fit(residual).predict(pen=contract.detection.pelt_penalty)
   │     → changepoint dates; keep those inside the window
   │     classify: SPIKE (point only) | LEVEL_SHIFT (changepoint + sustained) | DRIFT (neither, trend slope)
   │
   ├─ 5. QUANTIFY ──────────────────────────────────────────────────
   │     baseline   = expected level from trend+seasonal (counterfactual "no event" path)
   │     abs_effect = Σ(actual − baseline) over the post-changepoint window
   │     rel_effect = abs_effect / Σ(baseline)
   │     p_value    = Welch t-test, pre-window residuals vs post-window residuals
   │
   ├─ 6. MATERIALITY GATE (business rule from contract) ────────────
   │     (abs_effect >= min_abs_effect) OR (rel_effect >= min_rel_effect)
   │     AND duration >= min_duration_days
   │     ├─ FAIL → emit NO_MATERIAL_FINDING (and say why, with the numbers)
   │     └─ PASS → CandidateEvent
   │
   └─→ CandidateEvent { kpi, window, type, changepoint_date, abs_effect,
                        rel_effect, p_value, baseline_series, method_trace }
```

### 9.3 Why each step exists — the one-line defence for each

| Step | If you removed it |
|---|---|
| Coverage gate | You would run STL on 20 points and produce confident garbage — the exact "confidently wrong" failure your deck is built against. |
| Preprocess / schema stitching | The E5 marketplace rename would appear as a genuine 40% collapse. This step is the Reddit finding (§9.4) made operational. |
| STL | Every Monday and every festival week fires an alert. Alert fatigue, immediately. |
| Robust z (MAD) | A single extreme day inflates σ and hides the next real event. |
| PELT | You cannot tell "one bad day" from "something broke and stayed broken" — and those two demand completely different actions. |
| Materiality gate | You alert on statistically real, commercially irrelevant moves. Fraud ops learned this the expensive way: ~90–95% industry false-positive rates, 70% of analyst time on alerts that were fine (D6). |

### 9.4 The sparse-history path (Scenario 4)

When `n < min_history_days`, do not run STL, do not run PELT, and **say so**. Instead:

1. **Peer-group baseline.** Compare the new product/market to the pooled trajectory of comparable cohorts at the same age (`NewLaunch` at day 23 vs Apparel/Beauty launches at day 23).
2. **Wide interval.** Report a range from peer-cohort dispersion, not a point estimate.
3. **Hard confidence ceiling.** `confidence_band` is capped at `LOW` by rule — it cannot be argued upwards by strong evidence.
4. **Method transparency.** `method: "peer_cohort_baseline"`, `caveat: "23 days of history; 8 weeks required for seasonal detection. Seasonality is assumed, not measured."`
5. **Different recommendation class.** Levers tagged `requires_stable_baseline: true` are filtered out entirely — you do not recommend a pricing change off 23 days of data.

This turns "we don't have enough data" from an error state into a designed, defensible product behaviour. It is also, in my view, the single most under-rated scenario in the Round 2 list, because it is the one most teams will fake.

---

## PART 10 — DRIVER ATTRIBUTION

Three stages, all deterministic. **The LLM appears nowhere in this part.**

### 10.1 Stage A — Identity decomposition (which *factor* moved)

`Net Revenue = Sessions × Conversion × AOV × (1 − Refund Rate)`. The question "how much of the ₹ change is attributable to each factor" has a well-defined, residual-free answer: the **Logarithmic Mean Divisia Index (LMDI)**.

For a multiplicative identity `V = ∏ x_k`:

```
ΔV = Σ_k  L(V_1, V_0) · ln(x_k1 / x_k0)        where  L(a,b) = (a − b) / (ln a − ln b)
```

**Why LMDI and not a naive sequential split:** naive "change one factor at a time" decomposition leaves an unexplained interaction residual whose size depends on the order you chose. LMDI is perfectly additive — the factor contributions sum exactly to ΔV, with **zero residual and no ordering dependence**. When a judge asks "why do your four contributions add up exactly?", that is the answer, and it is a good one. (The familiar FP&A price/volume/mix variance bridge is the same idea in business dress; render the output as a **waterfall**, which is the visual finance people already read.)

```python
def lmdi(v0, v1, factors_0: dict, factors_1: dict) -> dict[str, float]:
    L = (v1 - v0) / (math.log(v1) - math.log(v0)) if v1 != v0 else v0
    return {k: L * math.log(factors_1[k] / factors_0[k]) for k in factors_0}
```

Output: *"Of the ₹38.2L shortfall, conversion explains ₹34.1L (89%), AOV ₹2.6L (7%), sessions ₹1.5L (4%), refunds ₹0."* **Note the grain constraint fires here:** conversion (K4) has no `product_category`, so Stage B on the conversion branch can only descend to `region × channel`, and the UI must display that limit rather than quietly omitting it.

### 10.2 Stage B — Dimensional attribution (which *slice* moved): Adtributor

For the fundamental measure, run Adtributor over all four dimensions independently.

```python
def adtributor(forecast: pd.DataFrame, actual: pd.DataFrame, dims: list[str],
               t_ep: float = 0.67, t_eep: float = 0.10) -> list[DimensionExplanation]:
    F, A = forecast.value.sum(), actual.value.sum()
    out = []
    for dim in dims:
        f = forecast.groupby(dim).value.sum(); a = actual.groupby(dim).value.sum()
        elements = []
        for e in f.index.union(a.index):
            fe, ae = f.get(e, 0.0), a.get(e, 0.0)
            ep = (ae - fe) / (A - F) if A != F else 0.0            # Eq. 4
            p, q = fe / F, ae / A                                   # Eqs. 5, 6
            s = js_divergence_term(p, q)                            # Eq. 7
            elements.append(Element(e, ep, s, fe, ae))
        elements.sort(key=lambda x: -x.surprise)                    # rank by SURPRISE
        cand, explained, surprise = [], 0.0, 0.0
        for el in elements:
            if el.ep > t_eep:                                       # succinctness floor
                cand.append(el); explained += el.ep; surprise += el.surprise
            if explained >= t_ep:
                break
        if explained >= t_ep:
            out.append(DimensionExplanation(dim, cand, explained, surprise))
    return sorted(out, key=lambda d: -d.surprise)                   # winner = most surprising

def js_divergence_term(p, q):
    m = (p + q) / 2
    t = 0.0
    if p > 0: t += 0.5 * p * math.log(p / m)
    if q > 0: t += 0.5 * q * math.log(q / m)
    return t
```

**The "forecast" input** is the STL baseline from Detection step 5 — the counterfactual "no event" path — computed per cell. This is a clean reuse: detection already produced exactly the `F` that attribution needs.

**Why this beats the obvious alternatives, stated plainly:**
- vs. **"rank dimensions by size of change"** — that is Adtributor's own strawman, and the paper measured it at **20% accuracy versus 95%**. It blames whatever is biggest.
- vs. **Shapley values** — Shapley answers "how much did each feature contribute to a prediction," not "which dimension's *share* shifted unexpectedly." It is also `O(2^n)` in dimensions, needs a model to explain, and produces no natural notion of surprise. Tellius ships Shapley and its own users report the results surface non-meaningful correlations (your §9.3 quote). Adtributor is cheaper, deterministic, and purpose-built for exactly this question.
- vs. **asking an LLM** — no ranking a model produces is reproducible, auditable or bounded. This is the case's own prohibition.

**Ratios (K3, K4, K5):** `additive: false` → do not run Adtributor directly. Per CMMD, attribute on the fundamental numerator and denominator and combine. The engine reads `attribute_via` from the contract, so this is not something a developer has to remember.

### 10.3 Stage C — Significance and counterfactual

**C1 — Contribution significance.** For each candidate slice, test whether the change is distinguishable from noise: two-proportion z-test for rates, Welch's t-test for levels, on pre- vs post-changepoint windows. Slices failing at α = 0.05 are demoted, not dropped, and are shown in the UI as "considered, not significant" — which is itself a trust signal.

**C2 — Temporal precedence.** A candidate cause dated *after* the changepoint cannot be the cause. Trivial to check, embarrassing to miss, and it is the cheapest guard against the most common LLM error in this domain.

**C3 — Difference-in-differences against a matched control.** This is the correlation-to-causation step, and it is 40 lines.

```
control slice := the slice with the highest pre-period correlation to the affected slice,
                 that is NOT itself flagged, matched on segment and category

DiD = (Y_affected,post − Y_affected,pre) − (Y_control,post − Y_control,pre)
```

Interpretation, and the exact licence it grants:
- **DiD large and significant** → the move is specific to the affected slice → `counterfactual.passed = True` → **causal language is licensed** in the narrative.
- **DiD ≈ 0** → the control moved too → this is a market-wide or systemic effect, not a slice-specific cause → causal language is **denied**; the narrative must say "consistent with a market-wide movement."
- **Control unavailable** (all comparable slices flagged, or too few) → `counterfactual.passed = False`, reason recorded, causal language denied.

**This is the mechanism behind your "we don't confuse correlation with causation" claim.** Without it that claim is a slogan; with it, it is a boolean in the state object that a gate reads.

### 10.4 Stage D — The ranked hypothesis structure

```python
class Hypothesis(BaseModel):
    id: str
    rank: int
    statement: str                       # deterministic template, NOT LLM-generated
    cause_bucket: Literal["internal_product","internal_pricing","internal_data_schema",
                          "external_competitor","external_market","external_seasonal","unknown"]
    slice: dict[str, str]                # {"region":"West","channel":"Web|Mobile App"}
    contribution_pct: float              # from LMDI + Adtributor EP
    contribution_abs: float
    surprise: float                      # JS divergence
    statistical_significance: float      # p-value
    temporal_precedence: bool
    counterfactual: CounterfactualResult # {passed, did_estimate, control_slice, reason}
    supporting_evidence: list[EvidenceRef]
    contradicting_evidence: list[EvidenceRef]     # ← required field, see below
    evidence_strength: float             # 0–1, deterministic (10.5)
    score: float
    causal_language_licensed: bool       # = counterfactual.passed AND temporal_precedence
```

**`contradicting_evidence` is a required field, not an optional nicety.** Retrieval explicitly searches for disconfirming evidence — documents in the affected window that describe the slice behaving *normally*, or that support a competing hypothesis. A hypothesis presented with zero contradicting evidence, in a system that never looked for any, is a confirmation-bias machine. Making the field mandatory forces the search. On Scenario 2 (E2), this is what produces the honest "two hypotheses, each with support and each with a problem" view instead of a fake winner.

### 10.5 Deterministic hypothesis scoring

```python
score = (0.30 * norm(abs(contribution_pct))
       + 0.15 * norm(surprise)
       + 0.15 * (1 - p_value)
       + 0.20 * evidence_strength
       + 0.10 * (1.0 if temporal_precedence else 0.0)
       + 0.10 * (1.0 if counterfactual.passed else 0.0))

evidence_strength = (0.40 * norm(distinct_supporting_docs)      # count, capped at 20
                   + 0.25 * norm(source_diversity)              # how many distinct source types
                   + 0.20 * norm(temporal_tightness)            # evidence clustered near changepoint
                   - 0.25 * norm(distinct_contradicting_docs))
```

Weights live in `config/scoring.yaml`, are versioned, and are the **only** thing feedback is allowed to tune (Part 15) — and only once there are ≥30 labelled cases. Until then they are frozen and you say they are hand-set. Claiming a learned weighting off 4 labelled examples is exactly the kind of thing a sharp judge will catch.

---

## PART 11 — EMBEDDING + RETRIEVAL ARCHITECTURE

### 11.1 The pipeline

```
Winning slice + window (from Attribution)      Entitlements (from L1)
              │                                        │
              └──────────────┬─────────────────────────┘
                             ↓
   ┌─── STRUCTURED EVIDENCE (exact, no embeddings) ──────────────┐
   │  deploy_changelog  WHERE deployed_at ∈ [cp−7d, cp+2d]       │
   │                      AND service ∈ slice_services            │
   │  schema_change_log WHERE changed_at ∈ [cp−7d, cp+2d]        │
   │                      AND table ∈ contract.lineage.upstream   │
   │  finance_adjustments joined on week × region × category      │
   └──────────────────────────────────────────────────────────────┘
                             +
   ┌─── UNSTRUCTURED EVIDENCE (hybrid retrieval) ────────────────┐
   │  1. HARD PRE-FILTER (never a soft signal):                  │
   │       date ∈ [cp−14d, cp+7d]                                │
   │       AND slice fields match (region/segment/channel)       │
   │       AND source_id ∈ principal.allowed_sources             │
   │     → ~40–120 candidates from ~1,370                        │
   │  2. QUERY CONSTRUCTION (deterministic, no LLM):             │
   │       from contract + slice + cause-bucket keyword sets      │
   │  3. BM25 over candidates          → ranked list A            │
   │  4. Dense cosine over candidates  → ranked list B            │
   │  5. RRF fuse (k=10)               → ranked list C            │
   │  6. Relevance floor; cohort roll-up; top-8 per hypothesis    │
   │  7. CONTRADICTION PASS: re-query for disconfirming evidence  │
   └──────────────────────────────────────────────────────────────┘
                             ↓
              Evidence[] with per-signal scores exposed to the UI
```

### 11.2 Why hybrid, and why RRF specifically

BM25 handles exact and rare terms (`ORD-88213`, `SKU-4471`, `PG-TIMEOUT-504`); dense handles paraphrase (`"card keeps getting rejected"` ↔ `"gateway declines"`). Your corpus has both in the same window. RRF fuses **by rank rather than score**, which avoids the score-incompatibility that makes naive weighted averaging unstable when a BM25 score of 14.2 has to be combined with a cosine of 0.81. Reported gains are consistent: RRF NDCG 0.7068 vs 0.6983 (BM25) and 0.6953 (dense) on WANDS.

```python
def rrf(rank_lists: list[list[str]], k: int = 10) -> dict[str, float]:
    scores = defaultdict(float)
    for lst in rank_lists:
        for rank, doc_id in enumerate(lst, start=1):
            scores[doc_id] += 1.0 / (k + rank)
    return dict(sorted(scores.items(), key=lambda kv: -kv[1]))
```

### 11.3 Chunking — do not chunk

A support ticket is ~80 words. A CRM note is ~120. A market event is ~60. **One document = one embedding.** Chunking short atomic records destroys the metadata binding (which account, which region, which date) that your pre-filter depends on, and it fragments the very cohort-level signal D7 says is the real predictor. This is why the LangChain text-splitter use case disappears.

The only exception: a support ticket with a long threaded conversation gets `subject + first_message + last_message` concatenated, deliberately dropping the middle. Rationale from D7: *persistence, not intensity* is the signal — the first and last messages capture "did this recur and did it stay unresolved" better than the middle of the thread does.

### 11.4 Metadata (drives filtering, and it is where most of the accuracy lives)

```python
{"doc_id","source_id","doc_type","created_at","region","segment","channel",
 "product_category","account_id","category","severity","security_class","cohort_key"}
```

**Metadata filtering does more work than the embedding does.** Cutting 1,370 documents to 60 by date and slice is a bigger precision win than any model upgrade. Say that to a judge — it is the kind of statement that separates people who have built retrieval from people who have read about it.

### 11.5 Cohort roll-up (implementing D7)

Individual tickets are weak evidence. After retrieval, group by `(cause_category, week)` and emit **one cohort evidence item**: *"34 payment-failure tickets across 29 accounts in West, 12–18 July, vs a trailing-8-week median of 6/week (5.7×)."* Individual tickets remain drill-downable but do not each count as evidence in `evidence_strength`.

**This also prevents a real scoring bug:** 34 tickets about one incident would otherwise inflate `distinct_supporting_docs` 34-fold and let volume masquerade as diversity.

### 11.6 The in-domain retrieval eval — non-negotiable

Hand-label 20 `(query → relevant doc_ids)` pairs from your generated corpus (you know the planted evidence, so this is cheap). Report **precision@5, recall@10, MRR** for BM25 alone, dense alone, and RRF-fused. Run it in CI.

Two reasons this matters more than it looks: it is how you actually justify your embedding choice (leaderboard rank does not transfer in-domain), and it converts "we use RAG" into "our retrieval scores precision@5 = 0.82 on our own labelled set." One of those sentences survives a technical judge.

### 11.7 What you deliberately do NOT build

| Not building | Why |
|---|---|
| **Cross-encoder reranking** | Reranking targets top-100 of ~200 fused candidates. Your entitlement-filtered pool is ~40. There is nothing to rerank. **V2** if the eval shows precision@5 < 0.7. |
| **Agentic / iterative retrieval** | A model deciding to search again is a model deciding what evidence it sees. Architecturally forbidden here. |
| **Query rewriting by LLM** | Queries are built deterministically from the contract and slice, so they are reproducible and auditable. |
| **GraphRAG / knowledge graph** | See Part 24. Your entity relations are already a star schema; a graph adds a second, weaker copy of it. |
| **HyDE / multi-query expansion** | Solves recall problems you do not have on a 40-document candidate pool. |

---

## PART 12 — THE LANGGRAPH WORKFLOW

### 12.1 State

```python
class InsightState(TypedDict, total=False):
    # request
    run_id: str; query_text: str; principal: Principal; persona: PersonaProfile
    # resolved
    kpi_id: str; window: Window; requested_dims: list[str]
    contract: KPIContract; access: AccessDecision
    # analysis
    freshness: FreshnessReport; quality: QualityReport
    metric_series: MetricSeries; detection: DetectionResult
    materiality: MaterialityVerdict
    identity_split: dict[str, float]; attribution: AttributionResult
    counterfactual: CounterfactualResult
    evidence: list[Evidence]; hypotheses: list[Hypothesis]
    bundle: EvidenceBundle                    # frozen, hashed
    # generation
    narrative: Narrative | None; verification: VerificationReport | None
    narration_attempts: int                   # retry cap lives here
    recommendations: list[Recommendation]
    # decision
    confidence: Confidence; deferral: DeferralDecision
    outcome: Literal["delivered","template","abstained","clarify","no_finding","access_denied"]
    # cross-cutting
    telemetry: list[NodeTelemetry]; lineage: list[LineageRecord]; feedback: Feedback | None
```

### 12.2 The graph

```
                                    START
                                      │
                            ┌─────────▼─────────┐
                            │ 1 resolve_intent  │  LLM (Haiku 4.5)
                            └─────────┬─────────┘
                            ┌─────────▼─────────┐
                            │ 2 load_contract   │  deterministic
                            └─────────┬─────────┘
                            ┌─────────▼─────────┐
                            │ 3 enforce_entitle │  deterministic
                            └─────────┬─────────┘
                        denied ◄──────┴──────► allowed
                          │                      │
                 ┌────────▼────────┐   ┌─────────▼─────────┐
                 │ X access_denied │   │ 4 gate_quality    │  ══ GATE 1 ══
                 │      → END      │   └─────────┬─────────┘
                 └─────────────────┘   fail ◄────┴────► pass
                                        │              │
                              ┌─────────▼──────┐ ┌─────▼──────┐
                              │ X abstain_data │ │ 5 detect   │  statistical
                              │     → END      │ └─────┬──────┘
                              └────────────────┘  ┌────▼─────────────┐
                                                  │ 6 materiality    │  business rule
                                                  └────┬─────────────┘
                                     not material ◄────┴────► material
                                          │                     │
                                ┌─────────▼───────┐   ┌─────────▼──────────┐
                                │ X no_finding    │   │ 7 decompose (LMDI) │
                                │     → END       │   └─────────┬──────────┘
                                └─────────────────┘   ┌─────────▼──────────┐
                                                      │ 8 attribute        │  Adtributor
                                                      └─────────┬──────────┘
                                                      ┌─────────▼──────────┐
                                                      │ 9 counterfactual   │  DiD
                                                      └─────────┬──────────┘
                                                      ┌─────────▼──────────┐
                                                      │ 10 retrieve_evid   │  hybrid + embeddings
                                                      └─────────┬──────────┘
                                                      ┌─────────▼──────────┐
                                                      │ 11 rank_hypotheses │  → freeze bundle
                                                      └─────────┬──────────┘
                                                      ┌─────────▼──────────┐
                                                      │ 12 gate_sufficiency│  ══ GATE 1b ══
                                                      └─────────┬──────────┘
                        ┌────────────────┬──────────────────────┼────────────────┐
                 insufficient       ambiguous               sufficient           │
                        │                │                      │                │
              ┌─────────▼──────┐ ┌───────▼────────┐   ┌─────────▼────────┐      │
              │ X abstain_evid │ │ X clarify      │   │ 13 narrate       │ LLM  │
              │    → END       │ │    → END       │   └─────────┬────────┘      │
              └────────────────┘ └────────────────┘   ┌─────────▼────────┐      │
                                                      │ 14 verify        │ ══ GATE 2 ══
                                                      └─────────┬────────┘      │
                                       ┌──────────────┬─────────┴────────┐      │
                                  pass │      fail & attempts<2 │   fail & attempts>=2
                                       │              └─────────┘              │
                                       │              (loop to 13)   ┌─────────▼────────┐
                                       │                             │ 15 template_mode │
                                       │                             └─────────┬────────┘
                                       └──────────────┬────────────────────────┘
                                              ┌───────▼────────┐
                                              │ 16 recommend   │  rules + LLM phrasing
                                              └───────┬────────┘
                                              ┌───────▼────────┐
                                              │ 17 calibrate   │  deterministic
                                              └───────┬────────┘
                                              ┌───────▼────────┐
                                              │ 18 defer_check │  cost-sensitive rule
                                              └───────┬────────┘
                                  defer ◄─────────────┴─────────────► deliver
                                    │                                   │
                        ┌───────────▼────────────┐          ┌───────────▼────────┐
                        │ 19 escalate  interrupt()│          │ 20 deliver         │
                        └───────────┬────────────┘          └───────────┬────────┘
                                    └──────────────┬────────────────────┘
                                          ┌────────▼────────┐
                                          │ 21 capture_fb   │  interrupt()
                                          └────────┬────────┘
                                          ┌────────▼────────┐
                                          │ 22 log_telemetry│  always
                                          └────────┬────────┘
                                                  END
```

### 12.3 Node specification

| # | Node | Purpose | Input (state) | Output (state) | Tool / method | Failure path |
|---|---|---|---|---|---|---|
| 1 | `resolve_intent` | NL → structured request | `query_text` | `kpi_id, window, requested_dims` | **LLM Haiku 4.5**, structured output | Unparseable / unknown KPI → `clarify` with the list of available KPIs |
| 2 | `load_contract` | Load + validate contract | `kpi_id` | `contract` | Pydantic registry | Missing/invalid contract → hard error (config bug, must be loud) |
| 3 | `enforce_entitlements` | Resolve row/col/source access | `principal, contract` | `access` | Policy engine | No permitted rows → `access_denied` **with an explanation of what was restricted and who to ask** |
| 4 | `gate_quality` | **Gate 1** | `contract, access` | `freshness, quality, metric_series` | SQL + rules | Stale beyond SLA / null rate > threshold / active schema change → `abstain_data` naming the specific failure |
| 5 | `detect` | Is it real? | `metric_series` | `detection` | statsmodels + ruptures | `n < min_history` → sparse-history path (9.4), not an error |
| 6 | `materiality` | Is it worth attention? | `detection, contract` | `materiality` | Business rule | Fail → `no_finding` **showing the rule and the numbers** |
| 7 | `decompose_identity` | Which factor? | `detection, contract.drivers` | `identity_split` | LMDI | Zero/negative factor → skip that term, flag it |
| 8 | `attribute_dimensions` | Which slice? | `metric_series, detection` | `attribution` | Adtributor | No dimension clears `T_EP` → mark `diffuse`, downgrade confidence, continue |
| 9 | `counterfactual_check` | Is it slice-specific? | `attribution` | `counterfactual` | DiD | No valid control → `passed=False` + reason; causal language denied |
| 10 | `retrieve_evidence` | Find corroboration + contradiction | `attribution, access` | `evidence` | BM25 + dense + RRF | Zero results → empty set (a valid, informative outcome) |
| 11 | `rank_hypotheses` | Rank and **freeze** | all analysis | `hypotheses, bundle` | Scoring fn | Fewer than 1 hypothesis → `abstain_evid` |
| 12 | `gate_sufficiency` | **Gate 1b** | `hypotheses, bundle` | routing decision | Rules (12.4) | routes to abstain / clarify / narrate |
| 13 | `narrate` | Draft claims | `bundle, persona, violations?` | `narrative`, `narration_attempts += 1` | **LLM Opus 5**, structured, **no tools** | API error → retry once, then template mode |
| 14 | `verify` | **Gate 2** | `narrative, bundle` | `verification` | Deterministic checks (+ advisory LLM) | Hard violations → loop or template |
| 15 | `template_mode` | Guaranteed-faithful fallback | `bundle` | `narrative` (templated) | f-strings | Cannot fail by construction |
| 16 | `recommend` | Levers → actions | `hypotheses, persona, contract.allowed_levers` | `recommendations` | Catalogue + **LLM phrasing only** | Unknown `lever_id` → drop + log |
| 17 | `calibrate_confidence` | Reliability band | full state | `confidence` | Bucketed calibration table | No history → `LOW` + "uncalibrated" label |
| 18 | `defer_check` | Automate or escalate | `confidence, hypotheses` | `deferral` | Cost rule (14.4) | — |
| 19 | `escalate` | Hand to analyst | `bundle, deferral` | paused run | **`interrupt()`** | Timeout → auto-deliver with an "unreviewed" banner |
| 20 | `deliver` | Emit bundle | all | `InsightBundle` | — | — |
| 21 | `capture_feedback` | Typed outcome | delivered bundle | `feedback` | `interrupt()` | No feedback → recorded as `no_response` (which is itself data) |
| 22 | `log_telemetry` | Persist run | all | telemetry rows | DuckDB | Never blocks delivery |

### 12.4 Conditional routing predicates — all pure functions of deterministic state

```python
def route_sufficiency(s: InsightState) -> str:
    h = s["hypotheses"]
    if not h or h[0].evidence_strength < 0.25:                 return "abstain_evid"
    if len(h) >= 2 and abs(h[0].score - h[1].score) < 0.08 \
       and h[0].cause_bucket != h[1].cause_bucket:             return "clarify"   # genuine ambiguity
    if s["quality"].imputed_fraction > 0.10:                   return "abstain_data"
    return "narrate"

def route_verification(s: InsightState) -> str:
    hard = [v for v in s["verification"].violations if v.severity == "HARD"]
    if not hard:                              return "recommend"
    if s["narration_attempts"] < 2:           return "narrate"      # the cycle
    return "template_mode"
```

**No LLM output ever appears in a routing predicate.** That sentence is worth saying aloud in the pitch — it is the cleanest possible statement of "the model does not control the system."

### 12.5 What LangGraph gives you that you would otherwise build

`SqliteSaver` checkpointing → the **lineage panel** renders directly from checkpoint history. `interrupt()` → escalation and feedback pause and resume without a job queue. Typed state → the telemetry wrapper is written once. Declared edges → the graph diagram in your deck is generated from `graph.get_graph().draw_mermaid()`, so **the picture cannot drift from the code**. That last one is a small thing that judges notice.

---

## PART 13 — TWO-STAGE TRUST AND VERIFICATION

### 13.1 Gate 1 — before generation (nodes 4 and 12)

| Check | Rule | On failure |
|---|---|---|
| **Source freshness** | `lag_hours <= contract.freshness.stale_after_hours` per source | `abstain_data`: *"Refund data is 5 days old (SLA 3 days). Explaining net revenue without it would be misleading."* |
| **Completeness** | `null_rate <= 5%` on grain columns | Abstain, naming the column and rate |
| **Imputation load** | `imputed_fraction <= 10%` of the window | Abstain, naming the imputed dates |
| **Schema stability** | No `schema_change_log` entry touching upstream tables inside the window | **Do not abstain — reclassify.** The schema change becomes hypothesis #1 (`internal_data_schema`). This is Scenario 5. |
| **Grain compatibility** | Requested dims ⊆ contract grain | Degrade to the available grain and state the limit |
| **Evidence sufficiency** | `hypotheses[0].evidence_strength >= 0.25` | `abstain_evid` |
| **Hypothesis separation** | `score[0] − score[1] >= 0.08` when buckets differ | `clarify` — present both, ask a disambiguating question |

**Gate 1's most important property: when it fails, the LLM is never called.** Not called and ignored — never invoked. That is both a cost argument and a safety argument, and you can prove it from the telemetry (`llm_calls = 0` on abstained runs is a line in your telemetry table you should point at during the demo).

### 13.2 Gate 2 — after generation (node 14)

| # | Check | Mechanism | Severity |
|---|---|---|---|
| 1 | **Numeric grounding** | Every number in every claim matches `bundle.metric_facts` within tolerance | HARD |
| 2 | **Driver membership** | Every named driver is a `hypothesis.id` in the bundle | HARD |
| 3 | **Direction consistency** | `claim.direction` matches the computed sign | HARD |
| 4 | **Coverage** | The largest-contribution driver appears in ≥1 claim | HARD |
| 5 | **Citation validity** | Every `evidence_id` exists; every `attribution`/`causal` claim has ≥1 | HARD |
| 6 | **Causal-language licence** | Causal verbs only where `causal_language_licensed == True` | HARD |
| 7 | **Entitlement leakage** | No restricted entity/value appears in the text | HARD |
| 8 | **Persona depth** | Claim count and jargon level within persona bounds | SOFT |
| 9 | **Hedging consistency** | Low confidence ⇒ hedged language present | SOFT |
| 10 | **Advisory LLM judge** | Second Opus 5 call flagging unsupported claims | **ADVISORY — logged, never blocks** |

Checks 1–4 are the arXiv 2608.08126 prescription plus the numeric extension. Check 6 is the correlation/causation discipline made mechanical. Check 10 is advisory *because* CALM showed LLM judging is inconsistent across datasets — you use it as a signal for your eval set, not as a gate.

### 13.3 Failure outcomes — the ladder, in order

1. **Retry once** with typed violations as explicit corrections. (Cap 1.)
2. **Deterministic template** — mechanically rendered from the bundle. Labelled in the UI.
3. **Alternative-hypothesis view** — when Gate 1b said `clarify`: both hypotheses side by side, no synthesis.
4. **Clarification request** — a specific question, not "please rephrase": *"Two explanations are equally supported. Do you want the competitor-promotion view or the stockout view? They imply different owners."*
5. **Analyst escalation** — the evidence packet, pre-assembled, with the specific point of doubt marked.
6. **Full abstention** — *"I can't explain this reliably,"* plus exactly what is missing and what would fix it.

**Never: a fluent answer produced because a fluent answer was expected.** That sentence is your architecture's thesis, and every item on this ladder is a place where the system chooses something less satisfying and more honest.

### 13.4 Confidence — the derivation (this is the "0.82" a judge will ask about)

Two components, and the distinction between them is the whole point.

**(a) Evidence score** — deterministic, from the bundle:

```python
evidence_score = (0.30 * norm(contribution_pct)
                + 0.20 * (1 - p_value)
                + 0.20 * evidence_strength
                + 0.15 * (1.0 if counterfactual.passed else 0.0)
                + 0.10 * data_quality_score
                + 0.05 * (1.0 if temporal_precedence else 0.0))
```

**(b) Calibration** — map that score to an observed accuracy band, not to a percentage:

| Band | `evidence_score` | Historical accuracy | Rendered as |
|---|---|---|---|
| HIGH | ≥ 0.75 | 29 / 34 correct | "High · correct in 29 of 34 similar past cases" |
| MEDIUM | 0.50–0.75 | 18 / 31 correct | "Medium · correct in 18 of 31 similar past cases" |
| LOW | 0.25–0.50 | 6 / 22 correct | "Low · correct in 6 of 22 similar past cases" |
| INSUFFICIENT | < 0.25 | — | Abstain |

**Why bands with base rates rather than "0.82":** the 184-participant study found calibrated confidence lifted decision accuracy ~20% while a miscalibrated or context-free number gave ~2% and increased automation bias; and a bare score can improve trust calibration without improving joint accuracy. A band with its historical hit-rate tells the user *how often this kind of call has been right*, which is the thing they actually need in order to decide whether to check it.

**Where the historical counts come from at demo time:** the ground-truth eval run over your generated dataset. Label the calibration table `seeded from N=87 synthetic labelled cases` in the UI. **Say that it is synthetic.** A judge who catches you implying production history has just destroyed the credibility of the one section that was supposed to be about honesty; a judge who sees you label it yourself concludes the opposite.

---

## PART 14 — RECOMMENDATION ENGINE

### 14.1 The structure the case asks for

`driver → controllable lever → action → expected impact → owner → confidence → monitoring plan`

Only **one** of those seven is LLM-generated.

### 14.2 The lever catalogue (business rules, versioned)

```yaml
# recommendations/levers.yaml
- lever_id: L_GATEWAY_ESCALATE
  applies_to_buckets: [internal_product]
  applies_to_drivers: [conversion_rate, checkout_completion]
  trigger_conditions:
    requires_evidence_types: [deploy_changelog, support_tickets]
    min_evidence_strength: 0.5
    requires_stable_baseline: false
  action_template: "Escalate {component} to Engineering for rollback assessment; request {service} error-rate logs for {window}."
  owner_role: engineering_lead
  decision_rights: {can_approve: [engineering_lead, cto], notify: [ops_lead]}
  impact_model: recover_to_baseline        # deterministic, see 14.3
  monitoring:
    metric: conversion_rate
    check_after_days: 2
    success_threshold: "recovers to >= 90% of pre-event baseline"
  constraints: ["Rollback window closes 14 days after deploy"]

- lever_id: L_PRICING_REVIEW
  applies_to_buckets: [external_competitor]
  trigger_conditions: {requires_stable_baseline: true, min_history_days: 90}   # ← blocks Scenario 4
  owner_role: pricing_manager
  decision_rights: {can_approve: [pricing_manager, finance_director]}
  impact_model: elasticity_estimate
  monitoring: {metric: average_order_value, check_after_days: 14}
```

### 14.3 What is deterministic vs LLM

| Element | Produced by | Mechanism |
|---|---|---|
| **Which levers are eligible** | Deterministic | `bucket` match ∩ `driver` match ∩ trigger conditions ∩ `contract.allowed_levers` ∩ persona decision rights |
| **Expected impact** | **Deterministic — computed, never generated** | `recover_to_baseline` → `abs_effect` already computed by detection. `elasticity_estimate` → historical elasticity from the fact table. Rendered as a **range**, with the method named. |
| **Owner** | Deterministic | `owner_role` → the org table |
| **Decision rights** | Deterministic | From the lever + persona (Priya can *request* a rollback; only `engineering_lead` can approve — the UI says so) |
| **Monitoring plan** | Deterministic | `metric` + `check_after_days` + `success_threshold` from the lever |
| **Confidence** | Deterministic | Inherited from the hypothesis, capped by lever preconditions |
| **The action sentence** | **LLM** | Fills `action_template` slots and adapts register per persona. Nothing else. |

**Hard rule:** a recommendation whose `lever_id` is not in the catalogue is dropped and logged as a `LEVER_HALLUCINATION` telemetry event. Because the field is a schema-constrained enum, this should be near-zero — and the counter being visibly zero on your telemetry tab is a quiet, powerful demonstration.

### 14.4 The deferral rule (Mozannar & Sontag, made concrete)

```python
def should_defer(h: Hypothesis, conf: Confidence, persona: PersonaProfile) -> DeferralDecision:
    p_model = calibration.accuracy_for_band(conf.band)              # e.g. 0.85
    p_human = human_accuracy.for_bucket(h.cause_bucket)             # from feedback history
    cost_error  = persona.decision_value_inr                        # e.g. ₹5,00,000
    review_cost = persona.analyst_hourly_inr * ESTIMATED_REVIEW_HOURS

    loss_model = (1 - p_model) * cost_error
    loss_human = (1 - p_human) * cost_error + review_cost
    return DeferralDecision(
        defer  = loss_model >= loss_human,
        reason = f"E[loss|model]=₹{loss_model:,.0f} vs E[loss|human]+review=₹{loss_human:,.0f}",
        capacity_ok = analyst_queue.depth() < persona.max_queue,
    )
```

The behaviour this produces, and why it is better than a threshold: on `internal_data_schema` hypotheses, `p_human` is high (an analyst spots a rename instantly) so the system defers **even at high model confidence**. On `external_market` hypotheses, `p_human` is low (the analyst has no more information than the system does) so it delivers **even at medium confidence**. A confidence threshold cannot express either behaviour. Demonstrate exactly this contrast in the pitch — it is the most sophisticated single idea in your design and it takes 20 seconds to show.

---

## PART 15 — THE FEEDBACK LOOP

"The model learns" is the answer the Round 2 case is filtering out. Here is the specific version.

### 15.1 Five outcomes → five named artifacts

| Outcome | Captured | Artifact updated | Update mechanism | Visible effect |
|---|---|---|---|---|
| **Accepted** | 1 click | `calibration_events` | +1 to (band, correct) counter; recompute band accuracy | The reliability text on the confidence chip changes |
| **Rejected — wrong driver** | click + pick the correct driver | `eval/attribution_labels.jsonl` **and** `config/scoring.yaml` | Labelled example added. Scoring weights refit by constrained logistic regression **only when N ≥ 30**; the diff is version-controlled and requires human merge | Hypothesis ordering changes on future similar cases |
| **Corrected — narrative wrong** | inline edit of the claim | `eval/narrative_corrections.jsonl` + `prompts/narrate.md` | Correction becomes a regression-test case. Prompt edits are **human-authored** from recurring patterns, never auto-applied | Fewer Gate 2 violations of that type |
| **Escalated** | routed to analyst | `human_accuracy` table + `deferral_stats` | Analyst's verdict updates `p_human` for that `cause_bucket` | The deferral rule's routing shifts for that bucket |
| **Insufficient evidence** | click + "what was missing" | `coverage_gaps` register + per-KPI thresholds | Missing source logged; if a source is named 5+ times it is promoted to a roadmap item | Gate 1 abstains earlier and more specifically |

### 15.2 What feedback explicitly does NOT do

- **No LLM fine-tuning.** Not in Round 2, not on 87 examples. Say so plainly — it is a credibility gain, not a gap.
- **No auto-applied prompt changes.** Corrections become regression tests; a human writes the prompt edit.
- **No unbounded weight drift.** Weights are refit only at N ≥ 30, only within bounds, only via a reviewed PR.
- **No retrieval index rebuild per feedback item.** Relevance labels accumulate; the RRF `k` and fusion weights are re-tuned on the labelled set in a batch job, not online.

### 15.3 Learning that is genuinely online

Two things update on every single feedback event, because both are simple counters:

1. **Calibration counters.** `(band, correct)` — this is what makes the confidence display honest over time and it needs no model at all.
2. **`p_human` per cause bucket** — which directly changes deferral routing.

Everything else is batched and reviewed. **This distinction — what updates live vs what updates on review — is exactly the specificity the case is testing for**, and it is a better answer than a more ambitious one you cannot defend.

---

## PART 16 — UX RESEARCH: GROWTH.DESIGN

**Source access note, stated honestly.** As of 2026-08-21 the individual Growth.Design case studies sit behind a waiting-list gate (registrations open 2026-08-24). I was able to extract two things: the **Coronavirus Dashboard UX** case study in full — which is the single most relevant one to this problem and the one you flagged — and the complete **Psychology of Design** principle taxonomy, which is the mechanism library underneath every case study on the site. The mapping below is built from those verified sources. Where I extend beyond what I could read, it is marked *[extension]*.

### 16.1 Coronavirus Dashboard UX — the closest analogue that exists

This is a dashboard that showed accurate numbers and still misled millions of people. That is *exactly* your failure mode: a system that is right and still produces a wrong decision.

| # | Mechanism it exposed | What the dashboard did | Why it misled | Transfer to BusinessIntelligence.ai | Concrete UI decision |
|---|---|---|---|---|---|
| 1 | **Availability heuristic** | Foregrounded the latest, most alarming numbers | Recent information takes precedence over base rates; recency reads as importance | A leader who sees only the flagged anomaly will over-weight it against the business's normal volatility | **Every anomaly renders against its own normal band.** The headline chart always shows the STL baseline and the historical residual range behind the actual line — the deviation is shown *in context*, never alone. |
| 2 | **Confirmation bias** | Alarming visuals confirmed pre-existing fear; contradicting data was ignored | People look for evidence that confirms what they already think | A regional lead who already blames the gateway will read the evidence panel as confirmation and stop | **Contradicting evidence is a peer panel, not a footnote** — same width, same weight, adjacent to supporting evidence. It is the field made mandatory in Part 10.4. |
| 3 | **Proportion distortion / denominator neglect** | Symbol maps rendered all of China "infected" at 0.005% prevalence | Visual area was read as magnitude | A red-highlighted region on a map is read as "the whole region collapsed" | **No choropleth or symbol map in the anomaly view.** Contribution is rendered as a waterfall with explicit denominators: "West = ₹34.1L of ₹38.2L (89%)". Share and absolute value are always shown together. |
| 4 | **Negativity bias** | Cumulative counts amplified the negative; recoveries were invisible | Unpleasant data is recalled more strongly | Showing only the drop makes every insight feel like a crisis and burns out the user | **Always render the counterfactual and the recovery path.** "Without this event, revenue would have tracked ₹X" and, where relevant, "the same slice recovered within 6 days after the April incident." |
| 5 | **Colour psychology** | Red read as a death sentence | Colour carries semantic weight beyond the data | Red-on-everything trains users to ignore red | **Colour is reserved for materiality, not for direction.** Amber = material and explained; red = material and *unexplained or escalated*; grey = detected, immaterial. A drop that the system understands well is not red. |
| 6 | **Missing context: no error margins** | Numbers were presented as absolute fact, not "known cases" | Users could not judge how much to trust a figure | Any number without its uncertainty invites over-trust — the automation-bias finding | **Every number carries its provenance chip**: source, as-of timestamp, method. Confidence never appears as a bare figure (Part 13.4). |
| 7 | **Qualifying language** | Recommended prefixing with "We know of…" | Framing the epistemic status of a number changes how it is used | Same move, verbatim: your system reports what it *observed*, not what *is* | **Claim-type-conditioned verbs**, enforced by Gate 2 check 6: `observation` → "fell by"; `attribution` → "is concentrated in"; `causal` → "caused" **only when licensed**. |

**This one case study justifies seven concrete UI decisions.** In the pitch, use it as your UX credibility anchor: *"the most-viewed dashboard in history had accurate data and still produced bad decisions; here are the seven things we changed because of it."*

### 16.2 Psychology of Design principles → UI decisions

From Growth.Design's own taxonomy ([growth.design/psychology](https://growth.design/psychology)):

| Principle (their wording) | Why it works | Transfer | UI decision |
|---|---|---|---|
| **Framing** — "the way information is presented affects how users make decisions" | Identical data, opposite choices | "Conversion fell 12%" and "88% of checkouts still completed" are the same fact | **Persona-conditioned framing is an explicit, labelled system behaviour.** Ops sees operational framing, Finance sees ₹ framing — and the UI shows *"framed for: Regional Ops Lead"* so framing is disclosed, not hidden. This turns a manipulation risk into a transparency feature. |
| **Anchoring bias** — "users rely heavily on the first piece of information they see" | The first number sets the reference | Whatever number you show first becomes the mental baseline | **The first number on screen is always the materiality-gated business effect** (₹38.2L), never a statistical artifact (p-value, z-score). Statistics live one layer down. |
| **Hick's Law** — "more options leads to harder decisions" | Choice time scales with options | Twelve ranked hypotheses is not more rigorous, it is unusable | **Hard cap: 3 hypotheses, 3 recommendations, 5 evidence items per hypothesis.** The rest is behind "show all considered." The cap is a product decision, and AgentRCA's Top-2 result is its justification. |
| **Progressive disclosure** — "delaying complex features reduces overwhelm" | Staged revelation reduces load | Your output has five natural depth layers | **Four fixed layers** (16.3). Layer 1 must be readable in 5 seconds. |
| **Cognitive load** | Working memory is the binding constraint | Analytical UIs fail by density, not by lacking features | One primary chart per screen; tabular detail on demand; no more than four numbers above the fold. |
| **Chunking** — "people remember grouped information better" | Grouped items survive recall | Evidence is currently a flat list | **Evidence grouped by source type** with a count badge: "Support tickets (34) · Deploy log (1) · Market events (0)". The zero is informative and must be rendered. |
| **Mental model** — "preconceived assumptions about how things work" | Violated expectations feel like bugs | Users arrive with a dashboard mental model: filters → charts → export | **Do not invent a novel interaction paradigm.** Left rail = KPI/date/persona (dashboard-shaped). The novelty is the *content* of the right panel, not the navigation. |
| **Labor illusion** — "visible effort increases perceived value" | Visible work raises perceived quality and trust | Your pipeline does 9 real analytical steps in ~8 s and users would otherwise see a spinner | **Render the pipeline as a live step ledger** — "STL decomposition ✓ 0.3s · PELT changepoint ✓ 0.6s · Adtributor across 4 dimensions ✓ 1.1s · Retrieved 47 documents ✓ 2.4s · Verified 6 claims ✓ 1.2s". This is simultaneously the labor illusion, the "clear breakdown of LLM vs non-LLM processing" the case demands, and your telemetry. **One component, three requirements.** |
| **Peak-End Rule** — "people judge an experience by its peak and how it ends" | Peak and ending dominate memory | Your session ends on the recommendation | **End on a committed action**, not a chart: an owner, a date, a monitoring check. The last thing on screen is "Monitoring: conversion_rate, check 2026-08-23." |
| **Reactance** — "resistance when behavior feels forced" | Directives get rejected | A confident directive to a senior leader triggers pushback | **Recommendations are phrased as interrogable options with visible reasoning and a one-click "why this?"** — never as an instruction. This is your existing "evidence packet, not a verdict" principle, sourced. |
| **Default bias** — "resistance to changing established behaviors" | Defaults win | Nobody adopts a tool needing a second login | Roadmap: embed in the existing BI surface. Reinforces the Copilot "wrong job" finding (D8). |
| **Zeigarnik effect** — "it's hard to leave things incomplete" | Open loops pull attention | Escalations and unreviewed insights are open loops | **A persistent "3 awaiting your review" badge** on the analyst persona. Uses the effect for the one thing that genuinely should not be dropped. |

### 16.3 The four disclosure layers *[extension]*

| Layer | Content | Reading time | Who stops here |
|---|---|---|---|
| **L1 — Verdict** | Headline + ₹ effect + confidence band + one-line cause | 5 s | A leader scanning between meetings |
| **L2 — Structure** | Waterfall (LMDI) + top 3 hypotheses + evidence counts by source | 30 s | A leader deciding whether to act |
| **L3 — Evidence** | Individual documents with excerpts, dates, retrieval scores; contradicting panel | 3 min | A leader challenging the finding |
| **L4 — Method** | STL/PELT parameters, Adtributor EP + surprise per dimension, DiD control slice, gate results, compiled SQL, prompt + raw model output | 15 min | The analyst, the data team, **and the judge** |

**Layer 4 is where you win the technical points.** Most prototypes have no layer 4 at all. Build it as a tab, not a hidden debug mode, and open it during the pitch.

---

## PART 17 — UX REQUIREMENT → BACKEND CAPABILITY → COMPONENT

| # | UX requirement (the user's question) | Backend capability | Implementation component | Layer |
|---|---|---|---|---|
| 1 | "What changed?" | Detection + materiality | `detection/engine.py` → `DetectionResult` | L2 |
| 2 | "Is it noise?" | STL + robust z + PELT + p-value | `detection/decompose.py`, `detection/changepoint.py` | L2 |
| 3 | "Does it matter commercially?" | Materiality rule from contract | `semantic/contract.py::MaterialityRule` | L1+L2 |
| 4 | "Which part of the business?" | LMDI + Adtributor | `attribution/lmdi.py`, `attribution/adtributor.py` | L3 |
| 5 | "Why did it happen?" | Hypothesis ranking + evidence linking | `attribution/hypotheses.py` | L5 |
| 6 | "What's the evidence?" | Hybrid retrieval + structured joins | `evidence/retrieve.py`, `evidence/structured.py` | L4 |
| 7 | "How sure are you?" | Evidence score → calibration band + base rate | `trust/confidence.py`, `trust/calibration.py` | L8 |
| 8 | "What else could it be?" | Ranked hypotheses + contradicting evidence | `attribution/hypotheses.py` (mandatory field) | L5 |
| 9 | "Could this be a data problem?" | Schema-diff + freshness gate | `semantic/freshness.py`, `evidence/schema_diff.py` | G1 |
| 10 | "Why did you say nothing?" | Materiality verdict with numbers | `NoFindingCard` renders the rule that did not fire | L2 |
| 11 | "Why did you abstain?" | Gate 1 typed failure reasons | `trust/gates.py` → `AbstentionCard` | G1 |
| 12 | "Prove the words match the numbers" | Gate 2 verification report | `trust/verify.py` → `VerificationBadge` | G2 |
| 13 | "What should I do?" | Lever catalogue + computed impact | `recommend/levers.py`, `recommend/impact.py` | L7 |
| 14 | "Who owns it? Can I approve it?" | `owner_role` + decision rights + persona | `recommend/decision_rights.py` | L7 |
| 15 | "Show me a different persona's view" | Persona profile + entitlements | `security/entitlements.py`, `llm/persona.py` | L1+L6 |
| 16 | "Why can't I see that source?" | Source allowlist + audit | `security/entitlements.py` → `WithheldEvidenceNotice` | L1 |
| 17 | "Where did this number come from?" | LineageRecord incl. compiled SQL | `semantic/gateway.py` → `LineagePanel` | L1 |
| 18 | "What did the AI actually do?" | Per-node LLM/non-LLM tagging | `telemetry/tracer.py` → `PipelineLedger` | L10 |
| 19 | "What did this cost?" | Token + cost accounting per call | `telemetry/cost.py` → `TelemetryTab` | L10 |
| 20 | "I disagree" | Five typed feedback outcomes | `feedback/capture.py` → `FeedbackDialog` | L9 |
| 21 | "Get me a human" | `interrupt()` + evidence packet | graph node 19 → `EscalationDialog` | L9 |
| 22 | "Is the model even reliable here?" | Calibration table + reliability history | `trust/calibration.py` → `ConfidenceChip` | L8 |

**Every row has a component. No row is satisfied by prompt wording.** That table is worth putting in the appendix of your deck verbatim — it is the clearest possible evidence that the UX and the architecture were designed together rather than one being decoration on the other.

---

## PART 18 — THE STREAMLIT PROTOTYPE

### 18.1 Principles

1. **Not a chatbot.** There is a query box, but it resolves to a structured request and renders a workspace. No conversation transcript.
2. **One run, one screen.** Analysis executes once; every interaction renders from the frozen `InsightBundle`.
3. **Four disclosure layers**, always in the same positions, so the layout itself becomes learnable.
4. **The system's uncertainty is a first-class visual**, never a caveat in small grey text.
5. **Every state is designed** — abstention, low confidence, sparse history and access-restricted are screens, not error toasts. Those four screens are where the case's requirements live.

### 18.2 Main workspace (Layer 1 + 2)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ BusinessIntelligence.ai            [Persona: Priya Nair · Regional Ops Lead (West) ▾] │
├────────────────┬─────────────────────────────────────────────────────────────────────┤
│ KPI            │  ⚠ MATERIAL MOVEMENT DETECTED                    ⟳ Explain this      │
│ ● Net Revenue  │                                                                      │
│ ○ Orders       │  Net Revenue · West · 12–24 Jul 2026                                 │
│ ○ AOV          │  ┌──────────────────────────────────────────────────────────────┐   │
│ ○ Conversion   │  │  ₹ 38.2L  below expected            −11.4% vs baseline        │   │
│ ○ Refund Rate  │  │  ▸ Sustained level shift from 12 Jul (PELT, p = 0.003)        │   │
│                │  │  ▸ Materiality: PASSED — ₹38.2L ≥ ₹2.5L floor, 13 d ≥ 3 d     │   │
│ Window         │  │  ▸ Confidence: ● HIGH — correct in 29 of 34 similar cases      │   │
│ [1–31 Jul ▾]   │  └──────────────────────────────────────────────────────────────┘   │
│                │                                                                      │
│ ─────────────  │  ┌── WHAT MOVED ──────────────────────────────────────────────┐     │
│ PIPELINE       │  │   actual ── · baseline ┄┄ · residual band ▒                 │     │
│ ✓ Contract     │  │        ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄                    │     │
│ ✓ Access       │  │   ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒                   │     │
│ ✓ Quality 0.3s │  │   ────────────────────╮ │                                    │     │
│ ✓ STL    0.4s  │  │                       ╰──────────────                        │     │
│ ✓ PELT   0.6s  │  │                    12 Jul ↑ changepoint                      │     │
│ ✓ LMDI   0.1s  │  └────────────────────────────────────────────────────────────┘     │
│ ✓ Adtributor   │                                                                      │
│   1.1s (4 dims)│  ┌── WHICH FACTOR (LMDI, residual-free) ──────────────────────┐     │
│ ✓ DiD    0.2s  │  │  Conversion  ████████████████████  −₹34.1L   89%           │     │
│ ✓ Retrieval    │  │  AOV         ██                    −₹ 2.6L    7%           │     │
│   2.4s (47 doc)│  │  Sessions    █                     −₹ 1.5L    4%           │     │
│ ✓ Narrate LLM  │  │  Refunds     ·                      ₹ 0.0L    0%           │     │
│   1.9s         │  │  ─────────────────────────────────────────────             │     │
│ ✓ Verify 6/6   │  │  Total                             −₹38.2L  100%  ✓ exact  │     │
│                │  └────────────────────────────────────────────────────────────┘     │
│ 🟦 non-LLM 6.1s│                                                                      │
│ 🟪 LLM     1.9s│  ┌── WHERE (Adtributor: EP + surprise) ───────────────────────┐     │
│ 3 calls · $0.04│  │  channel   Web + Mobile App   EP 91%  surprise 0.34  ★ won │     │
│                │  │  region    West               EP 96%  surprise 0.04        │     │
│ ─────────────  │  │  segment   diffuse            EP 61%  surprise 0.02        │     │
│ ⓘ Method (L4)  │  │  category  diffuse            EP 48%  surprise 0.01        │     │
│                │  │  ⓘ West has the highest EP but almost no surprise — it is  │     │
│                │  │    simply the largest region. Channel shifted share.        │     │
│                │  └────────────────────────────────────────────────────────────┘     │
└────────────────┴─────────────────────────────────────────────────────────────────────┘
```

That "West has the highest EP but almost no surprise" callout is the Adtributor paper's own insight rendered live. It is the single most persuasive square inch of your UI.

### 18.3 Explanation + evidence (Layer 2 + 3)

```
┌── EXPLANATION ────────────────────────────────── framed for: Regional Ops Lead ──────┐
│  Checkout conversion on Web and Mobile App in West fell from 3.4% to 2.1% starting   │
│  12 July. The drop is concentrated in these two channels; Marketplace and Retail      │
│  Partner were unaffected over the same period.                                        │
│                                                                                       │
│  ✓ VERIFIED  6 of 6 claims grounded · 8 numbers matched · 0 unsupported claims        │
│              causal language: LICENSED (control slice held, DiD = −1.26pp, p = 0.004) │
│                                                                                       │
│  ┌ HYPOTHESIS 1 ─────────────────────────────────── contribution 89% · ● HIGH ──────┐│
│  │ Payment gateway degradation on Web + Mobile App                                   ││
│  │ Bucket: internal_product     Temporal precedence: ✓   Counterfactual: ✓ PASSED    ││
│  │                                                                                   ││
│  │ SUPPORTING (3 sources)              │ CONTRADICTING (1)                           ││
│  │ ▸ 34 payment-failure tickets, 29    │ ▸ Marketplace channel uses the same         ││
│  │   accounts, 12–18 Jul (5.7× median) │   gateway and was unaffected — suggests     ││
│  │   [bm25 0.71 · dense 0.83 · rrf #1] │   a client-side rather than gateway fault   ││
│  │ ▸ Deploy PG-2026-07-12 "checkout    │   [exact join · deterministic]              ││
│  │   SDK v4.2" · risk: high · 11 Jul   │                                             ││
│  │   [exact join · deterministic]      │                                             ││
│  │ ▸ 0 market events in window         │                                             ││
│  │                                     │                                             ││
│  │ [ Show all 47 retrieved documents ]              [ Why this ranks first? ]        ││
│  └───────────────────────────────────────────────────────────────────────────────────┘│
│  ┌ HYPOTHESIS 2 ────────────────────────────── contribution 6% · ○ LOW ─────────────┐│
│  │ Seasonal softness in Apparel   [ expand ]                                         ││
│  └───────────────────────────────────────────────────────────────────────────────────┘│
│  ⓘ 2 evidence items withheld — source `crm_notes` not permitted for role `ops_lead`.  │
│    Contact: VP Revenue Operations.                                        [ Why? ]    │
└───────────────────────────────────────────────────────────────────────────────────────┘

┌── RECOMMENDED ACTION ────────────────────────────────────────────────────────────────┐
│  1 · Escalate checkout SDK v4.2 to Engineering for rollback assessment                │
│      Lever      L_GATEWAY_ESCALATE                                                    │
│      Impact     recovers ₹28L–₹34L/mo if conversion returns to baseline               │
│                 (computed from detected effect; not a forecast)                       │
│      Owner      Engineering Lead · you can REQUEST, approval sits with Eng Lead       │
│      Monitor    conversion_rate · check 2026-08-23 · success ≥ 90% of pre-baseline    │
│      Constraint Rollback window closes 25 Jul (14 d after deploy)                      │
│      [ Request rollback ]  [ Why this lever? ]  [ Show 2 other eligible levers ]      │
│                                                                                       │
│  ✓ Handled automatically — E[loss|model] ₹75,000 < E[loss|human] + review ₹1,12,000   │
│    [ Escalate to analyst anyway ]                                                     │
│                                                                                       │
│  Was this right?   [ ✓ Accepted ]  [ ✗ Wrong driver ]  [ ✎ Correct it ]               │
│                    [ ↑ Escalate ]  [ ? Not enough evidence ]                          │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

### 18.4 The four non-happy states — where the case's requirements actually live

**A · Abstention (Gate 1 failure)**
```
┌── NOT ENOUGH RELIABLE DATA TO EXPLAIN THIS ──────────────────────────────────────────┐
│  A −9.1% movement was detected in Net Revenue · South · 1–14 Aug and it clears the    │
│  materiality bar. We are not explaining it, for one specific reason:                   │
│                                                                                        │
│    ✗ Refund data (S3 finance) last updated 2026-08-14 — 5 days old, SLA is 3 days.    │
│      Net Revenue is defined net of returns, so the recent figures are incomplete.      │
│    ✓ Warehouse fresh (6h) · ✓ Product analytics fresh (2h) · ✓ No schema changes      │
│                                                                                        │
│  What would change this: the Monday finance load, expected 2026-08-19 06:00.          │
│  ⓘ No LLM call was made for this insight. Cost: $0.0012 (intent resolution only).     │
│  [ Notify me when data lands ]   [ Explain on stale data anyway (marked unreliable) ] │
└───────────────────────────────────────────────────────────────────────────────────────┘
```
That `$0.0012` line makes the architecture visible in a way no diagram can: the system **spent nothing** because it stopped before the expensive part.

**B · Genuine ambiguity (Gate 1b → clarify)**
```
┌── TWO EXPLANATIONS ARE EQUALLY SUPPORTED ────────────────────────────────────────────┐
│  Net Revenue · South × Apparel · −₹21.4L (−7.8%) from 2 June                          │
│  We are not choosing between these. They imply different owners and different actions.│
│                                                                                        │
│  A · Competitor promotion            0.61  │  B · Stockout in top 3 SKUs        0.58   │
│    6 market events (competitor −20%) │    11 CRM notes: "out of stock"                 │
│    AOV fell, volume held             │    Volume fell, AOV held                        │
│    ✗ but rivals' promo ended 8 Jun,  │    ✗ but inventory system shows stock           │
│      revenue did not recover         │      restored 6 Jun; revenue did not recover    │
│    Owner: Pricing Manager            │    Owner: Supply Chain Lead                     │
│                                                                                        │
│  Δscore = 0.03 (below the 0.08 separation floor) → the engine will not pick.          │
│  [ Investigate A ]  [ Investigate B ]  [ Send both to analyst with evidence packet ]  │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

**C · Sparse history**
```
┌── LIMITED HISTORY — INTERPRET WITH CARE ─────────────────────────────────────────────┐
│  NewLaunch category · 23 days of history · 56 required for seasonal detection         │
│  Method: peer_cohort_baseline (not STL/PELT — there is not enough data for either)    │
│                                                                                        │
│  Revenue is tracking ₹4.1L–₹7.8L below comparable launches at day 23                  │
│  (range from 6 prior launches, not a point estimate)                                   │
│  Confidence: ● LOW — capped by rule, and cannot be raised by strong evidence           │
│                                                                                        │
│  ⚠ 2 recommendations were suppressed: L_PRICING_REVIEW and L_PROMO_RESPONSE require    │
│    ≥90 days of stable baseline. Acting on 23 days would not be defensible.             │
│  Reliable seasonal detection available from ~2026-09-14.                               │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

**D · Access restriction** — inline, as shown in 18.3, plus an audit entry: `2026-08-21 14:32 · priya.nair · ops_lead · evidence_retrieval · crm_notes · DENIED · policy SRC-003 · 2 items withheld`.

### 18.5 Method tab (Layer 4) — the judge's tab

Five sections: **Detection** (STL params, residual plot, PELT penalty, p-value), **Attribution** (full EP × surprise matrix for all four dimensions, DiD control slice and estimate), **Retrieval** (all 47 candidates with BM25/dense/RRF scores and the filters applied), **Generation** (exact prompt, raw model JSON, all 10 verification checks with pass/fail), **Lineage** (compiled SQL per metric, source watermarks, contract versions, entitlement predicates applied).

### 18.6 Telemetry tab

Per run: wall-clock, per-node latency bars, **LLM vs non-LLM time split**, model calls with input/cached/output tokens and cost, retrieval latency, gate outcomes, verification violations by type. Aggregate: p50/p95 latency, mean cost per insight, abstention rate, verification failure rate, deferral rate, cumulative spend.

### 18.7 Implementation notes

Persona switch reruns the graph from node 3 (re-entitle → re-narrate) but **reuses the cached detection and attribution** — because the movement is a fact about the business, not about the viewer. Only entitlement-filtered evidence and the narrative change. That is both faster and philosophically correct, and it is worth saying so when you demo the persona toggle.

Use `st.fragment` for the evidence panel and telemetry so expanding a document does not re-run anything. Cache the DuckDB connection and the embedding model with `@st.cache_resource`. Store one `InsightBundle` in `st.session_state`. Plotly for the waterfall and the time series; Streamlit natives everywhere else.

---

## PART 19 — DEMO SCENARIOS

Each maps to an injected ground-truth event (7.5), so you can state accuracy rather than assert capability.

### Scenario 1 — High-confidence, multi-factor movement (E1)
**Input:** Priya asks "why did revenue drop in West?" · **Processing:** all gates pass → LMDI isolates conversion (89%) → Adtributor picks `channel {Web, Mobile App}` on surprise despite West having higher EP → DiD passes (Marketplace held) → 34 tickets + 1 deploy retrieved → HIGH → auto-delivered.
**Output:** full workspace, verified narrative, `L_GATEWAY_ESCALATE`. **UI:** happy path.
**Why it matters:** proves the pipeline end-to-end *and* demonstrates the EP-vs-surprise distinction live. **This is your opening scenario.**

### Scenario 2 — Conflicting evidence (E2)
**Input:** Arjun asks about South Apparel · **Processing:** two hypotheses at 0.61 / 0.58, different buckets, Δ = 0.03 < 0.08 → `clarify`. **Neither narrative is generated.**
**Output:** side-by-side with support *and* contradiction for each. **UI:** state B.
**Why it matters:** most systems would pick one and write it confidently. Showing the system declining to choose — and naming the numeric rule that stopped it — is the strongest possible answer to the case's "contradictory evidence" requirement.

### Scenario 3 — Low confidence / abstention (E3)
**Input:** Priya asks about East SMB · **Processing:** material movement, but `evidence_strength = 0.18 < 0.25` → `abstain_evid`. Zero LLM narration calls.
**Output:** abstention card naming what is missing. **UI:** state A.
**Why it matters:** AbstentionBench found reasoning models abstain 24% *worse*; your abstention is a graph edge on a deterministic predicate, so it does not depend on the model's willingness at all. Say that sentence during this scenario.

### Scenario 4 — Sparse history (E4)
**Input:** Arjun asks about NewLaunch · **Processing:** coverage gate → peer-cohort baseline; confidence capped LOW; two levers suppressed by `requires_stable_baseline`.
**Output:** range not point estimate, explicit method, suppressed-recommendation notice. **UI:** state C.
**Why it matters:** the requirement most teams will fake by showing a normal chart with a "limited data" caption. Yours takes a **different code path with a different method and different recommendations.**

### Scenario 5 — Two personas, one event (E6)
**Input:** same E1 insight, toggle Priya → Arjun.
**Processing:** detection and attribution cached and identical (the fact does not change); entitlements re-run → Arjun sees `crm_notes` and `margin`; narrative re-generated for the finance persona; lever set re-filtered by decision rights.
**Output:** Priya — "conversion on Web/Mobile fell from 3.4% to 2.1%; escalate SDK v4.2 rollback; Eng Lead approves." Arjun — "₹38.2L revenue at risk, ₹14.1L gross margin, 0.9% of quarter; two enterprise accounts flagged churn risk in CRM notes; approve rollback and brief the board."
**UI:** side-by-side comparison view built for the demo.
**Why it matters:** persona-specific narrative from *identical* computed facts is the case's requirement #4, and the shared attribution proves the personalisation is in the framing, not in the numbers. Show the identical `bundle_hash` on both sides — that is the proof.

### Scenario 6 — Access restriction (E6, Priya's side)
**Input:** Priya asks about the same event, then tries to query North.
**Processing:** (a) `crm_notes` filtered out pre-retrieval → withheld notice + audit row; (b) North query → `access_denied` before any data read.
**Output:** withheld-evidence notice; access-denied card naming the policy and the owner to ask.
**Why it matters:** proves entitlements are enforced **before** the model sees data, not masked afterwards. Open the audit table during this scenario — it is 10 seconds and it settles the question.

### Scenario 7 (bonus) — Schema change masquerading as a business event (E5)
**Input:** anyone asks about the Marketplace channel collapse on 14 June.
**Processing:** Gate 1 finds a `schema_change_log` entry (`channel` value renamed) inside the window → **reclassifies rather than abstaining** → hypothesis #1 becomes `internal_data_schema` with the change record as evidence; the 12 coincidental tickets rank second and are shown as such.
**Output:** *"This is not a business movement. On 14 June the `channel` value 'marketplace' was renamed 'Marketplace' by `sales-ops-etl`, splitting the series. Owner: data-platform. No commercial action required."*
**Why it matters:** this is the differentiator nobody else will have, it comes straight from your own verified practitioner research (§9.4), and it is the most memorable 20 seconds available to you. **If you only have time for four scenarios, keep this one.**

---

## PART 20 — TELEMETRY AND EVALUATION

### 20.1 What is recorded on every run

```python
class RunTelemetry(BaseModel):
    run_id: str; timestamp: datetime; kpi_id: str; persona_id: str
    query_text: str; outcome: str                      # delivered|template|abstained|clarify|no_finding|access_denied
    latency_total_ms: int
    latency_by_node: dict[str, int]
    latency_llm_ms: int; latency_nonllm_ms: int        # the LLM vs non-LLM split, quantified
    llm_calls: list[LLMCall]                           # model, purpose, in/cached/out tokens, cost, ms
    cost_total_usd: float
    retrieval: RetrievalTelemetry                      # candidates, filtered, returned, ms, mean rrf
    gate1_result: str; gate1_failures: list[str]
    gate2_violations: list[tuple[str, str]]            # (check, severity)
    narration_attempts: int
    confidence_band: str; evidence_score: float
    deferral: bool; deferral_reason: str
    bundle_hash: str; contract_versions: dict[str, str]
    feedback: str | None
```

### 20.2 The metrics that matter — and the ones that do not

**Detection quality** (measurable because you injected the events):
- `detection_precision` = flagged events that are real / all flagged. **Target ≥ 0.85.**
- `detection_recall` = real events flagged / all injected. **Target ≥ 0.90** (asymmetric — a missed material movement is worse than a false alarm you filter).
- `false_positive_rate_pre_materiality` vs `post_materiality` — **report both.** The delta is the quantified value of the materiality gate and it is one of the best numbers in your deck.

**Attribution quality:**
- `attribution_top1_accuracy` and `attribution_top2_accuracy` against ground truth. Report both explicitly; the AgentRCA precedent (40.0% → 61.5%) is why the Top-2 number justifies the 3-hypothesis UI.
- `dimension_selection_accuracy` — did Adtributor pick the right dimension? **Run this with surprise disabled as an ablation** and report both. If your numbers echo the paper's 95%-vs-20% gap, that ablation is worth a slide of its own.

**Evidence quality** (20 labelled pairs, Part 11.6):
- `precision@5`, `recall@10`, `MRR`, reported for BM25 / dense / RRF separately.

**Narrative faithfulness** — and note this is *better* than a RAGAS-style score because it is deterministic:
- `verification_pass_rate` (first attempt) — **target ≥ 0.90.**
- `claim_grounding_rate` = verified claims / total claims — **this is faithfulness, computed exactly rather than judged.**
- `violations_by_type` — which of the 10 checks fires most. If `UNGROUNDED_NUMBER` dominates, the prompt needs the fact table restated; if `CAUSAL_UNLICENSED` dominates, the persona prompt is too assertive. **This is a debugging tool, not just a metric.**
- `template_fallback_rate` — **target ≤ 0.05.**

**Abstention quality** (the selective-prediction frame):
- `coverage` = runs delivered / runs attempted.
- `selective_risk` = error rate on delivered runs.
- `abstention_precision` = abstentions where the ground truth really was ambiguous or the data really was bad.
- Plot the **risk-coverage curve.** A judge who knows the field will recognise it immediately, and it is the correct picture for "communicates uncertainty and abstains."

**Deferral quality:**
- `deferral_rate`, `deferral_precision` (deferred cases where the analyst changed the answer — a deferral the analyst rubber-stamps was wasted), `analyst_queue_depth`.

**Economics:**
- `cost_per_insight` (mean, p95), `tokens_per_insight`, `cache_hit_rate` (target ≥ 0.6 on the stable prefix), `cost_per_delivered_insight` **and** `cost_per_abstained_insight` — the second is near-zero, which is the point.
- `latency_p50`, `latency_p95`, and the **LLM vs non-LLM split** (expect roughly 75% / 25% non-LLM / LLM — a useful, surprising number).

### 20.3 Vanity metrics to refuse

| Do not measure | Why |
|---|---|
| Insights generated per day | Rewards volume; your whole design argues for fewer, better, gated insights |
| Total tokens consumed | An input, not an outcome — and framing it as scale rewards the wrong thing |
| "User satisfaction" on a demo dataset | n≈3, no variance, no meaning |
| Model benchmark scores | Not measured on your task; the in-domain eval replaces this |
| Time saved vs analyst (asserted) | Only defensible as a *measured* comparison. If you cannot measure it, present it as an assumption with its arithmetic shown. |
| Number of data sources connected | Architecture theatre — the exact thing this document argues against |

### 20.4 The eval harness

`eval/run_suite.py` executes all 7 scenarios plus 80 generated cases against ground truth and emits `eval/report.md` with every metric above. **Run it in CI.** Then put the report itself in your appendix — a competition prototype that ships a measured evaluation report is in a different category from one that ships a demo.

---

## PART 21 — SECURITY (lightweight, but real)

### 21.1 What to build and what to explicitly skip

| Build | Skip (and say you skipped it) |
|---|---|
| Role-based row filters | Real IdP / SSO / OAuth |
| Column-level masking | Token lifecycle, refresh, revocation |
| Source-level allowlists | Encryption at rest, KMS |
| Append-only audit log | Compliance certification |
| Policy-as-config (YAML) | Multi-tenant isolation |
| Single enforcement chokepoint | Network policy, secrets management |

**How to frame the gap:** *"We built the enforcement model, not the identity infrastructure. Swapping a simulated principal for an OIDC claim is a 20-line change at one chokepoint — which is the point of having exactly one chokepoint."* That is a much stronger answer than pretending the auth is real.

### 21.2 Policy as configuration

```yaml
# security/policy.yaml
roles:
  ops_lead:
    row_filters:      {net_revenue: "region = :user_region", orders: "region = :user_region"}
    denied_columns:   [margin, refund_reason_detail, customer_email]
    allowed_sources:  [S1, S2, support_tickets, deploy_changelog]
    denied_sources:   [crm_notes]
    max_grain:        [date, region, segment, product_category, channel]
  finance_director:
    row_filters:      {}
    denied_columns:   [customer_email]
    allowed_sources:  [S1, S2, S3, support_tickets, crm_notes, market_events, deploy_changelog]
  analytics_lead:
    row_filters:      {}
    denied_columns:   [customer_email]
    allowed_sources:  ["*"]
    extra_capabilities: [view_method_panel, view_raw_prompts, override_verdict]

sensitive_fields:
  customer_email:  {action: hash,   salt_env: PII_SALT}
  account_name:    {action: redact_in_narrative, keep_in_table: true}
```

### 21.3 Three enforcement points, all upstream of the model

1. **SQL compilation** — row predicates and column projections injected by `contract.compile_sql()`. Denied columns never enter the result set.
2. **Retrieval pre-filter** — `source_id ∈ allowed_sources` is a hard pre-filter, applied *before* scoring. Restricted documents are never embedded into a query context, never ranked, never seen.
3. **Narrative entity check** (Gate 2, check 7) — belt and braces: scan the generated text for restricted entity values. Should never fire; if it does, that is a bug in 1 or 2 and you want to know.

**The ordering is the security property.** Filtering before retrieval means a restricted document cannot influence the answer even indirectly. Masking at render time would leave it in the model's context — the difference between "the user cannot see it" and "the system did not use it," and only the second is defensible.

### 21.4 Audit log

Append-only DuckDB table, written by `guarded_query()` and by the retrieval pre-filter — never optional, never conditional:

```sql
CREATE TABLE audit_log (
  ts TIMESTAMP, run_id VARCHAR, actor VARCHAR, role VARCHAR,
  action VARCHAR,            -- metric_query | evidence_retrieval | narrative_generation | override
  resource VARCHAR, decision VARCHAR,        -- ALLOWED | DENIED | PARTIAL
  policy_applied VARCHAR, rows_returned INT, items_withheld INT,
  columns_masked VARCHAR[], detail VARCHAR
);
```

Surfaced in the UI as an Audit tab filterable by persona. **Open it during Scenario 6** — it is the fastest way to prove the entitlement story is real rather than cosmetic.

---

## PART 22 — REPOSITORY STRUCTURE

```
businessintelligence-ai/
├── README.md                     # architecture summary + how to run in 3 commands
├── requirements.txt              # with a comment marking langchain-core as transitive
├── app.py                        # Streamlit entrypoint
│
├── config/
│   ├── scoring.yaml              # hypothesis scoring weights (versioned)
│   ├── personas.yaml
│   └── models.yaml               # model routing + prices, for the cost calculator
│
├── semantic/
│   ├── contract.py               # Pydantic KPIContract, compile_sql()
│   ├── registry.py               # loads + validates all YAML contracts
│   ├── gateway.py                # ★ guarded_query() — THE ONLY DuckDB ACCESS PATH
│   ├── freshness.py
│   └── kpis/
│       ├── net_revenue.yaml  orders.yaml  average_order_value.yaml
│       └── conversion_rate.yaml  refund_rate.yaml
│
├── security/
│   ├── policy.yaml
│   ├── entitlements.py           # decide(principal, contract) -> AccessDecision
│   └── audit.py
│
├── detection/
│   ├── engine.py                 # orchestrates the flow in 9.2
│   ├── decompose.py              # STL
│   ├── changepoint.py            # PELT + robust z
│   ├── materiality.py
│   └── sparse.py                 # peer-cohort baseline path
│
├── attribution/
│   ├── lmdi.py                   # identity decomposition
│   ├── adtributor.py             # ★ EP + JS surprise (the core algorithm)
│   ├── significance.py
│   ├── counterfactual.py         # difference-in-differences
│   └── hypotheses.py             # ranking + scoring
│
├── evidence/
│   ├── index.py                  # build/persist embeddings + BM25 index
│   ├── retrieve.py               # hybrid + RRF + contradiction pass
│   ├── structured.py             # changelog / schema-diff / finance joins
│   └── cohort.py                 # D7 roll-up
│
├── llm/
│   ├── client.py                 # thin Anthropic wrapper: routing, caching, cost, retries
│   ├── schemas.py                # Narrative, Claim, RecommendationDraft
│   ├── narrate.py
│   └── prompts/
│       ├── intent.md  narrate_ops.md  narrate_finance.md  verify_advisory.md
│
├── trust/
│   ├── gates.py                  # Gate 1 + Gate 1b
│   ├── verify.py                 # ★ Gate 2, all 10 checks
│   ├── template.py               # deterministic narrative fallback
│   ├── confidence.py
│   └── calibration.py
│
├── recommend/
│   ├── levers.yaml
│   ├── engine.py
│   ├── impact.py                 # computed, never generated
│   └── deferral.py               # cost-sensitive rule
│
├── graph/
│   ├── state.py                  # InsightState
│   ├── nodes.py                  # 22 node functions
│   ├── routing.py                # conditional predicates (pure functions)
│   └── build.py                  # graph assembly + checkpointer
│
├── telemetry/
│   ├── tracer.py                 # node wrapper
│   ├── cost.py
│   └── store.py
│
├── feedback/
│   ├── capture.py
│   └── apply.py                  # batched weight/calibration updates
│
├── ui/
│   ├── pages/          1_workspace.py  2_method.py  3_telemetry.py  4_audit.py
│   └── components/     kpi_header.py  waterfall.py  attribution_matrix.py
│                       hypothesis_card.py  evidence_panel.py  confidence_chip.py
│                       recommendation_card.py  pipeline_ledger.py  states.py
│
├── data/
│   ├── generate.py               # seeded generator with injected events
│   ├── ground_truth.json
│   ├── scenario_manifest.json
│   └── warehouse.duckdb
│
├── eval/
│   ├── run_suite.py  retrieval_labels.jsonl  attribution_labels.jsonl  report.md
│
└── tests/
    ├── test_chokepoint.py        # ★ asserts single DuckDB access path
    ├── test_adtributor.py        # ★ reproduces the paper's worked example
    ├── test_lmdi.py              # contributions sum exactly to ΔV
    ├── test_verify.py            # each of the 10 checks, pass and fail
    ├── test_entitlements.py
    └── test_graph_routing.py
```

**Deliberately flat.** No `core/`, no `services/`, no `interfaces/`, no dependency injection container. Each package is one architectural layer and maps 1:1 to a box on your architecture slide — which means the diagram is navigable by anyone reading the repo, including a judge.

`tests/test_adtributor.py` reproducing the paper's own worked example ($100 → $50, data centre X vs Mobile/Tablet) is a small thing that says a lot: it proves you implemented the published algorithm rather than something Adtributor-flavoured.

---

## PART 23 — BUILD ORDER

Sequenced so that **you have a demoable artifact from Stage 4 onward**, and so the two riskiest things (LLM behaviour, UI polish) are never on the critical path for proving the concept.

**Two ordering decisions that matter more than they look:**
1. **Build the verifier (Gate 2) *before* the narrator.** The verification schema defines what narration is allowed to produce. Building narration first means writing a prompt against nothing and then bending the checks to fit whatever came out — which is how a verification layer quietly becomes decorative.
2. **Build the deterministic template narrative *before* the LLM narrative.** You then always have a working end-to-end demo, and the LLM becomes a quality upgrade rather than a dependency. If the API is down on presentation day, your prototype still runs.

| # | Stage | Task | Libraries | Expected result | Test | Common failure | Done when |
|---|---|---|---|---|---|---|---|
| 0 | **Scaffold** | Repo, deps, Pydantic base models, `config/` | pydantic, duckdb | `pytest` runs, imports clean | smoke | Over-engineering the abstractions on day 1 | `pytest` green on an empty suite |
| 1 | **Data + ground truth** | `generate.py`: 5 KPIs, 132K fact rows, 1,370 docs, 6 injected events, `ground_truth.json` | numpy, pandas, duckdb | Reproducible `warehouse.duckdb` from a seed | Row counts, seed reproducibility, injected events present | Data too clean → nothing to detect; or too noisy → nothing detectable. Tune until baseline CV ≈ 8–12%. | Two runs from the same seed are byte-identical, and a plot of West revenue shows a visible July shift |
| 2 | **Semantic + entitlements** | Contracts, `compile_sql()`, `guarded_query()`, audit, policy | pydantic, duckdb | Every metric read goes through one function | **`test_chokepoint.py`**, `test_entitlements.py` | A "quick" direct query in a notebook that becomes permanent | Chokepoint test passes; Priya's query returns West-only rows |
| 3 | **Detection** | Coverage gate, STL, robust z, PELT, materiality, sparse path | statsmodels, ruptures, scipy | Injected events detected | Precision/recall vs `ground_truth.json` | STL period wrong (7 vs 365) → everything is an anomaly | recall ≥ 0.90, precision ≥ 0.85 on injected events |
| 4 | **Attribution** | LMDI, Adtributor, significance, DiD | numpy, scipy | Correct dimension + slice identified | **`test_adtributor.py` reproduces the paper's example**; `test_lmdi.py` sums exactly | Running Adtributor on ratio KPIs (ignoring `additive: false`) | Top-1 dimension accuracy ≥ 0.80; **demoable milestone — you can now explain an event without any LLM** |
| 5 | **Evidence retrieval** | Index build, BM25 + dense + RRF, structured joins, cohort roll-up, contradiction pass | sentence-transformers, rank_bm25, numpy | Right documents surface for each event | 20-pair in-domain eval | Forgetting the hard date/slice pre-filter → plausible but irrelevant evidence | precision@5 ≥ 0.70 on labelled pairs |
| 6 | **Hypotheses + bundle** | Scoring, ranking, freeze + hash `EvidenceBundle` | pydantic | 2–3 ranked hypotheses with evidence both ways | Golden-file test per scenario | Contradicting evidence never populated because nothing searched for it | Scenario 2 yields two hypotheses within 0.08 |
| 7 | **Gate 2 + template** | All 10 checks; deterministic template narrative | pydantic, re | Verifier catches seeded violations; template renders | `test_verify.py` with hand-written bad narratives | Regex numeric extraction misses currency/percent formats | 10/10 checks pass their unit tests; template renders all 7 scenarios |
| 8 | **LLM narration** | `llm/client.py`, structured outputs, persona prompts, caching, routing | anthropic | Fluent persona narratives that pass Gate 2 | Verification pass rate over 20 runs | Prompt asks for a summary and gets prose instead of claims → **constrain the schema, not the wording** | first-attempt pass rate ≥ 0.90; cache hit rate ≥ 0.6 |
| 9 | **Recommendation + confidence + deferral** | Lever catalogue, computed impact, calibration table, deferral rule | pydantic | Actions with owners, impact, monitoring | Lever eligibility tests; deferral boundary tests | Impact silently becoming an LLM guess | Levers suppressed correctly in Scenario 4; deferral flips between buckets |
| 10 | **LangGraph assembly** | State, 22 nodes, routing, checkpointer, interrupts | langgraph, langgraph-checkpoint-sqlite | Full graph runs all 7 scenarios | `test_graph_routing.py` for every predicate | Business logic leaking into node functions instead of staying in modules | All 7 scenarios reach the correct terminal outcome |
| 11 | **Streamlit** | Workspace, 4 states, method/telemetry/audit tabs | streamlit, plotly | Full demo UI | Manual walkthrough of all 7 | Analysis running inside a callback → 8-second freezes on every click | All 7 scenarios demoable in under 90 s each |
| 12 | **Eval + telemetry** | `run_suite.py`, `report.md`, telemetry tab | pandas | Measured metrics report | CI run | Building this last and running out of time — **do not let this slip** | `eval/report.md` generated with all Part 20 metrics |
| 13 | **Polish** | Graph mermaid export, README, seeded calibration table, demo script | — | Judge-ready | Timed dry run | Adding features instead of rehearsing | Two clean end-to-end dry runs with no code changes between them |

**Critical path:** 1 → 2 → 3 → 4 gets you a working diagnostic engine with no LLM at all. If everything after that went wrong, you would still have a defensible prototype. Protect that sequence.

---

## PART 24 — WHAT NOT TO BUILD

| Technology | Verdict | Why not, specifically |
|---|---|---|
| **Fine-tuning** | **No** | You have ~87 synthetic examples. Fine-tuning on that overfits to your generator, and your quality problem is *grounding*, which fine-tuning does not fix. Saying "we deliberately did not fine-tune, because our failure mode is fabrication, not style" is a stronger answer than a LoRA. |
| **GraphRAG** | **No** | Your entities already live in a star schema with explicit foreign keys. GraphRAG builds a weaker, probabilistic copy of the relationships DuckDB already models exactly. |
| **Knowledge graph / ontology** | **No for Round 2** | The semantic layer *is* your lightweight ontology, and the case asks for a "lightweight KPI or semantic contract" — which is exactly what you have. A full ontology is V3. |
| **Multi-agent systems** | **No — and argue against it** | Multiple agents negotiating an answer is the opposite of "the LLM is not the source of quantitative truth." Every agent boundary is a place a number can mutate without a check. |
| **Autonomous agents** | **No** | Gartner's own "agent drift" warning (D9) is your citation. Your architecture *is* the guardian-agent pattern; adding autonomy underneath it defeats its purpose. |
| **Microservices / Kubernetes / Docker Compose stacks** | **No** | One Python process, one DuckDB file. `git clone && streamlit run`. A judge who can run your prototype in 30 seconds trusts it more than one who cannot run it at all. |
| **Managed vector infrastructure** | **No** | 2.3 MB of vectors (Part 3.3). |
| **Cross-encoder reranking** | **V2** | Nothing to rerank in a 40-document candidate pool. |
| **DoWhy / EconML / causal discovery (PC, LiNGAM)** | **No** | Structure learning on 5 KPIs and 4 dimensions with 550 observations produces unstable graphs you cannot defend under questioning. DiD gives you a real, checkable counterfactual instead. **Name this as a deliberate trade-off** — it shows you know the field well enough to decline it. |
| **Forecasting (Prophet / ARIMA / NeuralProphet)** | **No** | You need a *baseline* (what would have happened), which STL already provides. Forecasting the future is a different product. |
| **Streaming (Kafka / Flink / real-time alerting)** | **No** | Batch + on-demand covers every scenario. |
| **A second LLM provider for "redundancy"** | **No** | Two providers doubles the prompt surface and halves the caching benefit. Use the `fallbacks` parameter within one provider. |
| **A chat interface** | **No — actively harmful** | Chat invites open-ended questions your gates cannot bound and trains users to expect an answer to everything. Bounded query → bounded workspace. |
| **RAG over the KPI definitions** | **No** | Argued in 2.3. Fuzzy-matching a source of truth is how the wrong definition reaches a narrative. |
| **Auth / SSO / user management** | **No** | Simulated principal + one chokepoint. Say so. |

**The framing sentence for this slide:** *"We evaluated fourteen technologies and used four. Here is what we rejected and why."* A judge remembers the rejections, because they are the only part that cannot be faked.

---

## PART 25 — FINAL ROUND 2 ARCHITECTURE

### 25.1 The exact stack

| Component | Decision |
|---|---|
| **Primary LLM** | **Claude Opus 5** (`claude-opus-5`) — narration + verification. Structured outputs, adaptive thinking with `effort`, prompt caching. |
| **Cheap route** | **Claude Haiku 4.5** (`claude-haiku-4-5`) — intent resolution only. |
| **Fallback** | **Claude Sonnet 5** (`claude-sonnet-5`) via the server-side `fallbacks` parameter. |
| **Embedding model** | **`BAAI/bge-small-en-v1.5`**, local, via `sentence-transformers`. |
| **Vector store** | **None.** NumPy matrix (2.3 MB) + `rank_bm25`, fused with RRF (k=10). Deliberate, defended in 3.3. |
| **Database** | **DuckDB**, single file: facts, dimensions, documents, policy, audit, feedback, telemetry. |
| **LangChain** | **NO.** (`langchain-core` transitively under LangGraph only.) |
| **LangGraph** | **YES.** 22 nodes, typed state, 5 conditional branches, 1 bounded cycle, 2 interrupts, SQLite checkpointer. |
| **Streamlit** | **YES.** Decision workspace, 4 designed non-happy states, 4 tabs. Explicitly a Round 2 surface. |
| **Statistical methods** | Coverage gate → **STL** → **robust z (MAD)** → **PELT** → **materiality gate**. CUSUM and BOCPD named, not built. |
| **Attribution** | **LMDI** identity decomposition + **Adtributor** (EP + JS surprise) + significance tests + **difference-in-differences** counterfactual. |
| **Retrieval** | Hard metadata pre-filter → **BM25 + dense → RRF** → cohort roll-up → contradiction pass. No reranker in Round 2. |
| **Verification** | **Gate 1** (freshness, completeness, schema stability, evidence sufficiency, hypothesis separation) + **Gate 2** (10 checks, 7 hard) + 1 retry + deterministic template. |
| **Telemetry** | Per-node latency, LLM/non-LLM split, tokens, cache hits, cost, gate outcomes, violations by type. Eval suite in CI. |
| **Security** | Policy-as-YAML, 3 enforcement points, all upstream of the model; append-only audit log. |
| **Deployment** | `git clone && pip install -r requirements.txt && streamlit run app.py`. One process. No containers. |

### 25.2 Architecture diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            STREAMLIT DECISION WORKSPACE                          │
│   Workspace │ Method (L4) │ Telemetry │ Audit        [Persona: Priya ▾]          │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │  one InsightBundle
┌───────────────────────────────────▼─────────────────────────────────────────────┐
│                       LANGGRAPH  (22 nodes · SQLite checkpointer)                │
│                                                                                  │
│  ①resolve_intent ──🟪LLM Haiku                                                   │
│  ②load_contract ─▶③entitlements ─▶④GATE 1 ─▶⑤detect ─▶⑥materiality              │
│                          │            │                          │               │
│                     access_denied  abstain_data              no_finding          │
│                                                                  ▼               │
│  ⑦LMDI ─▶⑧Adtributor ─▶⑨DiD ─▶⑩retrieve ─▶⑪rank+freeze ─▶⑫GATE 1b              │
│                                                                  │               │
│                                          abstain / clarify ◄─────┤               │
│                                                                  ▼               │
│                    ┌───────────▶ ⑬narrate ──🟪LLM Opus 5 ──▶ ⑭GATE 2             │
│                    │  retry ≤1              (no tools)          │                │
│                    └──────────────────────────────────┬─────────┘                │
│                                        ⑮template ◄────┘ (2nd failure)            │
│                                            │                                     │
│  ⑯recommend ─▶⑰calibrate ─▶⑱defer ─▶⑲escalate⏸ / ⑳deliver ─▶㉑feedback⏸ ─▶㉒log │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────────┐
│                    SEMANTIC + ENTITLEMENT LAYER  ★ single chokepoint             │
│   KPI contracts (YAML→Pydantic) · compile_sql() · row filter · column mask       │
│   · source allowlist · lineage · freshness · audit                               │
└───────────────────────────────────┬─────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────────┐
│  DuckDB (single file)                          Local indices                     │
│  S1 warehouse (daily)                          NumPy embeddings  2.3 MB          │
│  S2 product analytics (hourly, no product dim) BM25 index                        │
│  S3 finance (weekly, T+3) · docs · policy      1,370 documents                   │
│  audit · feedback · telemetry · calibration                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

           🟪 = LLM (3 calls, ~1.9 s, ~$0.041)     everything else deterministic
```

### 25.3 Component responsibilities — the slide the case is asking for

| Class | Owns | Components |
|---|---|---|
| **Deterministic** | Every number, every rule, every access decision, every route | Semantic layer, `compile_sql`, entitlements, materiality, LMDI, Adtributor, lever eligibility, computed impact, Gate 1, Gate 2 checks 1–9, confidence, deferral rule, routing predicates, telemetry, audit |
| **Statistical** | Is it real, is it significant, is it slice-specific | STL, robust z (MAD), PELT, Welch t-test, two-proportion z-test, difference-in-differences, calibration |
| **Traditional ML** | **None — and that is the finding.** | No supervised model. There is no labelled training set for "why did revenue drop," and pretending otherwise is exactly the failure AgentRCA's zero-shot framing addresses. Named honestly as V2: a learned hypothesis re-ranker once ≥ 200 labelled cases exist. |
| **Retrieval** | Find corroborating **and contradicting** evidence | BM25, dense (bge-small), RRF, metadata pre-filter, cohort roll-up |
| **LLM** | Intent parsing · narrative synthesis · advisory second opinion · lever phrasing | 3 calls, schema-constrained, no tools, no data access |
| **Human** | Accept / reject / correct / escalate; approve levers; own the decision | 5 typed feedback outcomes, 2 interrupt points |

### 25.4 MVP — the smallest thing that convincingly satisfies Round 2

Stages 1–8 plus a thin Streamlit, and **Scenarios 1, 3, 5, 7**:

- 5 connected KPIs, 3 sources, 3 grains, 3 cadences ✓
- Semantic contract with definitions, formulas, drivers, thresholds, lineage, access ✓
- 2 personas with different narratives and actions ✓
- 1 multi-factor movement with known drivers ✓
- 1 low-confidence abstention ✓
- 1 sparse-history scenario ✓ *(add Scenario 4 — it is cheap once the coverage gate exists)*
- 1 role-based entitlement scenario ✓
- Evidence with freshness, method, contribution, confidence, lineage ✓
- Clear LLM vs non-LLM breakdown ✓ *(the pipeline ledger)*
- Runtime telemetry: latency, model calls, tokens, cost ✓

**That is every minimum expectation the case lists.** Everything beyond it is margin.

### 25.5 V2 — only after the MVP works

Ordered by value per unit of effort: (1) cross-encoder reranking, if the retrieval eval justifies it; (2) **HotSpot** for multi-dimensional root causes; (3) CUSUM online monitoring for proactive alerting; (4) a learned hypothesis re-ranker at ≥ 200 labelled cases; (5) pgvector + Postgres when the corpus outgrows memory; (6) embedded delivery inside the host BI tool; (7) conformal prediction sets with formal coverage guarantees; (8) Bayesian online changepoint detection for slow drift.

### 25.6 The five judge-facing differentiators

1. **Adtributor.** You implement a published Microsoft algorithm (NSDI '14) purpose-built for "revenue moved, which dimension is to blame" — 95% accuracy against 20% for the size-ranking strawman. And you can *show* the difference live by toggling surprise off. Almost no team will have a named, cited, deterministic attribution algorithm; most will have an LLM guessing.

2. **The LLM cannot fetch data, and cannot emit an unverified number.** Three enforced mechanisms: no tools on the narrator, a claim schema with mandatory evidence IDs, and a numeric allowlist. When Gate 2 fails twice, the system ships a less fluent, fully faithful template — and labels it. **Demonstrate the failure live.** A prototype that refuses to produce its best-looking output is a prototype a judge believes.

3. **Abstention is a graph edge, not a model decision.** AbstentionBench found reasoning-tuned models abstain 24% worse than non-reasoning ones. So your system never asks the model whether it is confident — a deterministic predicate decides before the model is called, and the telemetry proves it (`llm_calls = 0` on abstained runs).

4. **Measured, not asserted.** Because the dataset ships with injected ground truth, you report real detection precision/recall, real Top-1/Top-2 attribution accuracy, real precision@5, a real risk-coverage curve and a real cost per insight (~$0.041). Bring `eval/report.md`. Most prototypes cannot quote a single measured number.

5. **The rejections.** LangChain, GraphRAG, multi-agent, fine-tuning, causal discovery, cross-encoder reranking, vector databases — each declined with a specific technical reason. Selection is the signal.

### 25.7 The final answer, without diplomacy

**LangGraph, embeddings and Streamlit earn their place. LangChain does not.**

- **LangGraph** is justified because the Round 2 case mandates conditional abstention, a verify-retry cycle, human interrupts and a lineage trail — and a checkpointed graph delivers all four from one dependency. Without those requirements it would be decoration. With them, hand-rolling it is strictly worse.
- **Embeddings** are justified over exactly one thing: ~1,370 free-text documents where paraphrase defeats keyword search. They are excluded from KPI metadata, changelogs, lever catalogues and every number. Scope is what makes them defensible.
- **Streamlit** is justified as the fastest route to a multi-state, multi-persona analytical UI — and you should name its production replacement rather than defend it as an endpoint.
- **LangChain is decoration here, and worse than neutral.** Its 2026 value is an agent loop. Your architecture's entire thesis is that the model must not choose what data it sees. Adopting the abstraction would quietly undermine the claim your prototype exists to prove.

**And the simpler architecture question, answered directly:** the simpler architecture *is* the recommended one. The heavy lifting is done by a 1978-vintage seasonal decomposition, a 2014 attribution algorithm, a rank-fusion formula, and 10 deterministic string checks. Three LLM calls sit at the edges doing the one thing language models are genuinely best at — turning a verified structure into words a specific human can act on.

That is not a smaller ambition than a full agentic stack. **It is a more defensible one — and defensibility is precisely what this case is testing.**
