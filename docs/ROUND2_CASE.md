# Round 2 Case — Problem Track 3: BusinessIntelligence.ai
**Accenture Innovation Challenge 2026 · Round 2, Prototype Development**

*Verbatim transcription of the official Round 2 problem statement PDF (`6a882073d90c9_accenture_innovation_challenge_round_2_detailed_problem_statements_final.pdf`, pages 4–6 and 7). This is the requirements source of truth. Do not paraphrase it into code comments; cite section numbers from here instead.*

---

## General framing (applies to all tracks)

> Congratulations on advancing to Round 2. You've already pitched an initial concept for one of the four problem statements — now it's time to go deeper. This document expands your chosen track with the real-world complexity that companies grapple with, along with a broader option for solutioning areas you might explore. It is still intentionally open: there is no single "correct" architecture, and you are not expected to have access to a real company's proprietary data. Use reasonable assumptions and focus on innovation, creativity, and technical novelty.

> Each problem track below expands on its Round 1 brief with deeper context, the real complexities such problems present inside real organizations, and a broad set of solutioning areas you're free to draw from selectively — **you are not expected to address every point listed.**

---

## Recap & Expanded Context

> In Round 1, you explored a KPI storytelling engine that explains what changed in a business metric, identifies likely root causes, and recommends next steps in plain language. In practice, most businesses track KPIs across fragmented systems with different refresh cadences and granularities, and the "right" explanation for a movement often depends on who's asking and what they plan to do about it.

---

## R2-OBJ · Round 2 Objective

Design and demonstrate a working prototype of a KPI intelligence-to-action engine that:

| ID | Objective |
|---|---|
| **R2-OBJ-1** | Detects and prioritises material KPI movements. |
| **R2-OBJ-2** | Reconciles data and business context across heterogeneous sources. |
| **R2-OBJ-3** | Identifies and ranks explanatory drivers using appropriate analytical methods. |
| **R2-OBJ-4** | Generates persona-specific narratives supported by traceable evidence. |
| **R2-OBJ-5** | Communicates uncertainty and abstains when evidence is insufficient or contradictory. |
| **R2-OBJ-6** | Recommends practical actions grounded in business levers, constraints and decision rights. |
| **R2-OBJ-7** | Mechanism to learn from analyst and business-user feedback. |
| **R2-OBJ-8** | Operates within realistic security, cost, latency and scalability constraints. |

> **The LLM should not be treated as the source of quantitative truth. Teams should explicitly demonstrate when they use deterministic logic, SQL, business rules, statistics, traditional ML, causal inference, retrieval or LLMs — and why.**

---

## R2-CX · Real-World Complexities to Consider

| ID | Complexity |
|---|---|
| **R2-CX-1** | Multiple interacting drivers such as price, volume, mix, marketing, supply, seasonality, competition and external events. |
| **R2-CX-2** | Different source-system refresh cadences, grains, data quality levels and historical coverage. |
| **R2-CX-3** | Inconsistent KPI definitions, hierarchies, calendars, business rules and aggregation logic. |
| **R2-CX-4** | Sparse history for new products, categories or markets. |
| **R2-CX-5** | Materiality based on both statistical significance and business impact. |
| **R2-CX-6** | Contradictory evidence, missing data and confidence calibration. |
| **R2-CX-7** | Role-based personalization of insight depth, recommended actions and delivery channels. |
| **R2-CX-8** | Row-, column- and domain-level security, sensitive-data protection and auditability. |
| **R2-CX-9** | Model and data drift, feedback capture and continuous evaluation. |
| **R2-CX-10** | LLM economics, including model choice, token consumption, latency, caching and cost per insight. |

---

## R2-SA · Solutioning Areas You Could Explore

*Teams may explore a hybrid combination of the following. This is a menu, not a checklist.*

- Anomaly detection, contribution analysis, forecasting, causal inference and business-rule reasoning.
- Governed KPI semantics, metadata, lineage, business rules, ontology or knowledge graphs.
- LLM-assisted intent understanding, orchestration, narrative synthesis and contextual retrieval.
- Proactive alerts, conversational analysis, augmented dashboards or decision workspaces.
- Confidence scoring, evidence citation, alternative hypotheses and abstention mechanisms.
- Action recommendations structured as: **driver → controllable lever → action → expected impact → owner → confidence → monitoring plan**
- Human feedback, expert validation, correction workflows and learning loops.
- Platform-native and custom capabilities using Databricks, Snowflake, Microsoft Fabric, Tableau, Qlik, Looker or another suitable technology. (Open to choose any platform, or build a completely custom solution, or a hybrid.)

> Platform-specific solutions are acceptable, but teams should distinguish between **native, configured, custom-built and externally integrated** capabilities.

---

## R2-MPE · Minimum Prototype Expectations

**These are the hard acceptance criteria. Every one must be demonstrable.**

| ID | Requirement |
|---|---|
| **R2-MPE-1** | Three to five connected KPIs across two or three data sources with different grains or refresh cadences. |
| **R2-MPE-2** | A lightweight KPI or semantic contract covering definitions, calculations, drivers, thresholds, lineage and access restrictions. |
| **R2-MPE-3** | At least two personas receiving different insight narratives or recommended actions. |
| **R2-MPE-4** | One multi-factor KPI movement with known or simulated underlying drivers. |
| **R2-MPE-5** | One low-confidence scenario in which the engine requests clarification or abstains. |
| **R2-MPE-6** | One sparse-history or newly launched KPI scenario. |
| **R2-MPE-7** | One role-based security or entitlement scenario. |
| **R2-MPE-8** | Evidence showing source freshness, analytical method, contribution, confidence and lineage. |
| **R2-MPE-9** | A clear breakdown of LLM versus non-LLM processing. |
| **R2-MPE-10** | Runtime telemetry covering latency, model calls, token usage and estimated cost. |

---

## R2-DEL · What Round 2 Asks You to Deliver

| ID | Deliverable |
|---|---|
| **R2-DEL-1** | **Detailed Business Proposal** — problem framing, solution design, target users, business case and impact, a phased roadmap, and key risks with mitigations. |
| **R2-DEL-2** | **Working Prototype** — a functional demonstration of the solution's core mechanism. It does not need to be production-grade or use real enterprise data; a working proof-of-concept on illustrative or sample data is expected and encouraged. |
| **R2-DEL-3** | **Pitch Presentation** — presenting both the proposal and the prototype for evaluation. |

---

## Note on scope discipline

The case says explicitly that teams are *not* expected to address every point in the complexities or solutioning lists. `docs/ROUND2_TECHNICAL_ARCHITECTURE.md` Part 24 records which technologies were deliberately declined and why. Declining with a reason is treated as a positive signal by this project, not a gap.
