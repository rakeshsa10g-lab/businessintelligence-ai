# BusinessIntelligence.ai — Master Compilation
**Accenture Innovation Challenge 2026 · Problem Statement 3 · Team SouthernHustlers**

Compiled 2026-08-21. This single file contains the full text of every research, strategy, framing, and script document produced for this project, concatenated in the order they were created. It cannot contain the binary deliverables (the deck, the video, the exported PDF) — those are listed with their exact paths in the manifest at the end.

## Table of contents

1. Strategy Roadmap
2. Master Research Dossier
3. Research Findings (full, all sections)
4. CIRCLES + RCA Framing
5. NotebookLM Synthesis Guide
6. AIC Round 1 — Deck Content Spec
7. AIC Round 1 — Visuals Guide (Napkin AI)
8. AIC Round 1 — 3-Minute Video Script
9. Design System — README
10. Manifest of binary deliverables and where they live

---



# 1. Strategy Roadmap

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\BusinessIntelligence_ai_Strategy_Roadmap.md`*

---

# Strategy Roadmap: BusinessIntelligence.ai — KPI Storytelling Engine

## 1. The Problem, Restated

**Case prompt:** A dashboard shows revenue dropped 8% in a region. It doesn't explain why or what to do next — that translation currently falls to an analyst and takes days. You're asked to design an AI system that:

- Explains *what changed* in a business metric, in natural language
- Identifies *likely root causes*
- Recommends *next steps*
- Uses *both structured data* (the metrics/warehouse) and *unstructured data* (support tickets, sales notes, news, Slack threads, etc.)

**The two hard questions baked into "Think about":**
1. How do you separate a *meaningful* change from *noise*?
2. How do you move from *correlation* to something a leader can *act on* — and what happens when the data is genuinely *ambiguous*?

These two questions are the actual case — everything else is scaffolding. A generic "AI dashboard that explains numbers" answer will not differentiate. The roadmap below is built so that your research and tooling converge on strong, specific answers to exactly these two questions, then gets packaged into a McKinsey-style narrative.

---

## 2. Overall Approach

Treat this like a real PM case: **Research → Frame → Solve → Package**, using the CIRCLES and Root Cause Analysis (RCA) frameworks from your casebook as the analytical spine, and the tool stack to accelerate each stage rather than replace the thinking.

| Stage | Goal | Primary Tools | Output |
|---|---|---|---|
| 1. Research & Ground Truth | Understand how this problem is solved today, what's broken, what users actually say | Apify, Answer the Public, Elicit AI | Insight doc |
| 2. Frame the Case | Apply CIRCLES + RCA to structure the solution | Claude / NotebookLM | Structured solution outline |
| 3. Synthesize & Ideate | Turn scattered research into a coherent system design | NotebookLM | Mind map / architecture sketch |
| 4. Visualize | Convert the design into diagrams a judge can scan in seconds | Napkin AI | Visual assets |
| 5. Package | Build the final case deck | Claude (pptx skill) | McKinsey-style deck |

---

## 3. Stage 1 — Research & Ground Truth

Before designing anything, you need real signal on (a) how existing BI/analytics tools fail today and (b) what "explaining a KPI" actually looks like to a business user. This is what makes your answer feel researched instead of invented on the spot.

### 3.1 Apify — Scrape public reviews & comments
Target sources where people complain about BI tools not explaining *why*:
- G2 / Capterra / TrustRadius reviews for Tableau, Power BI, Looker, ThoughtSpot, Sisense, Domo, Explorium, Pecan AI
- Reddit threads (r/BusinessIntelligence, r/analytics, r/PowerBI) — search "dashboard doesn't explain," "why did X drop," "root cause analytics"
- App store reviews for mobile BI apps
- Twitter/LinkedIn posts from data analysts venting about manual root-cause digging

**What to extract:** recurring complaint patterns (e.g., "dashboards are descriptive, not diagnostic," "takes an analyst 2 days to explain one anomaly," "false alarms from noisy metrics"). These become your problem validation and your differentiators slide.

### 3.2 Answer the Public — Customer language & question mining
Feed in seed terms: "why did revenue drop," "KPI explanation," "root cause analysis tool," "business metric anomaly," "explain dashboard." This surfaces the *actual phrasing* business leaders use when they want an explanation — useful for:
- Naming the product's natural-language output style (match how humans actually ask "why")
- Identifying adjacent unmet needs (e.g., "how to explain KPI drop to CEO" tells you the audience cares about defensibility, not just detection)

### 3.3 Elicit AI — Academic grounding for the two hard questions
This is where you get rigor for the "Think about" section, which is the differentiator. Search Elicit for:
- **Signal vs. noise:** statistical process control, anomaly detection, time-series changepoint detection, seasonality-adjusted control limits (e.g., CUSUM, Bayesian changepoint detection, STL decomposition)
- **Correlation → causation:** causal inference in business analytics, Granger causality, causal graphs / DAGs for root-cause attribution, "root cause analysis for time series" papers
- **Handling ambiguity:** confidence-calibrated explanations, abstention in ML systems, human-in-the-loop decision support

You don't need to become a statistician — you need 3–4 named techniques you can cite in the case ("we'd use STL decomposition to separate seasonality from trend, then flag deviations beyond N standard deviations as candidate anomalies") to sound credible and specific rather than hand-wavy.

---

## 4. Stage 2 — Frame the Case (CIRCLES + RCA, adapted)

This case is a hybrid: **Product Design** (CIRCLES) wrapping a **Root Cause Analysis engine** (RCA) as the core feature. Use CIRCLES for the overall product shape, and nest the RCA framework inside "List Solutions" for the diagnostic logic itself.

**C — Comprehend the situation.** Clarify scope before designing: Is this for a specific persona (regional sales lead, CFO, ops manager)? Real-time or scheduled? What data sources are actually connected? What counts as "unstructured" here — support tickets, CRM notes, news, internal Slack? Assume: mid-size B2B enterprise, connects to a data warehouse + a few SaaS tools (CRM, support desk), used by non-technical business leaders.

**I — Identify the customer.** Segment: the *analyst* (currently does this manually, is your ally and QA layer), the *business leader* (consumer of the explanation, wants confidence + action), and the *data/BI team* (owns the pipes, cares about trust and governance). Prioritize the business leader as primary — they're the one losing days waiting on an analyst.

**R — Report the customer's needs.** Not "a dashboard" — the underlying need is *time-to-decision*. They don't want data, they want a defensible narrative: what changed, why, how confident are we, what should I do.

**C — Cut through prioritization.** Use the AARRR-adjacent lens but repurposed as a **diagnostic funnel**: Detect → Explain → Attribute → Recommend → Verify. Prioritize Detect + Explain for MVP (this is where "noise vs. signal" lives), Attribute + Recommend as v2, Verify (feedback loop) as the trust-building layer that should exist from day one even if thin.

**L — List solutions.** This is where your RCA framework and Elicit research combine into the actual engine design:

1. **Detection layer (signal vs. noise):**
   - Decompose each KPI into trend, seasonality, and residual (e.g., STL or similar).
   - Apply statistical thresholds (e.g., control limits, z-scores on residuals) rather than flat % thresholds — an 8% drop in a volatile metric may be noise; a 2% drop in a stable one may be real.
   - Use changepoint detection to distinguish a genuine regime shift from a one-off blip.
   - Confidence-score every flagged anomaly instead of binary alerting.

2. **Attribution layer (correlation → action):**
   - Borrow directly from the casebook's RCA structure: bucket candidate causes into **External factors** (competitor moves, market/seasonal trends, macro events — surfaced via news/unstructured data) and **Internal factors** (pricing changes, product/UI changes, campaign changes, funnel-stage breaks — surfaced via structured logs + change/event tracking, e.g., a changelog or feature-flag system).
   - Walk the metric's *user/business journey* the way the sample cases do (Uber ride journey, Blinkit checkout funnel) — decompose the KPI into its component drivers (e.g., Revenue = Volume × Price × Conversion) and isolate which sub-metric moved.
   - Use unstructured data (support tickets, sales call notes, news) as corroborating evidence, not standalone proof — this is the key move from correlation to something actionable: a leader trusts "conversion dropped in the payment step AND support tickets mention payment errors AND this started the same week as a gateway API change" far more than a bare correlation.
   - Rank candidate causes by evidence strength, not just statistical correlation.

3. **Recommendation layer:**
   - Map each root-cause category to a standard playbook of next steps (e.g., payment-gateway issue → "escalate to eng, check API logs"; competitor promotion → "review pricing/promo response").
   - Always pair a recommendation with its confidence and supporting evidence, so it's a suggestion the leader can interrogate, not a black-box directive.

4. **Handling genuine ambiguity (the differentiator):**
   - When evidence is thin or conflicting, the system should say so explicitly — present the top 2–3 competing hypotheses with their evidence for/against, rather than forcing a single answer.
   - Route ambiguous cases to the human analyst with a pre-assembled evidence packet (cuts their investigation time from days to an hour, rather than replacing them).
   - Log resolved ambiguous cases as training signal for the next occurrence (the feedback loop from stage "Verify").

**E — Evaluate trade-offs.** Speed vs. accuracy (real-time flagging vs. waiting for more data to confirm a trend), automation vs. trust (fully automated narratives vs. human-in-the-loop sign-off), false positives vs. false negatives (alert fatigue vs. missed real issues), and build vs. buy (LLM for narrative generation vs. classical stats for detection — recommend a hybrid: statistical/causal methods for rigor, LLM strictly for turning verified findings into natural language).

**S — Summarize your recommendation.** One clear sentence: "Build a hybrid statistical + LLM engine that detects statistically significant KPI shifts, attributes them using structured + unstructured evidence ranked by confidence, and explains ambiguity rather than hiding it — cutting analyst turnaround from days to minutes while keeping humans in the loop for low-confidence cases."

---

## 5. Stage 3 — Synthesize with NotebookLM

Upload into one NotebookLM notebook: the case statement, your Apify scrape summaries, Answer the Public output, Elicit AI paper summaries, and your CIRCLES/RCA notes from Stage 2.

Use it to generate:
- A **mind map** of the full solution (Detect → Attribute → Recommend → Verify, with sub-branches for each) — this becomes your architecture slide skeleton.
- An **infographic/summary** of the research findings (top 5 complaints about existing BI tools, top statistical techniques found) — supporting evidence slides.
- A **FAQ / audio overview** you can use to rehearse defending the case out loud before presenting — NotebookLM's Q&A grounding on your own sources helps you stress-test the logic (e.g., "how would the system know it's wrong?").

---

## 6. Stage 4 — Visualize with Napkin AI

Take the structured text from Stages 2–3 (not raw notes) and turn it into 3–4 clean diagrams:
1. **System architecture** — Data sources (structured + unstructured) → Detection layer → Attribution layer → Recommendation layer → Output (natural-language narrative + confidence + evidence).
2. **The diagnostic funnel** — Detect → Explain → Attribute → Recommend → Verify, annotated with what happens at each stage.
3. **Decision flow for ambiguity** — what the system does when confidence is low (multi-hypothesis view + human handoff).
4. **Before/After** — analyst spends 2 days manually digging vs. system surfaces a ranked, evidenced explanation in minutes.

Napkin works best from tight, declarative sentences — feed it the bullet points from Stage 2, not paragraphs.

---

## 7. Stage 5 — Package with Claude (McKinsey-style deck)

Once the diagrams exist, use Claude to assemble the final case deck (pptx skill), structured the way case interviews/competitions expect:

1. Title + one-line thesis
2. Problem framing (the 8%-drop example, why current dashboards fail)
3. Research grounding (Apify/Answer the Public findings — validates the problem is real)
4. Framework slide (CIRCLES applied, or your Detect→Explain→Attribute→Recommend→Verify funnel)
5. Solution deep-dive: Detection (signal vs. noise), Attribution (correlation → action), Ambiguity handling — one slide each, each ending in a crisp "so what"
6. Architecture diagram (from Napkin)
7. Trade-offs slide (speed vs. accuracy, automation vs. trust)
8. Success metrics (time-to-explanation, analyst hours saved, recommendation acceptance rate, false-positive rate)
9. Recommendation / summary slide
10. Appendix: research sources, academic citations from Elicit

Keep each slide to one idea, one visual, minimal text — that's the McKinsey convention Claude should follow when generating it.

---

## 8. Suggested Timeline (if this is a timed case/competition)

| Time | Activity |
|---|---|
| First 15–20% | Research (Apify + Answer the Public scan, Elicit AI search) — don't skip this, it's what separates you from a generic answer |
| Next 30% | Frame with CIRCLES + RCA, nail the two "Think about" questions specifically |
| Next 20% | NotebookLM synthesis + Napkin diagrams |
| Final 25–30% | Deck build in Claude, rehearse narrative, tighten the "so what" on every slide |

---

## 9. The One Thing to Not Get Wrong

Judges will probe hardest on the two "Think about" questions. Make sure your answer to "signal vs. noise" names an actual technique (not just "we'll use AI to detect anomalies"), and your answer to "ambiguity" shows the system *admitting uncertainty* rather than always producing a confident-sounding wrong answer — that's the detail that separates a strong CIRCLES answer from a generic one.



---



# 2. Master Research Dossier

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\BusinessIntelligence_ai_Master_Research.md`*

---

# BusinessIntelligence.ai — Master Research Dossier
*Case: Design a KPI storytelling engine — AI that explains what changed in a business metric, identifies root causes, and recommends next steps using structured + unstructured data.*

This file merges (1) the analysis of your `Business_Insight_Areas_V2` prompt workbook, (2) a domain-relevance map telling you which of its 111 insight areas actually matter for this case, (3) a ready-to-paste self-prompt library adapted from its three lenses, and (4) real research already executed against the highest-value segments — with sources, quotes, and stats you can cite directly in the deck. Pick this up in Claude Code and keep running the unexecuted prompts in Part C against whatever case-specific files you're given.

---

## Part A — What the workbook is, and how it's been adapted here

The workbook is built for a different situation than the one we're in: it assumes you've uploaded a specific company's Excel data + PDFs and want Claude to cross-reference *your files*. We don't have a target company's dataset — this is a **product design case**, not a data-diagnosis case. So instead of "cross-reference the Excel sheet against the PDF," I've re-pointed the same three lenses (Pattern Disruptor / Strategic Horizon / Decision Activator) at **open market and technical research**, treating the web as the "uploaded files." Where you do get case-specific data later (in the live competition), the original workbook prompts become directly usable again — Part C is written so you can drop real file names into the bracketed placeholders at that point.

**The three lenses, and why order matters:**
1. **Pattern Disruptor** — "what is the data/market hiding?" → run first, surfaces contradictions and non-obvious findings.
2. **Strategic Horizon** — "where is this going?" → run second, converts findings into forward-looking bets and one contrarian view.
3. **Decision Activator** — "what do we do about it?" → run last, forces every finding into a quantified, cited recommendation.

---

## Part B — Domain relevance map (all 16 domains)

| Domain | Relevance to this case | Why |
|---|---|---|
| Customer & Market | **High** | VoC and behavior/psychology directly shape how the engine's output should read and be trusted by a business leader |
| Competitive & Industry | **High** | Defines white space vs. Tellius/ThoughtSpot/Power BI/Arria — needed for differentiation |
| Product & Innovation | **High** | Product-market fit signals for AI copilots directly inform adoption risk |
| Technology & Data | **High** | Data quality/governance is the single biggest risk to a system that auto-generates causal claims |
| Sales & Revenue | **High** | The case's own example (regional revenue drop) lives here — revenue decomposition methodology |
| Digital & E-commerce | **High** | Conversion funnel drop-off analysis is the closest analog to "explain why a KPI moved" |
| Customer Service & Exp. | **High** | Support tickets are the primary unstructured data source the case explicitly requires |
| Risk & Compliance | **Medium-High** | Fraud detection is the most mature sibling discipline for anomaly detection + false-positive management |
| Financial & Economic | **Medium-High** | P&L/unit economics is the metric layer most KPI dashboards actually track |
| Macroeconomic & External | **Medium** | External-factor bucket in root-cause attribution (mirrors the casebook's RCA "external factors") |
| People & Talent | **Medium** | Relevant only for the "does this replace or augment the analyst" narrative — skills gap angle |
| Marketing & Brand | **Low-Medium** | Only relevant as a source of KPIs the engine might explain (campaign ROI), not core to the product design |
| Operations & Supply Chain | **Low** | Plausible KPI source but not differentiating for this specific case |
| Channel & Partnerships | **Low** | Same — plausible KPI source only |
| Geographic & Demographic | **Low** | The case's own example is regional, but this is covered under Sales & Revenue segmentation already |
| Risk sub-areas: ESG, Geopolitical | **Skip** | Not relevant to an internal KPI-explanation product |

**Recommendation:** don't force research into all 111 rows — that dilutes signal. The 8 "High" domains below are where real depth was executed. Part C gives you self-prompts for all 8 (plus the 4 "Medium" ones) so you can keep going in Claude Code if you want more.

---

## Part C — Self-prompt library (paste into Claude Code, one master prompt per lens, then row prompts)

### Master Prompt — Pattern Disruptor (adapted, no uploaded files required)

```
You are a forensic data analyst and senior strategy consultant with 20 years of experience finding non-obvious patterns in messy business data.

I'm researching the open web (product reviews, forums, vendor docs, analyst reports, academic papers) rather than a proprietary dataset, for a case: designing "BusinessIntelligence.ai," an AI system that explains what changed in a business metric, identifies root causes, and recommends next steps, using structured + unstructured data.

Your working method for ALL prompts in this session:
1. Cross-reference vendor claims/documentation AGAINST real user reviews and forum complaints — never take a vendor's marketing claim at face value.
2. Hunt for contradictions: where a product claims to solve "why," but real users say it still requires manual interpretation.
3. Ignore surface-level obvious findings. Only surface insights that require connecting at least two sources (e.g., a stat from an analyst report + a complaint pattern from reviews).
4. Think like a detective: what is the market hiding about how well "AI explains business metrics" actually works today?

Use this once. Then send the row prompts below as follow-ups.
```

### Master Prompt — Strategic Horizon (adapted)

```
You are a Chief Strategy Officer and scenario planner preparing a leadership team for a competitive case presentation on an AI KPI-explanation product.

Your working method for ALL prompts in this session:
1. Focus on DIRECTION and VELOCITY — what's accelerating (agentic analytics, GenAI-native BI) vs. what's stalling (copilot adoption plateaus)?
2. Look for leading indicators in analyst forecasts (Gartner, etc.) and vendor roadmaps, not just current-state comparisons.
3. Always produce at least one contrarian view — what does the evidence suggest that most "AI will replace analysts" takes are getting wrong?

Use this once. Then send the row prompts below as follow-ups.
```

### Master Prompt — Decision Activator (adapted)

```
You are a McKinsey-style management consultant preparing a board-ready recommendation for a case competition. Precision and evidence are non-negotiable.

Your working method for ALL prompts in this session:
1. Every recommendation MUST cite a specific stat, quote, or source found in research — no generic advice.
2. Quantify: state expected impact in numbers/percentages/time saved, even as a range, sourced from analogous domains (fraud ops, support ops) where the case itself has no numbers.
3. For every "build this" recommendation, name what should be AVOIDED based on what the research disproves (e.g., "don't build a fully autonomous explain button — evidence shows trust breaks without a confidence layer").

Use this once. Then send the row prompts below as follow-ups.
```

### Row prompts — High-relevance domains (already researched in Part D; re-run any time you want to go deeper)

**Technology & Data → Data Quality & Governance**
> Pattern Disruptor: What hidden failure modes exist where an AI root-cause engine would confidently generate a wrong explanation because of upstream data quality issues? Find contradictions between vendor claims of "automated insight" and real evidence about GIGO in AI systems.

**Customer Service & Exp. → Support Ticket Volume & Resolution Time**
> Pattern Disruptor: What non-obvious signal do support tickets carry that structured metrics miss entirely? Find the specific mechanism (aggregation vs. single-ticket analysis) that makes ticket data predictive.

**Risk & Compliance → Fraud Detection Signals**
> Decision Activator: What is the single highest-leverage technique fraud-ops teams use to cut false-positive rates without missing true positives, and what would it cost (in engineering effort) to port into a KPI-anomaly engine? Cite the exact reduction percentages found.

**Competitive & Industry → White Space & Unmet Needs**
> Pattern Disruptor: Where do real user reviews of ThoughtSpot Spotter, Power BI Analyze, and Tellius contradict their own marketing claims about "AI explains your data"? What specific gap does every competitor share?

**Sales & Revenue → Revenue by Segment/Product/Region**
> Decision Activator: What decomposition methodology (e.g., variance decomposition, Shapley attribution) should the engine default to for a "revenue dropped 8% in a region" prompt, and what's the quantified accuracy/speed tradeoff vs. simpler methods?

**Digital & E-commerce → Conversion Funnel Drop-offs**
> Pattern Disruptor: What contradictions exist between how funnel analysis tools present drop-off data and what actually causes it (payment gateway bugs vs. UX vs. pricing)? Use the casebook's Blinkit/cloud-storage RCA pattern as a lens.

**Product & Innovation → Product-Market Fit Signals**
> Strategic Horizon: What leading indicators separate AI copilots with real PMF (GitHub Copilot, narrow triage tools) from ones stuck at low adoption (general enterprise Copilot)? What's the contrarian prediction for AI-explains-your-KPI tools specifically?

**Macroeconomic & External → Technological Disruption Signals**
> Strategic Horizon: What does Gartner's 2026-2027 analytics forecast (agentic/autonomous analytics, GenAI content share) imply for the 18-month horizon of a KPI-storytelling product? What's the contrarian read on "agent drift" risk?

**People & Talent → Skills Gaps & Training Needs** *(executed — see Research Findings §7)*
> Decision Activator: Does the evidence support "augment the analyst" or "replace the analyst" as the framing for this product? Cite adoption-pattern evidence from the AI-copilot research above.
> **Answer:** Augment, still — but the Copilot Studio agent-creation surge (400K+ custom agents in Q1 FY2026) shows adoption energy shifting toward narrow embedded automation *within* an augment framing, not full replacement.

**Financial & Economic → P&L Performance** *(executed — see Research Findings §8)*
> Pattern Disruptor: What's the non-obvious risk in decomposing P&L-level metrics (revenue, margin) with an LLM-generated narrative layer, versus operational metrics? Where does causal ambiguity get worse at the financial-statement level?
> **Answer:** A 2026 fidelity audit found an LLM inverted the risk direction on 3 of 4 factors in a credit-risk narrative — its own priors overrode the actual supplied evidence. Portable fix: a post-generation verification gate (membership/direction/coverage checks) as a second gate alongside the pre-generation data-quality gate from D5.

---

## Part D — Executed research findings (real sources, quotes, stats)

### D1. Problem validation — dashboards fail at "why" (Customer & Market / Competitive & Industry)

- **ThoughtSpot:** "Dashboards are great at telling you what's happening, but the moment you ask why, you're chasing numbers across tools, digging through reports, and coming up short." [Root-Cause Analysis: How Do You Get to the 'Why' Faster](https://www.thoughtspot.com/data-trends/analytics/root-cause-analysis)
- **sranalytics.io:** **73% of BI implementations fail due to strategy/diagnostic gaps, not technology**; only **~21% of employees actively use** deployed BI tools when dashboards can't answer "why" — they revert to spreadsheets. Manufacturing example: a "gorgeous operations dashboard" confirmed delays existed but couldn't say if the cause was supply chain, equipment, or scheduling. [Why BI Tools Fail: The Strategy Gap Killing ROI](https://sranalytics.io/blog/why-bi-fails/)
- **dev.to:** Names "insufficient diagnostic capability" and "no automated anomaly detection" as 2 of 5 core dashboard failure modes. [Why Dashboards Fail](https://dev.to/amoakomensa/why-dashboards-fail-2n54)

### D2. Real competitor review evidence (Competitive & Industry — direct from G2, fetched live)

**ThoughtSpot Spotter — the closest existing analog to this case — real user quotes:**
- Positive: *"I can simply ask plain-language questions about causes that have resulted in changes in data and get insightful answers along with visual explanations"* — Syed Saad M., Software Development Manager, Mid-Market
- **The critical gap (this is your differentiation opening):** *"The experience can still require too much user interpretation... when moving from a question to a fully trusted, decision-ready insight"* — Farid V., Enterprise
- *"Their agent isn't as powerful as I would expect. It doesn't fully learn user behavior"* — Maayan B., Data Analyst, Small-Business
- *"Natural language doesn't work well. Our users found it very non-intuitive"* — Carolina A., Data Analyst, Mid-Market

**Verdict:** even the market leader in "AI explains your data" has real users saying the last mile — going from an AI answer to a *trusted, decision-ready* insight — isn't solved. This is your case's exact thesis, validated by real review data, not assumption. [G2: ThoughtSpot Reviews](https://www.g2.com/products/thoughtspot/reviews)

**Tableau/Power BI reviews:** less directly on-topic (complaints skew toward learning curve, performance, cost), but Power BI ships a real shipped feature worth analyzing in detail (below). [G2: Tableau Reviews](https://www.g2.com/products/tableau/reviews) · [G2: Power BI Reviews](https://www.g2.com/products/microsoft-power-bi/reviews)

### D3. Power BI's "Explain the increase/decrease" — a real shipped competitor feature (Technology & Data / Product & Innovation)

Full technical teardown (from Microsoft's own docs):
- **Mechanism:** ML algorithm compares a selected data point to the immediately previous one, breaks down all other columns/dimensions "before vs. after," ranks columns by size of change, and returns the top contributors.
- **Presentation:** 4 interactive views — waterfall chart (ranked contributors), scatter plot (above/below trend line), 100% stacked column (relative % shift), ribbon chart (rank-order changes over time, e.g., "Louisiana dropped from #2 to #11 contributor").
- **Hard limitations (your whitespace):** only binary before/after comparison (no multi-period trend), no predictive element, breaks on TopN filters/RLS/DirectQuery/filtered measures, **no narrative generation** (user still has to interpret 4 charts themselves), **no cross-dimensional storytelling** ("why did Q2→Q3 increase despite market decline?" is unanswerable), and silent failures (button just disables with no explanation).

**This is the single most useful artifact found** — it's a real, shipped, ML-powered "explain the change" feature from the market leader, and it stops exactly where your case's ambition starts (narrative synthesis, multi-period, cross-dimensional causal reasoning). Use it as the "here's the floor, here's our ceiling" competitive slide. [Microsoft Learn: Analyze feature](https://learn.microsoft.com/en-in/power-bi/consumer/end-user-analyze-visuals)

### D4. Signal vs. noise — technique shortlist (Technology & Data)

| Method | Mechanism | Best for | Noise-handling |
|---|---|---|---|
| CUSUM | Accumulates deviation from target mean, signals on threshold breach | Real-time monitoring | Strong at small sustained shifts, controlled false-alarm rate |
| BinSeg | Recursive divide-and-conquer changepoint search | Long series, speed | Weakest — greedy, can mistake noise for shift when changepoints cluster |
| **PELT** | Dynamic programming + pruning, exact multi-changepoint detection, ~linear time | Default production choice | Penalty term explicitly tunes overfit-vs-miss — **best citation for "how do you separate signal from noise"** |

Recommended pipeline: **STL seasonal-trend decomposition → PELT on the residual → CUSUM as a lightweight real-time layer between full re-runs.** [MetricGate: Changepoint Detection Methods](https://metricgate.com/blogs/changepoint-detection-methods/)

### D5. Data quality risk — the biggest threat to trust (Technology & Data — new this round)

This is the domain most case-solvers skip, and it's exactly the kind of "non-obvious" finding the Pattern Disruptor lens is built to surface: an AI system that *confidently* generates causal narratives is uniquely exposed to GIGO (garbage-in-garbage-out) — a dashboard that's silently wrong is bad; an AI that **narrates a confident, wrong story** about why revenue dropped is worse, because natural language reads as more authoritative than a chart. [Garbage In, Garbage Out — Wikipedia](https://en.wikipedia.org/wiki/Garbage_in,_garbage_out) · [Profisee: GIGO](https://profisee.com/blog/garbage-in-garbage-out/)

**Design implication:** the engine needs a data-quality confidence gate *before* the narrative layer — if the underlying dimension/segment data is stale, sparse, or has known join/tracking issues, the system should degrade to "I don't have reliable enough data to explain this" rather than generate a fluent-sounding wrong answer. This should be its own slide — it's the kind of judgment-under-uncertainty point that separates a winning answer from a generic one.

### D6. Fraud detection — the most mature sibling discipline for anomaly/alert design (Risk & Compliance)

Real, sourced statistics directly portable to your Detection layer's design rationale:
- **70% of analyst time** is spent investigating alerts that turn out to be legitimate (Gartner 2025).
- Industry-average false-positive rate: **90-95%**, barely improved in a decade.
- Analysts reviewing 30+ alerts/day show a **22% decline in detection accuracy** (alert fatigue is measurable, not just anecdotal).
- **67% of fraud analysts report moderate-to-severe burnout**; average tenure 2.1 years.

**What actually reduces false positives (directly reusable for your Detection/Attribution layers):**
1. AI-powered risk scoring before human review → **40-52% false-positive reduction**
2. Contextual enrichment (auto-attach behavioral baselines/history to every alert) → **59% reduction in investigation time**
3. Automated low-risk triage/auto-close below a threshold
4. Rule rationalization (retire redundant rules) → **30-40% alert volume reduction** with no loss of true positives
5. Feedback loop from investigation outcomes back into the model → **35% improvement in alert precision over 12 months**

[FluxForce: Fraud Alert Fatigue](https://www.fluxforce.ai/blog/fraud-alert-fatigue)

**Direct port to the case:** techniques #2 (contextual enrichment) and #5 (feedback loop) map almost exactly onto the case's own "Attribution layer" and "Verify" stage — cite this domain explicitly as "we borrowed alert-fatigue mitigation patterns from fraud ops, a discipline that has been solving this exact precision/recall tradeoff for over a decade."

### D7. Support tickets as a leading indicator (Customer Service & Exp.)

- University of Victoria study of IBM's support org: escalation prediction requires **aggregating ticket history per customer**, not analyzing single tickets — escalation likelihood rises as unresolved issues accumulate.
- Pre-churn signal pattern: recurring issues reworded differently, progressively longer threads, customers re-explaining context, language shifting from problem-solving to persistence.
- **Persistence, not intensity, is the strongest signal** — repeated low-severity tickets predict churn/problems better than one high-severity escalation.
- **The metrics gap:** teams can hit SLA/resolution-time targets while churn quietly rises, because standard support KPIs measure throughput, not whether problems actually resolve. [Unwrap.ai: What Support Tickets Reveal Before Churn](https://www.unwrap.ai/post/what-support-tickets-reveal-before-customers-churn)

**Design implication:** your unstructured-data ingestion shouldn't treat each ticket as an independent signal — it should aggregate at the customer/account/cohort level over time, matching exactly the case's requirement to fuse unstructured evidence with structured metric trends rather than bolt on sentiment analysis as an afterthought.

### D8. Enterprise AI adoption — the contrarian read (Product & Innovation / Strategic Horizon)

Sharpest strategic-horizon finding of this round: Microsoft 365 Copilot's **3.3% penetration after 18 months** isn't a slow-adoption-cycle story — the "Jobs to Be Done" analysis argues it's a **structural mismatch**. Microsoft built for "activity acceleration" (draft faster); enterprises actually needed help "making decisions with incomplete information," "translating technical analysis for non-technical audiences," and "synthesizing conflicting data into coherent pictures" — which is almost verbatim your case's job description.

High-adoption AI tools share three traits: **narrow, repetitive, measurable** tasks with visible/quantifiable alternative costs (GitHub Copilot ~40%+ developer adoption; customer-service triage; legal document review).

**Contrarian prediction for your deck:** a horizontal "AI explains everything" positioning risks the same fate as Copilot's low penetration. The winning framing is narrow and workflow-embedded — e.g., "explains regional revenue anomalies for retail ops leads," not "explains any KPI for anyone" — until trust is earned. [Copilot at 3%: Enterprise AI Is Being Hired for the Wrong Job](https://www.vaasblock.com/research/enterprise-ai-adoption-copilot-jobs-to-be-done-2026/)

### D9. Market trajectory (Strategic Horizon / Macroeconomic & External)

- Gartner: **75% of new analytics content** will be GenAI-contextualized by 2027; augmented analytics platforms will mature into "autonomous analytics" managing **20% of business processes** by 2027.
- Over **50% of surveyed analytics/AI leaders** already use AI for automated insights + natural-language query today (2025-2026).
- Gartner's named risk: **"agent drift"** — autonomous systems gradually deviating from intended outcomes — with "guardian agents" recommended as a monitoring layer. [Gartner: 75% of Analytics Content GenAI by 2027](https://www.gartner.com/en/newsroom/press-releases/2025-06-18-gartner-predicts-75-percent-of-analytics-content-to-use-genai-for-enhanced-contextual-intelligence-by-2027)

**Design implication:** "agent drift" is a ready-made citation for why your ambiguity-handling layer and human-in-the-loop routing aren't optional nice-to-haves — they're the "guardian agent" pattern Gartner is already telling the market to expect.

### D10. Causal attribution technique (already in Stage 1, reinforced)

- Tellius's shipped approach: variance decomposition across dimensional hierarchies + Shapley-value driver ranking (rank ~8 factors explaining 80% of variance) + dimensional traversal with chi-squared/t-test significance testing at each node. [Tellius: AI-Powered Root Cause Analysis](https://www.tellius.com/resources/blog/ai-powered-root-cause-analysis-from-what-happened-to-why-in-60-seconds)
- Academic backing: causal graphs/structural models, not bare correlation, are the consensus requirement for correlation→action; a 2025 paper specifically proposes causal RCA using **multi-modal (structured + unstructured) data**, directly validating the case's data-fusion requirement. [ScienceDirect: Causal inference-based RCA using multi-modal data](https://www.sciencedirect.com/science/article/abs/pii/S0951832025007203)

---

## Part E — Consolidated answer update (what changes vs. the original roadmap)

1. **Lead your problem slide with the ThoughtSpot review quotes (D2)**, not a generic pain-point — real users of the market leader say the "trusted, decision-ready insight" gap is still open. That's a stronger opening than an invented scenario.
2. **Use Power BI's Analyze feature (D3) as your explicit "floor" competitive slide** — you're not inventing a category, you're extending a real, limited, already-shipped feature into narrative, multi-period, cross-dimensional territory.
3. **Add a Data Quality Gate as an explicit fourth layer** (before Detect), sourced from D5 — this is the finding most competing teams will miss.
4. **Cite fraud-ops false-positive-reduction numbers (D6)** when defending your Detection layer's design — gives you real percentages instead of hand-waving about "reducing noise."
5. **Reframe unstructured-data ingestion as customer/cohort-level aggregation, not per-ticket sentiment (D7)** — more sophisticated and defensible under questioning.
6. **Use the Copilot "wrong job" contrarian argument (D8) to justify a narrow initial scope** in your recommendation — "start with regional revenue anomalies for ops leads" beats "explains any KPI," and shows judgment under the CIRCLES "evaluate trade-offs" step.
7. **Cite Gartner's "agent drift" / "guardian agents" (D9)** as external validation that your human-in-the-loop ambiguity design isn't overcaution — it's where the market is already heading.

---

## Part F — Apify / real scraped data status

Apify actor calls failed again this session (`User was not found or authentication token is not valid`), even after a new API key was reportedly attached to the Apify connector. The key isn't reaching this session — check Settings → Connectors → Apify in the desktop app and confirm the token saved there (a token pasted only into chat won't authenticate the connector). Everything in Part D/§7-8 that reads like "scraped reviews" was pulled by fetching real, public pages directly (verbatim quotes, not simulated) — genuine, just retrieved one page at a time rather than at Apify's scale. Reddit still blocks both direct fetch (403) and web search indexing.

Once the connector actually authenticates, tell me and I'll run G2/Capterra review-scraper actors and a Reddit-search actor to pull structured datasets (hundreds of reviews/threads) instead of one-off fetches — this is the main remaining gap in the research phase.



---



# 3. Research Findings (full)

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\BusinessIntelligence_ai_Research_Findings.md`*

---

# Research Findings — BusinessIntelligence.ai (KPI Storytelling Engine)

*Compiled from web research standing in for Apify + Answer the Public + Elicit AI (Apify actor calls failed in this session — no APIFY_TOKEN connected; see note at bottom).*

## 1. Problem validation — dashboards fail at "why," not "what"

Consistent, independently-sourced pattern across every source checked:

- **ThoughtSpot:** "Dashboards are great at telling you what's happening, but the moment you ask why, you're chasing numbers across tools, digging through reports, and coming up short." Analysts spend hours pulling data from disparate systems and guessing at causes rather than confirming them. [Root-Cause Analysis: How Do You Get to the 'Why' Faster](https://www.thoughtspot.com/data-trends/analytics/root-cause-analysis)
- **sranalytics.io:** Cites a manufacturing example — "a gorgeous operations dashboard" that could confirm delays existed but couldn't say whether the cause was supply chain, equipment, or scheduling. Claims **73% of BI implementations fail due to strategy/diagnostic gaps, not technology**, and that only ~21% of employees actively use deployed BI tools when dashboards can't answer the "why" — they revert to spreadsheets and manual investigation. [Why BI Tools Fail: The Strategy Gap Killing ROI](https://sranalytics.io/blog/why-bi-fails/)
- **dev.to (Why Dashboards Fail):** Names "insufficient diagnostic capability" and "no automated anomaly detection" as two of five core failure modes — static snapshots without drill-down or correlation analysis leave users stuck at "what happened." [Why Dashboards Fail](https://dev.to/amoakomensa/why-dashboards-fail-2n54)

**Takeaway for the deck:** you don't need to argue the problem is real — three independent sources already do. Lead with the 73%-strategy-gap / 21%-adoption stats as your "why now."

## 2. What "good" already looks like — competitive/analogous solutions

- **ThoughtSpot Spotter / natural-language querying:** lets users ask "why" directly, pairs automated anomaly detection with cross-metric correlation, aims for "insight to action in seconds."
- **Tellius** (closest analog to the case prompt) uses three concrete techniques worth citing directly:
  1. **Variance decomposition** — splits a metric change (e.g., "-$12M revenue") across dimensional hierarchies (product, segment, channel, geography).
  2. **Key driver ranking via Shapley values** — instead of showing 50 dimensions, ranks the ~8 factors that explain 80% of the variance.
  3. **Dimensional traversal** — auto-explores hierarchies (geography→territory→account) testing statistical significance at each node (chi-squared/t-tests) to reject noise.
  Output is delivered as a confidence-scored, ranked narrative in ~60 seconds, exported as an "executive-ready" artifact. [Tellius: AI-Powered Root Cause Analysis](https://www.tellius.com/resources/blog/ai-powered-root-cause-analysis-from-what-happened-to-why-in-60-seconds)
- **Arria NLG / Narrative Science (Quill):** established players in natural-language generation *specifically for BI narratives* — good precedent that "turn metrics into a written narrative" is a solved sub-problem; your differentiation should be root-cause attribution + ambiguity handling, not narrative generation itself. [Arria NLG for BI](https://www.arria.com/blog/intelligent-narratives-4-ways-nlg-extracts-the-value-from-your-data/)
- **Zenlytic / Pecan AI:** newer "AI data analyst" agents — worth a one-line competitive mention that the space is heating up (2026), which strengthens urgency without undermining originality (your differentiator is explicitly the ambiguity-handling + evidence-ranking layer, which none of these headline).

**Takeaway:** cite Tellius's three techniques by name in your CIRCLES "List Solutions" step — it upgrades "we'll use AI" into a credible, specific mechanism, and shows you know the landscape.

## 3. Signal vs. noise — technique shortlist (Elicit-equivalent academic grounding)

From MetricGate's changepoint methods breakdown and supporting anomaly-detection literature:

| Method | What it does | Best for | Noise-handling |
|---|---|---|---|
| **CUSUM** | Accumulates deviation from a target mean, signals when cumulative sum crosses a threshold | Real-time monitoring, detecting one sustained shift as data streams in | Strong at catching small sustained shifts while controlling false alarms via the decision boundary |
| **Binary Segmentation (BinSeg)** | Recursive divide-and-conquer changepoint search | Very long series where speed matters (O(n log n)) | Weakest of the three — greedy, can cascade errors on closely-spaced changepoints (i.e., can mistake noise for a shift) |
| **PELT** | Dynamic programming + pruning, finds multiple changepoints exactly in ~linear time | Default recommendation for most production use | Penalty term explicitly tunes overfit-vs-miss tradeoff (BIC/modified BIC) — this is your best citation for "how do you separate signal from noise" |

Recommendation for the case: **use STL-style seasonal-trend decomposition to strip seasonality first, then run PELT on the residual** to flag genuine regime shifts, with CUSUM as a lightweight real-time layer between full PELT re-runs. [MetricGate: Changepoint Detection Methods](https://metricgate.com/blogs/changepoint-detection-methods/)

## 4. Correlation → actionable causation

- Broad academic consensus (FasterCapital, LatentView, ScienceDirect causal-RCA framework) frames the move from correlation to action as requiring **causal graphs / structural models**, not just statistical correlation — i.e., you need a hypothesized mechanism (a DAG of "campaign change → traffic → conversion → revenue") that the data either supports or contradicts, not just "these two lines moved together." [Causal Analysis Guide: Moving from Correlation to Causation](https://www.latentview.com/blog/a-comprehensive-guide-to-causal-analysis/)
- A 2025 ScienceDirect paper proposes root-cause analysis via causal inference specifically using **multi-modal data** (i.e., structured + unstructured combined) in complex systems — directly validates the case's requirement to fuse both data types rather than treating them as separate features. [A causal inference-based RCA framework using multi-modal data](https://www.sciencedirect.com/science/article/abs/pii/S0951832025007203)

**Takeaway:** frame your Attribution layer as testing a small set of pre-defined causal hypotheses (pricing, funnel break, competitor action, macro/seasonal) against both structured evidence (the metric decomposition) and unstructured evidence (support tickets, news, campaign logs) — evidence convergence across both data types is what upgrades a correlation into something a leader can act on.

## 5. Handling genuine ambiguity — human-in-the-loop framing

- Literature on trust calibration is consistent: **presenting a confidence score alongside an explanation improves trust calibration more than either accuracy or explanation alone** — users trust appropriately (not over- or under-trust) when confidence is explicit. [Effect of confidence and explanation on accuracy and trust calibration](https://www.researchgate.net/publication/338841931_Effect_of_confidence_and_explanation_on_accuracy_and_trust_calibration_in_AI-assisted_decision_making)
- "AI systems that know when they don't know" is an active design pattern — the recommendation is to **abstain or downgrade to multiple ranked hypotheses** rather than force a single confident-sounding answer when evidence is thin. [How to Design AI Systems That Know When They Don't Know](https://sakaradigital.com/blog/anchored-knowledge-ai-uncertainty/)
- Human-in-the-loop is positioned not as a fallback but as a **quality/oversight mechanism baked into the workflow** — reinforces the case answer that ambiguous cases should route to an analyst with a pre-built evidence packet rather than being silently guessed at. [Human-in-the-Loop: How Oversight Drives AI Quality](https://productschool.com/blog/artificial-intelligence/human-in-the-loop-ai)

**Takeaway:** this is your strongest differentiation point for the "Think about" ambiguity question — explicitly design for the system to say "I'm not sure, here are the top 2 hypotheses and the evidence for each" rather than always producing one polished-sounding narrative.

## 7. People & Talent — augment vs. replace framing (executed this round)

- Current adoption evidence still favors **augmentation over replacement** as the honest framing: early-Copilot-user surveys show 73% completing tasks faster and 85% reaching a good first draft faster, but role elimination isn't supported by hiring trends — AI compresses the *drafting/documentation* portion of analyst work, not the judgment portion. [Microsoft Copilot Statistics 2026](https://www.getpanto.ai/blog/microsoft-copilot-statistics)
- **Counter-signal worth flagging in the deck:** in Q1 FY2026, ~160,000 organizations created 400,000+ custom agents in Copilot Studio in three months — a sign enterprise appetite is quietly shifting toward *automation* (agents doing the task) rather than pure *augmentation* (copiloting a human), even while vendor messaging still says "augment." [The Latest on Microsoft's AI Strategy](https://www.useluminix.com/reports/company-overviews/the-latest-on-microsoft-s-ai-strategy-spring-2026/source/3)
- **Verdict for the case:** stick with "augment the analyst," consistent with D8's Copilot "wrong job" finding — but note the agent-creation surge as evidence that *narrow, embedded automation within* an augment framing (e.g., auto-drafting the evidence packet, not auto-deciding) is where real adoption energy is heading. This sharpens the earlier recommendation rather than contradicting it.

## 8. Financial & Economic — narrative-layer risk at the P&L level (executed this round)

- A 2026 arXiv fidelity audit of LLM-generated credit-risk narratives found the model **inverted the risk direction on 3 of 4 factors** it was asked to explain, even under constrained prompting and greedy decoding — controls the literature previously considered sufficient. The narrative asserted "age, income, and venture intent increase risk" when the underlying SHAP/LIME attributions scored all three as risk-*reducing*, and it omitted the actual dominant driver (loan amount) while naming a feature that was never supplied. [Accurate Ensembles, Fragile Narratives (arXiv 2608.08126)](https://arxiv.org/html/2608.08126)
- **Root cause:** the model's own priors ("high income = good credit") overrode the supplied evidence when the evidence contradicted them — i.e., an LLM narrating a financial metric doesn't just risk misreading noisy data (D5), it can silently substitute its training-time priors for the actual attribution it was given.
- **Mitigation the paper prescribes — directly portable to your Detect→Explain layer:** a post-generation verification pass checking three conditions before the narrative ships — (1) **membership**: every named driver must appear in the supplied evidence set, (2) **direction**: asserted direction must match the attribution's sign, (3) **coverage**: the largest-magnitude driver must be mentioned. Direct quote: *"A narrative layer in a regulated setting should run them and fall back to a deterministic template when they fail."*
- **Design implication — this upgrades D5 into a two-gate architecture:** a **data-quality gate** before generation (is the underlying data reliable enough to explain at all?) plus a **narrative-fidelity gate** after generation (does the generated text actually match what the stats layer found?). This is a stronger, more specific answer to the ambiguity/trust question than D5 alone, and it's a distinct citation — use both.

## 9. Real scraped review corpus (Apify, executed manually via console — ~385 records, verified)

The Apify connector never authenticated in-session, so you ran the actors directly in the Apify Console and handed back the exported datasets. I spot-checked the raw `.xlsx` exports (not just the summary) against real cell contents — headers, reviewer job titles, star ratings, and quote text all check out as genuine, not fabricated. One correction to the summary you were given: the strongest Tellius quote below is real but I found an additional sentence in that same review that's arguably the single best piece of evidence in the whole corpus for this case (see 9.3).

**Corpus:** G2 — ThoughtSpot (100), Tableau (100), Sisense (100), Tellius (14, all it has); Capterra — Tableau ≤3★ (40); Reddit — r/BusinessIntelligence (30 posts/comments). G2 Power BI and Capterra ThoughtSpot returned 0 (product slugs the actor couldn't resolve / too few low-star reviews) — not yet covered by real scraped data.

### 9.1 Theme: no semantic layer = no "why" when the business logic changes
> *"It is cumbersome to manage when the organization grows and the business is siloed. Due to the lack of a semantic layer, it frequently results in inconsistent data reported and when the business logic changes, it becomes a huge burden to keep existing dashboards updated."*
> — Analytics Engineer, Tableau, Capterra (3★) — **verified verbatim**

This is a sharper, more technical version of D1's "dashboards can't answer why" — it names the specific mechanism (no semantic layer) rather than just describing the symptom. Use this to justify why your engine needs its own metric-definition layer, not just a narrative layer bolted onto existing dashboards.

### 9.2 Theme: even NLQ-first tools still break on nuanced questions
> *"Natural language queries don't always interpret intent correctly for more nuanced or domain-specific questions, sometimes requiring rephrasing to get the right result."*
> — Tellius user, G2 (4★) — **verified verbatim**, from the "cons" half of a review titled "Tellius Makes Team Data Analysis Easy with Natural Language Queries"

### 9.3 The single best-sourced quote in the corpus — correlation vs. causation, from a live user, unprompted
Same Tellius review as 9.2, next sentence — **not in the original summary, found on verification**:
> *"...some of the automated insights, while useful, occasionally surface correlations that aren't actually meaningful without manual review to confirm relevance."*
> — Tellius user, G2 (4★) — **verified verbatim**

This is real evidence, from a paying customer of the closest existing competitor, that the exact problem your case's "Think about" section names — moving from correlation to something actionable — is an *unsolved, currently-experienced* pain point, not a hypothetical. Lead your Attribution-layer slide with this quote before D10's academic citation; it's stronger because it's a user, not a paper.

### 9.4 Theme: root cause is a data-lineage problem, not just a stats problem (Reddit, r/BusinessIntelligence — verified)
> *"This is missing what I think is one of the most common reasons: schema or logic changes to existing data... Sales Ops team deletes columns in Salesforce. Marketing team changes definition of the Paid Search lead source bucket."* — u/Nateorade
> *"...the biggest problem is a disconnect between the data users and the data producers... the person who creates the problem doesn't even know (or care) how their response might affect things downstream."* — u/gordanfreman
> *"Garbage in garbage out. We've built multiple systems on the backend to capture bad data from the front end applications."* — anonymous

All three verified verbatim against the raw thread ("Data quality issues root causes"). **This directly reinforces D5's data-quality-gate finding with real practitioner testimony** — the root cause of a KPI move is frequently an upstream schema/definition change nobody logged, not a market event. Your Attribution layer's "internal factors" bucket should explicitly include a changelog/schema-diff check, not just pricing/campaign/product changes.

### 9.5 Theme: cost gates who gets to ask "why" at all (Tableau, G2 + Capterra — verified)
> *"user license cost is expensive compared to features"* — analyst, Capterra (3★)
> *"More than one license is too expensive"* — Capterra reviewer (3★, paraphrase of a longer real quote about single-license constraints)

Supports the case's "narrow, embedded" framing (D8) from a different angle: if the explanation tool is gated behind an expensive analyst-only license, the business leader who needs the "why" still can't get it directly — reinforces routing ambiguous/complex cases to a human rather than assuming universal self-serve access.

### 9.6 Gaps still open
- **Power BI G2 reviews**: actor couldn't resolve the slug — get these manually if you want direct G2 evidence on Power BI specifically (D3's Power BI evidence still stands, sourced from Microsoft's own docs instead).
- **ThoughtSpot Capterra**: too few ≤3★ reviews exist there to be useful.
- Full raw exports remain in your Downloads folder (`dataset_g2-scraper_*.xlsx`, `dataset_capterra-reviews-scraper_*.xlsx`, `dataset_reddit-scraper-lite_*.xlsx`) if you want to pull additional quotes yourself.

## 11. Deepened academic grounding (2025-2026 papers, Elicit-equivalent — Elicit connector itself hit an API-access paywall, so this substitutes WebSearch/WebFetch on arXiv, same as D4/D9/D10/§8)

Four searches, one per unresolved academic question from Part C. All four papers below are real, dated, and linkable — verified by fetching the actual abstract/body, not just search snippets.

### 11.1 Signal vs. noise — LLM-augmented changepoint detection is now an active research line, not just classical stats
- **LLM-Augmented Changepoint Detection** (Lukassen et al., 2026) pairs an *ensemble* of ten classical changepoint algorithms (voting to reduce any single method's blind spots) with an LLM explanation layer that links each detected changepoint to a plausible real-world cause, optionally grounded via RAG over your own documents. [arXiv:2601.02957](https://arxiv.org/abs/2601.02957)
  - **Design implication:** validates a two-stage architecture — ensemble/statistical layer decides *whether* something changed, LLM layer only narrates *why* — rather than asking one model to do both. This is a stronger citation than D4 alone because it's explicitly built for "detect, then explain," matching your case's exact structure.
- **CALM** (2025) uses an LLM-as-judge to classify each flagged anomaly as a sustained shift ("KEEP") vs. a transient blip ("REMOVE") by giving it before/after data plus the mean/stdev shift — e.g., CPU usage moving from ~30% to a stable ~61% is classified as real. On the TSB-UAD benchmark, this improved detection AUC by up to **+0.351** on the best dataset, though the authors flag that the LLM judge is less reliable than a formal statistical guarantee and can degrade results on some datasets. [arXiv:2508.21273](https://arxiv.org/html/2508.21273v1)
  - **Honest caveat worth including in your trade-offs slide:** this is a real, named risk of LLM-in-the-loop anomaly judging — it's not universally an improvement, which supports keeping the statistical layer (PELT/CUSUM) as the source of truth and the LLM strictly for narration, not classification.

### 11.2 Correlation → action — evidence-grounded agentic RCA, with hard accuracy numbers
- **AgentRCA** (2026) diagnoses faults using a "digital twin" trained only on normal-operation data (no labeled failures needed) plus an LLM agent that inspects residuals, directional shifts, and correlation changes, maintaining a ranked hypothesis table. Tested on two industrial benchmarks: **87.6% Top-1 accuracy** zero-shot on a 17-variable facility (vs. 94.5-99.6% for supervised models that needed 20+ labeled failure examples per class), and **40.0% Top-1 / 61.5% Top-2** on a harder 52-variable, 21-fault-type process (vs. 78.5-85.7% supervised, which needed ~40 labeled examples per fault type). [arXiv:2607.22385](https://arxiv.org/html/2607.22385v1)
  - **Direct port to the case:** this is the strongest available citation for why your Attribution layer should present a *ranked hypothesis table with evidence*, not a single answer — it's a proven pattern, and the accuracy gap vs. supervised models is exactly the "no labeled training data for every possible KPI-drop cause" situation your engine will actually be in. Cite the Top-2 accuracy jump (40%→61.5%) as justification for showing 2-3 ranked hypotheses instead of one.

### 11.3 Ambiguity handling — reasoning models are measurably *worse* at knowing when to stay quiet
- **AbstentionBench** (Kirichenko, Ibrahim, Chaudhuri, Bell — 2025) is a large benchmark testing whether frontier LLMs correctly decline to answer unanswerable questions (missing info, false premises, subjective questions). Headline finding, confirmed in the paper's own abstract: **reasoning-tuned models abstain 24% worse on average** than their non-reasoning counterparts — the very capability that makes a model good at multi-step causal reasoning (exactly what your Attribution layer needs) actively works against it admitting uncertainty. [arXiv:2506.09038](https://arxiv.org/pdf/2506.09038)
  - **This is the sharpest available citation for the case's ambiguity question.** It reframes "the system should admit uncertainty" from a nice-to-have UX choice into a known, measured *failure mode of the exact model class you'd use* — meaning the abstention/multi-hypothesis behavior has to be engineered as an explicit guardrail (e.g., the fidelity-check gate from §8), not assumed to emerge naturally from a smarter model.

### 11.4 Consolidated addition to Part E (design implications)
Combining 11.1-11.3: the architecture now has three defensible gates, each backed by a distinct paper — (1) ensemble-statistical detection before any LLM sees the data (11.1), (2) a ranked, evidenced hypothesis table instead of one answer (11.2), (3) an explicit abstention/verification layer because reasoning capability and honest uncertainty are shown to trade off against each other, not reinforce each other (11.3 + §8's fidelity-check gate). This is a materially stronger "so what" for your architecture slide than citing PELT/CUSUM and Tellius alone.

## 13. Elicit AI — proper peer-reviewed grounding (executed by you directly in Elicit, self-critiqued — this supersedes §11's WebSearch approximation in rigor)

This round is materially stronger than §4/§11: each answer went through Elicit's own independent-review pass, which caught real errors in the first draft (noted below). Treat these as your primary citations; §4/§11 remain useful as secondary/supporting sources.

### 13.1 Signal vs. noise — corrected and upgraded from §4/D4
The properly-sourced taxonomy splits methods along **change/cost model × search algorithm × penalty** — not just "offline vs. online" as D4/§11.1 had it. Two corrections to what's already in the doc, both caught by Elicit's own review pass:
- **CUSUM is for abrupt, persistent mean shifts — not gradual drift.** The doc's earlier framing ("gradual deterioration in conversion") was wrong; use CUSUM for a sudden step-change (e.g., a pricing change hitting overnight), and a different method (Bayesian online changepoint detection, which tracks "run length" probabilistically) for slow drift.
- **PELT deserves to be named explicitly** as the standard exact penalized-optimization method — D4 already used it as the production default, this confirms that choice against the canonical literature (change/cost model + search + penalty framework), not just informally.
- **New, highly citable design rule:** validate every statistical changepoint against a **minimum business-effect threshold** (e.g., "a sustained shift of ≥2 percentage points or revenue impact above $X"), not a statistical threshold alone — directly answers the case's "how do you separate meaningful change from noise" question with an actual operating rule, not just an algorithm name. [Aminikhanghahi & Cook, 2016, *A Survey of Methods for Time Series Change Point Detection*, Knowledge and Information Systems; Wang et al., 2013, arXiv]
- Also confirmed: **first remove/model trend and seasonality, then detect breaks in the residual** — matches the STL→PELT pipeline already recommended in §4, now with a named source for the "seasonality-first" step. [Li et al., 2019, *Automating Data Monitoring: Detecting Structural Breaks... Using Bayesian Minimum Description Length*, arXiv]

### 13.2 Correlation → action — the field's own honesty check on itself
This is the most important corrective in the whole batch: the literature survey explicitly states **"prediction is not intervention"** — a model can rank candidate causes well on benchmarks while never proving that acting on the top-ranked cause would actually fix the problem. Key line: *"benchmark and simulated gains do not yet establish that acting on a ranked cause will prevent a real-world failure."* [Multimodal causal RCA survey, 2026, drawing on Kong et al. 2026 and Trilla et al. 2024, arXiv]
- **Practical architecture the survey recommends** (directly reusable as your Attribution layer's internal structure): (1) define the failure/intervention question precisely, (2) build a domain causal graph from temporal ordering and known mechanisms — don't just infer a graph from fused features, (3) keep each data modality's structure separate before fusing, (4) explicitly model *why* data is missing (a support-ticket spike being under-logged is itself a signal, not noise to impute away), (5) validate top candidate causes with something closer to a counterfactual check, not just an attribution score.
- **The single sharpest line to put on your Attribution slide:** *"Separate explanation from causation. SHAP, attention, saliency, and feature importance can prioritize signals, but they do not by themselves establish that changing a feature would change the outcome."* This is exactly the discipline your case's "correlation → action" question is testing for, and it's a stronger, more precise answer than D10's citation alone.

### 13.3 Confidence & trust — the strongest single statistic to add to your deck
A 2026 within-subjects study (184 participants) found **well-calibrated confidence improved decision accuracy by ~20%, while miscalibrated confidence produced only ~2% gain and increased automation bias/conservatism.** [Fregosi et al., 2026, AAAI] This is a much sharper number than the "trust calibration" citation already in §D-ambiguity — use this one as the headline stat instead.
- **Important nuance that corrects an oversimplification risk:** confidence displays are not universally good — one study found confidence scores improved *trust calibration* without improving *joint decision accuracy*, because the human couldn't contribute knowledge that complemented the model's specific error pattern. [Zhang et al., 2020, FAT*] The design implication: don't ship a bare confidence percentage and assume it helps — test it against a no-display baseline on your actual task, and present uncertainty with reliability context (e.g., "this type of call is right 80% of the time in similar cases"), not a raw number.
- **The core design principle, quotable as-is:** *"Do not optimize for making users trust the AI; optimize for helping them know when to trust it."*

### 13.4 Ambiguity handling / human escalation — the best architectural upgrade in this whole research phase
This is the standout finding. The roadmap's current design ("route ambiguous cases to a human when confidence is low") is a **naive threshold rule** — Elicit's own review pass caught this and corrected it to something much stronger: **"learning to defer."**
- **Selective prediction** (what the doc had) asks: *is the model confident enough to answer?* **Learning to defer** asks the better question: ***who* is more likely to be right on this specific case — the model or the human — and is the review worth its cost?** [Mozannar & Sontag, 2020, ICML] Model uncertainty and human advantage are not the same thing — a model can be uncertain on a case a human also finds hard (escalating gains nothing), or confident on a case with a known systematic blind spot (should escalate despite high confidence).
- **The decision rule to put directly in your architecture slide:**
  > automate if `expected_loss(model)` < `expected_loss(human) + review_cost` — else defer, subject to reviewer capacity.
  This reframes your Verify/human-in-the-loop layer from "if confidence < threshold, escalate" (generic, any team would say this) into a cost-sensitive, capacity-aware routing policy backed by real ICML/IJCAI work — a materially more sophisticated answer to "what does the system do under ambiguity" than most competing case answers will give.
- **Supporting mechanism, also real and citable:** conformal prediction sets (showing the top 2-3 plausible root causes with a coverage guarantee, not just one) **measurably improved human decision accuracy** in a preregistered randomized study — direct validation of the "present top 2-3 competing hypotheses" design already in the roadmap. [Cresswell et al., 2024, ICML]
- **Operational metrics to name when defending this layer under case-competition questioning:** coverage (% handled automatically), selective risk (error rate on automated cases), deferral rate/reviewer workload, human-assisted accuracy (after seeing the model's output), and drift monitoring over time — this list alone signals more design maturity than most competing teams will show.

## 14. Answer the Public — verified customer/AI-search language (executed by you; real exports, spot-checked)

Your exports came from ATP's AI-prompt-cloud feature (ChatGPT/Gemini/Google/Bing "what people actually ask"), not the classic question-wheel — even more useful, since it's literally the phrasing people type into AI assistants for this exact problem.

**Seed: "explain KPI drop"** — real prompts logged: *"What are common reasons for a KPI drop in digital marketing campaigns?"*, *"How to analyze a KPI drop in e-commerce sales dashboards?"*, *"How to recover from a sudden KPI drop in customer engagement metrics?"* — note the pattern: people ask for **cause + recovery action in the same breath**, not cause alone. Your engine's output should always pair the explanation with a next step, never explanation only — reinforces the case's own "recommends next steps" requirement as something users demand by default, not an add-on.

**Seed: "why did revenue drop"** — real prompts: *"Why did revenue drop for major e-commerce platforms in India?"*, *"How to diagnose a sudden drop in sales revenue?"*, *"What are the primary causes of declining business income?"* — Gemini's results skew more commercial ("recommended software for sales analytics and forecasting"), confirming there's active tool-shopping intent behind this question, not just curiosity — useful market-sizing evidence for your opening slide.

**Seed: "dashboard doesn't explain why"** — the most directly on-target results in the whole corpus: *"Why does my analytics dashboard not explain the data trends clearly?"*, *"Best software for dashboards that explain why metrics change over time?"*, *"Which dashboard tools offer clear explanations for data anomalies?"*, and — the single best-matching real query found in this entire research phase — *"How to get root cause explanations from business intelligence dashboards?"* (Gemini). This is close to a verbatim restatement of your case prompt, coming from real AI-search logs, not an invented scenario. Use it to open the problem slide.

## 15. Note on tooling gap (updated)

All four original tooling gaps are now closed — every tool in the roadmap (Apify, Answer the Public, Elicit AI) has produced real, verified output, either through this session's connectors or run manually and handed back:

- **Apify**: connector never authenticated in-chat; you ran the actors manually via the Apify Console. Real datasets incorporated in §9 (~385 records, spot-checked against raw cells).
- **Answer the Public**: connector wasn't available in-chat; you ran it manually and exported the AI-prompt-cloud data. Real queries incorporated in §14, spot-checked against raw cells.
- **Elicit AI**: the connector itself authenticated but was blocked by an `api_access_denied` plan-tier gate; you ran the four research questions manually in Elicit's own UI instead, including its independent-review self-critique pass. This is now the strongest-sourced section in the whole document (§13) — properly peer-reviewed, with citation-level corrections already applied.

The research phase (Stage 1 of the roadmap) is essentially complete: problem validation, competitive teardown, real scraped review evidence, real customer-language evidence, and peer-reviewed technique grounding for both "Think about" questions are all in place. Next per the roadmap is Stage 2 — formal CIRCLES + RCA framing — which can now draw on all of this rather than generic assumptions.



---



# 4. CIRCLES + RCA Framing

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\BusinessIntelligence_ai_CIRCLES_RCA_Framing.md`*

---

# CIRCLES + RCA Framing — BusinessIntelligence.ai (KPI Storytelling Engine)
*Stage 2 of the roadmap. Every non-obvious claim below is tagged with the research-doc section it's grounded in — cite those, not this file, in your deck appendix.*

---

## C — Comprehend the Situation

**Clarifying questions to ask the interviewer/judge up front** (per the casebook's own pattern — Blinkit/Uber/cloud-storage cases all open this way):
- Is this for a specific persona, or should the design generalize? (We'll prioritize below.)
- Real-time streaming or scheduled/batch?
- What's already connected — a warehouse only, or warehouse + CRM + support desk + news feed?
- What counts as "unstructured" here?

**Assumed scope** (state this explicitly, then move on — don't over-clarify in a design case):
Mid-size B2B enterprise. Connected to a data warehouse + CRM + support desk. Used by non-technical business leaders, with an analyst team as the existing (manual) fallback. Both real-time alerting and on-demand "explain this" queries in scope.

---

## I — Identify the Customer

Three segments, same as the roadmap, now with evidence behind the prioritization:

| Segment | Role | Evidence |
|---|---|---|
| **Business leader** (primary) | Consumes the explanation, wants a defensible narrative + action | Real Gemini/ChatGPT query logs show people asking "how to get root cause explanations from BI dashboards" and "how to recover from a KPI drop" *in the same breath* — action-seeking, not curiosity (research doc §14) |
| **Analyst** (secondary — ally, not replaced) | Currently does this manually; becomes the QA/escalation layer | Adoption evidence favors augmentation, not replacement (§7) — Copilot Studio's agent-creation surge shows the winning shape is narrow automation *within* an augment frame |
| **Data/BI team** (tertiary) | Owns pipes, cares about trust/governance | Real Reddit thread: root causes are usually **schema/definition changes nobody logged** — Sales Ops deleting a Salesforce column, Marketing redefining a lead bucket (§9.4) — this segment is where that gets caught |

**Prioritize the business leader.** They're the one losing days waiting on an analyst — that's the actual time-to-decision problem, evidenced independently by three sources (ThoughtSpot, sranalytics.io's 73%-strategy-gap stat, dev.to) in §1.

---

## R — Report the Customer's Needs

Not "a dashboard." The underlying need is **a defensible narrative delivered fast enough to act on**, not more data. Real evidence this is underserved even by category leaders:

> *"...automated insights, while useful, occasionally surface correlations that aren't actually meaningful without manual review to confirm relevance."*
> — real Tellius user, G2, on the closest existing competitor product (§9.3)

> *"The experience can still require too much user interpretation... when moving from a question to a fully trusted, decision-ready insight"*
> — real ThoughtSpot user, G2 (§D2 in the master dossier)

So the need, precisely: **what changed, why (with evidence strength), how confident are we, and what should I do next** — in that order, every time.

---

## C — Cut Through Prioritization

Diagnostic funnel: **Detect → Explain → Attribute → Recommend → Verify**

- **MVP: Detect + Explain.** This is where "signal vs. noise" lives — the harder and more differentiating of the two "think about" questions.
- **V2: Attribute + Recommend.**
- **Present from day one, even if thin: Verify.** *(Design judgment, not directly sourced — flag this as inference if a judge presses on it.)* The reasoning: a feedback loop is architecturally cheap to stub early (log resolved cases) and expensive to retrofit later (retrofitting means reconstructing historical resolution data you never captured). What *is* sourced: trustworthy calibration compounds in value over time, since a real 184-participant study found well-calibrated confidence lifts decision accuracy ~20% versus ~2% for a static, uncalibrated number (§13.3) — the Verify loop is what lets the confidence layer actually become well-calibrated rather than staying a fixed guess.

---

## L — List Solutions *(RCA framework nested here — this is the core of the answer)*

### 1. Detection layer — signal vs. noise

- **Pipeline:** STL-style seasonal/trend decomposition → **PELT** (exact penalized changepoint detection) on the residual → **CUSUM** as a lightweight real-time layer between full PELT re-runs; **Bayesian online changepoint detection** for metrics with slow drift rather than abrupt shifts. *(Correction already applied: CUSUM is for abrupt, persistent shifts — not gradual drift, which needs the Bayesian online method instead. §13.1)*
- **Don't flag on statistical significance alone.** Pair every statistical changepoint with a **minimum business-effect threshold** — e.g., "sustained shift ≥2 percentage points, or revenue impact above $X" — sourced directly from the changepoint literature's own warning that a "statistically detectable break" and a "commercially meaningful" one are not the same thing (§13.1). This is your direct, named answer to "how do you separate a meaningful change from noise."
- **Confidence-score every flagged anomaly** rather than binary alerting — feeds directly into the trust-calibration design in layer 3.

### 2. Attribution layer — correlation → action

- **Structure:** bucket candidate causes into External (competitor moves, macro, seasonality — surfaced via news/unstructured data) and Internal (pricing, product/UI changes, funnel breaks, **schema/data-definition changes** — surfaced via structured logs + a changelog/feature-flag system). The "schema change" bucket is not in most competing teams' answers — it's grounded in real practitioner testimony that this is one of the *most common* root causes in practice (§9.4).
- **Decompose the metric along its driver tree** (Revenue = Volume × Price × Conversion, or the equivalent user-journey walk the casebook itself uses for Blinkit's checkout funnel) to isolate which sub-metric actually moved, before hypothesizing why.
- **Rank hypotheses by evidence strength, not correlation alone**, and **do not treat attribution scores as proof of causation.** This is the single most important discipline in the whole architecture, and it's a direct, quotable line from the research: *"SHAP, attention, saliency, and feature importance can prioritize signals, but they do not by themselves establish that changing a feature would change the outcome."* (§13.2) Validate top hypotheses with something closer to a counterfactual check (e.g., "did the metric partially recover when the suspected cause was addressed elsewhere / in a comparable segment?") rather than shipping a bare attribution ranking as the answer.
- **Fuse unstructured evidence at the cohort/account level, not per-ticket** — a single support ticket is weak signal; persistence of the *same* issue reworded across a growing thread over time is the real predictive pattern, per the University of Victoria/IBM escalation study (master research dossier, D7). *(Note: the Reddit thread in §9.4 is a separate, complementary finding — it's about upstream schema/data-definition changes as a root-cause category, not about ticket-wording persistence. Don't cite it for this specific claim, as an earlier draft incorrectly did.)*

### 3. Trust / narrative layer — two gates, not one

This is the most technically differentiated part of the design, and it directly answers "what happens when the data is genuinely ambiguous":

- **Gate 1 — pre-generation data quality gate.** If the underlying dimension/segment data is stale, sparse, or has a known join/tracking break, degrade to *"I don't have reliable enough data to explain this"* rather than generate a fluent, confident, wrong narrative. (Research doc §5/D5.)
- **Gate 2 — post-generation fidelity gate.** Before the narrative ships, run three automatic checks: **membership** (every driver named in the text must appear in the actual supplied evidence), **direction** (the asserted direction of effect must match the underlying statistic's sign), **coverage** (the largest-magnitude driver must be mentioned). This exists because a real 2026 fidelity audit found an LLM explaining risk factors **inverted the direction on 3 of 4 factors**, overriding the correct evidence with its own training-time priors (§8). Fall back to a deterministic template if either gate fails.
- **Show calibrated confidence, not a bare percentage** — present it with reliability context ("this type of call is right in ~80% of similar past cases"), because a real 184-participant study found well-calibrated confidence lifts decision accuracy ~20% while a miscalibrated or context-free number barely helps and increases automation bias (§13.3). Core design principle to state explicitly in the deck: *"optimize for helping users know when to trust it, not for making them trust it."*

### 4. Recommendation & ambiguity-routing layer — the differentiator

- **Every recommendation ships paired with its confidence and supporting evidence** — a suggestion the leader can interrogate, not a black-box directive.
- **When evidence is thin or conflicting, present the top 2–3 competing hypotheses with evidence for/against, rather than forcing one answer.** This is independently validated: conformal prediction sets (returning a small set of plausible answers instead of one) **measurably improved human decision accuracy** in a real preregistered randomized study (§13.4).
- **Route to a human using a cost-sensitive "learning to defer" policy, not a confidence threshold.** This is the sharpest upgrade in the whole design. Most competing answers will say "if confidence is low, escalate to a human" — that conflates *model uncertainty* with *human advantage*, which the literature explicitly shows are not the same thing (a model can be uncertain on a case a human also finds hard, gaining nothing from escalation; or confident on a case with a known blind spot, where it should escalate anyway). The actual decision rule, directly quotable for your architecture slide:
  > **automate if** `expected_loss(model)` **<** `expected_loss(human) + review_cost` **— else defer, subject to reviewer capacity.** (§13.4, Mozannar & Sontag 2020)
- **Log every resolved ambiguous case as training signal** — this is the thin-but-present Verify loop from stage C, and it's what keeps the two-gate trust layer improving over time instead of static.

---

## E — Evaluate Trade-offs

| Tension | Position, with evidence |
|---|---|
| Speed vs. accuracy | Real-time CUSUM layer between full PELT re-runs — don't wait for a full re-run to catch an abrupt shift, but don't trust CUSUM alone for regime changes it's not built for (§13.1) |
| Automation vs. trust | Two-gate narrative architecture (§8, §13.2) — the extra latency of a post-generation fidelity check is cheap insurance against the exact failure mode a real fidelity audit found (3-of-4 factors inverted) |
| False positives vs. false negatives | Minimum business-effect threshold (§13.1) prevents statistically-real-but-commercially-irrelevant alerts from causing alert fatigue — same lesson fraud-ops learned the hard way (70% of analyst time on false alerts, 90-95% industry FP rate, per the master dossier's D6) |
| Build vs. buy / statistical vs. LLM | Hybrid, not a choice: statistical/causal methods own detection and attribution (rigor, auditability); LLM is used strictly to narrate *already-verified* findings, gated by the fidelity check — never to detect or attribute on its own |
| Universal vs. narrow scope | Narrow, workflow-embedded framing over "explains any KPI for anyone" — directly sourced from the Copilot "wrong job" adoption evidence (§8 in the master dossier: 3.3% penetration after 18 months from a mismatch between what was built and what leaders actually needed) |

---

## S — Summarize Your Recommendation

> **Build a hybrid statistical + LLM engine that detects statistically *and* commercially significant KPI shifts (STL→PELT/CUSUM, with a minimum-business-effect gate), attributes them using ranked, evidence-weighted hypotheses across structured and unstructured data — while explicitly refusing to treat attribution as proof of causation — narrates findings through a two-gate trust layer (data-quality gate before generation, fidelity-check gate after), and routes ambiguous cases to analysts using a cost-sensitive deferral policy rather than a confidence threshold. Start narrow — regional revenue anomalies for ops leads — not "explains any KPI for anyone," and let the Verify feedback loop earn broader trust over time.**

This single sentence packs in six independently-sourced, non-generic design decisions (STL/PELT, business-effect threshold, evidence-ranked attribution, causation discipline, two-gate trust, cost-sensitive deferral) — each traceable to a real paper, real user quote, or real practitioner testimony rather than an assumption. That density of grounded specificity is what should separate this from a generic "AI dashboard that explains numbers" answer.

---

## The Two "Think About" Questions — direct answers to lead with

**"How do you separate a meaningful change from noise?"**
Statistical changepoint detection (PELT on a seasonality-adjusted residual, CUSUM for abrupt shifts, Bayesian online detection for drift) *plus* a minimum business-effect threshold — a break can be statistically real and still not worth flagging. Named techniques, named failure mode, named fix.

**"How do you move from correlation to something a leader can act on — and what do you do when data is ambiguous?"**
Rank causes by evidence strength across structured + unstructured data, explicitly refuse to treat attribution scores as causation, validate top hypotheses with counterfactual-style checks, and when evidence is genuinely thin, show 2-3 ranked hypotheses (proven to help human decisions) and route to a human using a cost-sensitive deferral rule — not a bare confidence threshold.



---



# 5. NotebookLM Synthesis Guide

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\BusinessIntelligence_ai_NotebookLM_Guide.md`*

---

# NotebookLM Synthesis Guide — BusinessIntelligence.ai

## Step 1: Create one notebook, upload these sources (in this order)

1. `BusinessIntelligence_ai_CIRCLES_RCA_Framing.md` ← the finished Stage 2 output, most important source
2. `BusinessIntelligence_ai_Research_Findings.md` ← all 15 sections of evidence, quotes, citations
3. `BusinessIntelligence_ai_Master_Research.md` ← the domain map + D1-D10 findings (some overlap with #2, fine — NotebookLM handles redundant sources well)
4. `BusinessIntelligence_ai_Strategy_Roadmap.md` ← original roadmap, gives NotebookLM the full stage context
5. The three Answer the Public `.xlsx` exports (`all categories-*.xlsx`) — upload as-is, NotebookLM reads spreadsheets
6. The six Apify `.xlsx` datasets (`dataset_g2-scraper_*.xlsx`, `dataset_capterra-reviews-scraper_*.xlsx`, `dataset_reddit-scraper-lite_*.xlsx`) — raw evidence, useful if you want NotebookLM to pull additional quotes beyond what's already curated
7. The Elicit `.md` exports (the changepoint / causal-RCA / confidence / selective-prediction answers + their "Refined"/"Independent review" pairs) — upload all of them; the review/refinement pairs are valuable as-is, don't merge them
8. `IITK Product Management Casebook 2024-25.pdf` ← for CIRCLES/RCA framework fidelity-checking and the Blinkit/Uber/cloud-storage worked examples

Skip the case-prompt screenshot — not needed once #1 exists.

## Step 2: Prompts to run, in this order

### A. Mind map / architecture sketch (your architecture slide skeleton)
```
Generate a mind map of the full BusinessIntelligence.ai system design, rooted at "Detect → Explain → Attribute → Recommend → Verify." For each stage, branch into: (1) the specific technique or mechanism used, (2) the design decision that makes it non-generic, (3) the source (paper, real user quote, or practitioner testimony) that justifies it. Pull the specifics from the CIRCLES + RCA Framing document — especially the "L — List Solutions" section — not from general knowledge.
```

### B. Research findings infographic (supporting evidence slide)
```
Summarize the top 5 recurring complaints about existing BI/analytics tools (with the strongest verbatim quote for each) and the top 4 statistical/ML techniques recommended for signal-vs-noise detection, root-cause attribution, and ambiguity handling. Cite the specific source document and section for each item so I can verify it. Format as two ranked lists suitable for a single dense slide.
```

### C. FAQ / defense prep (rehearse before presenting)
```
Based only on the uploaded sources, generate 12 hard questions a case-competition judge might ask about this design, covering: (1) why PELT/CUSUM over simpler thresholding, (2) why the two-gate trust layer is necessary rather than one gate, (3) why "learning to defer" is better than a confidence-threshold escalation rule, (4) what happens if the LLM hallucinates a root cause anyway, (5) how this differs from Power BI's existing "Explain the increase/decrease" feature, (6) why narrow scope (regional revenue for ops leads) beats a general "explain any KPI" positioning. For each question, give the answer using only what's in the sources, with the specific citation.
```

### D. Audio overview
```
Generate an audio overview focused specifically on the two "Think about" questions in the case: separating signal from noise, and moving from correlation to an actionable, evidence-based recommendation under ambiguity. Treat these as the two hardest parts to defend live.
```

### E. Stress-test the weakest point (run this one last, be skeptical of the answer)
```
What is the single weakest, least-evidenced claim in the CIRCLES + RCA Framing document? Where does the framing rely on inference or design judgment rather than something directly sourced? Be specific about which sentence and why.
```
Use E's answer as your own final gut-check before locking the deck — it's the one prompt here designed to find gaps, not summarize strengths.

## Step 3: What to do with the outputs
- Mind map (A) → hand to Napkin AI as the input for the architecture diagram (Stage 4 of your roadmap)
- Infographic (B) → becomes your research-grounding slide directly
- FAQ (C) + audio overview (D) → rehearsal only, not deck content
- Stress-test (E) → if it surfaces something real, come back and I'll help tighten that specific section of the framing doc before you move to the deck build



---



# 6. AIC Round 1 — Deck Content Spec

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\AIC2026_Deck_Content.md`*

---

# AIC 2026 · Round 1 — Deck Content Spec
**Problem Statement 3 — BusinessIntelligence.ai (KPI Storytelling Engine)**

Use this file to rebuild, refine, or restyle the deck anywhere (Claude Design, Claude chat, Canva, Figma). It maps 1:1 to the built `.pptx`.

**Hard constraints from the brief & template**
- Deliverable: concept deck, **max 3 content slides** + a **max 3-minute video**
- Template: official Accenture AIC template, **Arial**, instructions slide removed before submission
- File naming: `Team name_Idea Name.pptx`
- Brief explicitly says: *"research, debate, and creativity are encouraged over technical precision at this stage"*

**Deck structure (7 slides total, 3 of which are content)**
1. Title (template, unchanged) · 2. Team details (fill in) · **3. Problem** · **4. Solution** · **5. Why it matters** · 6. Video · 7. Thank you

**Palette:** Accenture purple `#A100FF`, deep purple `#460073`, lavender tint `#F4EAFF`, ink `#1B1B25`, grey `#5F6070`, accent blue `#0B7BBF`, gap-marker red `#C0245C`

---

## Slide 3 — `01 | The Problem — dashboards show what moved, never why`

**Row 1 — four stat cards**
| 73% | ~21% | Days | 3.3% |
|---|---|---|---|
| of BI implementations fail on the diagnostic gap — not on technology | of employees keep using dashboards that cannot answer "why" | typical analyst turnaround to explain a single metric move | Copilot enterprise penetration — AI hired for the wrong job |

**Row 2 — two cards**

*Three structural reasons the gap persists*
- **Detection ≠ explanation.** Tools flag that a number moved; the mechanism behind it stays a manual investigation.
- **Evidence lives in two worlds.** Metrics sit in the warehouse; causes sit in support tickets, CRM notes, changelogs and news.
- **Confidence is unpriced.** No tool states how sure it is — so a leader cannot separate a real finding from a fluent-sounding guess.

*Verified market voice — real reviews, scraped and checked*
- "The experience can still require too much user interpretation… moving from a question to a fully trusted, decision-ready insight." — ThoughtSpot user, G2
- "Automated insights… occasionally surface correlations that aren't actually meaningful without manual review." — Tellius user, G2
- "Sales Ops deletes columns in Salesforce. Marketing changes the definition of a lead bucket." — r/BusinessIntelligence

**Row 3 — flow: THE PATH A LEADER LIVES TODAY — two days, and still a hedge**
1. **Dashboard flags −8%** — No cause, no confidence, no next step.
2. **Analyst pulls data** — Four or more tools, manually reconciled. Day 1.
3. **Cross-references** — Tickets, CRM notes, changelogs, competitor news. Day 2.
4. **Writes a narrative** — Plausible, unranked, with no stated confidence.
5. **Window has closed** — The decision was already taken without it.

**Row 4 — competitive floor (3 cards)**
- **ThoughtSpot Spotter** — Natural-language Q&A with automated anomaly detection. → *Stops at: users still interpret the answer themselves.*
- **Power BI "Analyze"** — ML-ranked contributors across four chart views. → *Stops at: binary before/after only — no narrative, no cross-dimension reasoning.*
- **Tellius** — Variance decomposition with Shapley-ranked drivers. → *Stops at: surfaces correlations its own users call not meaningful.*

**Closing band:** The gap every competitor shares: none of them close the loop from detection → evidence-ranked cause → an action a leader can defend.

**Sources line:** sranalytics.io BI failure study · G2 & Capterra reviews (314 verified) · r/BusinessIntelligence · Microsoft Learn · Copilot adoption research

---

## Slide 4 — `02 | Our Solution — a five-stage KPI storytelling engine`

**Row 1 — pipeline**
`1 DETECT` Only shifts that are statistically and commercially real → `2 EXPLAIN` Narrative passes two gates before it may ship → `3 ATTRIBUTE` Causes ranked by evidence, across both data types → `4 RECOMMEND` Next step, paired with its evidence and confidence → `5 VERIFY` Resolved cases feed back and sharpen the engine

**Row 2 — the three hard questions**

*Q1 · Separating signal from noise*
- **STL decomposition** strips trend and seasonality first.
- **PELT** finds exact changepoints on the residual; CUSUM watches live; Bayesian online detection covers slow drift.
- **Minimum business-effect gate:** every alert must also clear a materiality bar (≥2pp sustained, or revenue impact above ₹X).

*Q2 · Correlation → action*
- **Driver tree** (Revenue = Volume × Price × Conversion) isolates which sub-metric actually moved.
- **Causes bucketed** External (competitor, macro, seasonal) vs Internal (pricing, funnel break, and the bucket most miss — schema changes nobody logged).
- **Ranked by evidence strength;** attribution scores are never treated as proof of causation.

*Q3 · When data is genuinely ambiguous*
- **Gate 1 — pre-generation:** data-quality check; degrades to "not enough reliable data" rather than inventing a story.
- **Gate 2 — post-generation:** fidelity check on membership, direction and coverage of every claim.
- **Shows 2–3 ranked hypotheses** when evidence is thin, not one false-confident answer.

**Row 3 — WORKED EXAMPLE: "revenue dropped 8% in the West region"**
1. **Flagged** — −8%, sustained three weeks, clears the materiality gate.
2. **Decomposed** — Driver tree isolates Conversion — Volume and Price are flat.
3. **Corroborated** — Ticket volume on payment errors up 4×; changelog shows a gateway API change on 12 Aug.
4. **Gated** — Both gates pass: every driver named is in evidence, directions match.
5. **Delivered** — Cause ranked #1, confidence 0.82, action: escalate to engineering.

**Row 4 — inputs & output**
- **STRUCTURED INPUT:** Warehouse metrics · CRM · product & funnel logs · pricing and campaign changelog · feature flags · schema-diff feed
- **UNSTRUCTURED INPUT:** Support tickets aggregated per account and cohort — not per ticket · sales call notes · competitor and market news
- **WHAT THE LEADER RECEIVES:** What changed · why, ranked by evidence · how confident · what to do next · one click to the analyst, packet pre-built

**Closing band:** Escalation is a cost rule, not a threshold: automate if `expected_loss(model) < expected_loss(human) + review_cost` — else route to an analyst.

**Footer:** The LLM narrates only what the statistical layer has already verified — it never detects or attributes on its own.

---

## Slide 5 — `03 | Why It Matters — time-to-decision, earned trust, a defensible wedge`

**Row 1 — before / after**
- **TODAY:** A dashboard flags −8%. An analyst spends two days pulling data across tools, cross-referencing tickets and notes, and guessing at causes. The answer lands after the decision window has closed — and its confidence is a verbal hedge.
- **WITH BUSINESSINTELLIGENCE.AI:** Only commercially material shifts surface. Each arrives as a ranked, evidenced explanation in minutes with an explicit confidence — and the genuinely ambiguous cases reach an analyst with the evidence already assembled.

**Row 2 — success metrics**
| Days → minutes | Analyst hours | Acceptance rate | Gate pass rate |
|---|---|---|---|
| time-to-explanation for a flagged metric move | redirected from assembling evidence to exercising judgement | share of recommendations a leader acts on | narratives blocked before reaching a human |

**Row 3 — three cards**

*Who it helps* — **Business leader (primary):** owns the decision and currently waits days for it. · **Analyst:** becomes the QA and escalation layer — augmented, not replaced. · **Data team:** schema and definition changes surface instead of silently corrupting metrics.

*Why now* — **Gartner:** 75% of new analytics content will be GenAI-contextualised by 2027. · **Named risk — "agent drift",** with guardian agents prescribed as the mitigation. · **Our two gates are that pattern,** designed in from day one rather than bolted on.

*Why this wins* — **Horizontal "explains any KPI" tools stall** — Copilot reached 3.3% in 18 months. · **We start narrow:** regional revenue anomalies for ops leads. · **Trust compounds** through the Verify loop — then the scope widens.

**Row 4 — WHAT COULD GO WRONG (and what we built to stop it)**
- *A confident, wrong narrative reaches a leader* → Two gates plus a deterministic template fallback; the LLM never asserts what evidence does not carry.
- *Alert fatigue from too many flags* → Materiality gate first, then cost-sensitive deferral — volume is tuned to reviewer capacity.
- *Upstream data silently breaks* → Schema-diff feed is a first-class cause bucket, not an afterthought.
- *Analysts distrust or resist it* → They receive an evidence packet, not a verdict — and they own every escalation.

**Closing band:** In one line: detect what is both statistically and commercially significant, explain it only when the evidence supports the words, and hand over to a human whenever the human is genuinely likely to do better.

**Grounding:** Gartner 2027 analytics forecast · Mozannar & Sontag 2020 (ICML) · Cresswell et al. 2024 (ICML) · arXiv 2608.08126 narrative-fidelity audit · Fregosi et al. 2026 (AAAI)



---



# 7. AIC Round 1 — Visuals Guide (Napkin AI)

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\AIC2026_Visuals_Guide.md`*

---

# Visuals Guide — Napkin AI, NotebookLM & the 3-minute video

## First, the honest framing

The Round-1 deck is **already complete and visual** — the pipeline, the worked example, the today-path flow and the risk grid are all built as native PowerPoint shapes, so they stay editable and never render as blurry images. **You do not need Napkin AI to submit Round 1.**

Where Napkin genuinely earns its place:
1. **The 3-minute video** — this is its highest-value use. Video needs motion and clean visuals; native pptx shapes are static and fiddly to animate.
2. **Round 2**, if you're shortlisted — that round explicitly asks for detailed, prototype-ready solutions, where richer diagrams matter.
3. **Optional upgrade** to one row of the deck, if you decide a hand-designed diagram beats the built version.

---

## Napkin AI — exact usage

**How Napkin works:** you paste text, select it, and Napkin generates visual options from that text. It works from *short declarative sentences*, not paragraphs. Long prose produces cluttered output.

**Setup once:** In Napkin, open the style/color panel and set the accent to `#A100FF` (Accenture purple) with `#460073` as the secondary. Export as **PNG with transparent background at 2× resolution** so it drops onto any slide cleanly.

### Prompt 1 — The five-stage engine (use in the video, ~0:45–1:30)
Paste exactly this, select it, generate:
```
A KPI storytelling engine works in five stages.
Detect: flag only shifts that are statistically and commercially real.
Explain: the narrative passes two gates before it may ship.
Attribute: rank causes by evidence across structured and unstructured data.
Recommend: pair every next step with its evidence and confidence.
Verify: resolved cases feed back and sharpen the engine.
```
Pick a **horizontal process flow** style. This is your single most reusable asset.

### Prompt 2 — The two-gate trust layer (the differentiator; video ~1:30–2:10)
```
Every generated narrative passes two gates.
Gate one runs before generation: it checks data quality and refuses to explain unreliable data.
Gate two runs after generation: it checks that every named driver appears in the evidence, that directions match, and that the largest driver is mentioned.
If either gate fails, the system falls back to a deterministic template instead of a generated story.
```
Pick a **decision flow / gated pathway** style.

### Prompt 3 — Before and after (video opener, ~0:00–0:45)
```
Today: a dashboard flags an eight percent drop. An analyst spends two days pulling data across tools. The answer arrives after the decision window has closed.
With BusinessIntelligence.ai: only material shifts surface. Each arrives in minutes as a ranked explanation with an explicit confidence score.
```
Pick a **side-by-side comparison** style.

### Prompt 4 — The worked example (video ~2:10–2:45)
```
Revenue dropped eight percent in the West region.
The drop clears the materiality gate: sustained three weeks.
The driver tree isolates conversion. Volume and price are flat.
Payment error tickets rose four times. The changelog shows a gateway API change on twelve August.
Both gates pass. The cause ranks first with confidence zero point eight two. The action is to escalate to engineering.
```
Pick a **numbered timeline or step sequence** style.

### Prompt 5 — Driver tree (optional, Round 2)
```
Revenue equals volume multiplied by price multiplied by conversion.
Each branch splits by region, by segment, and by channel.
The engine walks this tree to isolate which sub-metric actually moved before hypothesising why.
```
Pick a **tree / hierarchy** style.

**If you want one of these in the deck:** the cleanest swap is Slide 4's worked-example row (Napkin's timeline styles are strong there). Send me the exported PNG and I'll place it properly — don't paste it in yourself over the existing shapes, or the spacing will break.

---

## NotebookLM — what's still worth generating

You already have the mind map, the FAQ, and the audio overview. Two things remain genuinely useful:

**1. Video script grounding** — paste into your existing notebook:
```
Write a 3-minute spoken script for a product concept video on BusinessIntelligence.ai, structured as: 40 seconds on the problem, 90 seconds on how the five-stage engine works with the West-region worked example, 30 seconds on why it matters and why now, 20 seconds close. Use only claims supported by the uploaded sources. Write it to be read aloud — short sentences, no bullet points, no jargon a business leader wouldn't use.
```

**2. A final devil's-advocate pass** before you submit:
```
A judge has three minutes with this concept and is skeptical. Based only on the uploaded sources, what are the three sharpest objections they would raise, and what is the strongest evidence-backed response to each? Flag any claim in the deck that the sources do not actually support.
```
This is the same class of prompt that caught the two real citation errors last time — worth running once more against the final deck content.

**Infographics:** NotebookLM's infographic output is fine for personal synthesis but generally too generic for a submitted deck. Don't use it in the deck; Napkin's output is more controllable and on-brand.

---

## Before you submit — checklist

- [ ] Open the `.pptx` in PowerPoint and read every slide once (I validated structure and rendered every slide, but your eyes are the final check)
- [ ] Fill in Slide 2: team name, member names, photos, college, stream, year of graduation — **all fields are mandatory** per the template
- [ ] Rename the file to `TeamName_BusinessIntelligence.ai.pptx`
- [ ] Run spell check (the template explicitly asks for this)
- [ ] Confirm the instructions slide is gone — it already is in the built file
- [ ] Record the video (max 3 minutes) and add the link/embed to Slide 6



---



# 8. AIC Round 1 — 3-Minute Video Script

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\AIC_Video_Script_3min.md`*

---

# BusinessIntelligence.ai — 3 minute video script
**Team SouthernHustlers · Accenture Innovation Challenge 2026 · Problem Statement 3**

Paced for **135 words per minute**. Measured at 380 spoken words, landing at **2:48**, which leaves twelve seconds of slack for pauses and breaths. Section timings below are the real per-section counts, not estimates.

The technical middle gets roughly 100 of those seconds. That is deliberate: it is the part that separates this from a generic pitch, so it is the part that should not be rushed.

Bracketed lines are what goes on screen, not what you say.

---

## 0:00 – 0:35 · The problem

> A dashboard says revenue in the West fell eight percent.
>
> It will not say why. That still takes an analyst about two days.
>
> We read and coded three hundred and eighty four reviews and forum threads on the leading BI tools. Eighteen percent say you need an expert. Thirteen percent describe manual digging.
>
> But only zero point six percent ever say the words "root cause". Nobody is asking for it. They are complaining about the labour that replaces it.

*[Problem slide. Hold on the coded bar chart for the percentages, then rest on the 0.6% bar.]*

---

## 0:35 – 0:48 · What we are building

> BusinessIntelligence dot AI is one engine.
>
> It reads numbers from the warehouse, CRM and changelog, and words from tickets, sales notes and news. Five stages. Detect, Attribute, Explain, Recommend, Verify.

*[Switch to the solution slide. Let the five step flow sit on screen.]*

---

## 0:48 – 2:28 · How it works

> **Detect.** STL decomposition strips trend and seasonality. PELT finds exact changepoints on the residual, CUSUM watches live, Bayesian detection covers slow drift.
>
> But a real break is not automatically worth attention. Every alert must also clear a Minimum Business Effect Gate: two points sustained, or a revenue floor. Two tests, not one.
>
> **Attribute.** A driver tree splits revenue into volume, price and conversion, down to the segment that moved.
>
> Prediction is not intervention. What promotes a cause is two sources agreeing: a ticket spike and a changelog entry on the same day.
>
> **Explain.** The failure mode here is hallucination: a fluent sentence the evidence does not support. A twenty twenty six audit caught a model inverting the direction on three of four risk factors.
>
> So we gate it twice. Before generation, a data quality check: stale or sparse, and it says so. After generation, every claim is tested for membership, direction and coverage. Either gate fails and a deterministic template ships. The model never gets the last word.
>
> **Recommend and Verify.** On thin evidence, conformal prediction returns two or three ranked hypotheses, not one confident guess.
>
> Escalation is not a confidence threshold. Sending everything below eighty percent to a human escalates the cases humans also fail.
>
> We use learning to defer. Automate if the model's expected loss is below the human's, plus the cost of review.

*[Bottom half of the solution slide. Move across the four columns in time with the words. Hold on the gate diagram during Explain, and on the expected loss line at the end.]*

---

## 2:28 – 2:48 · Close

> The leader gets one screen. Revenue down eight percent, driven by conversion, not price. Likely cause, a gateway change. Confidence, zero point eight two. Escalate to engineering.
>
> Two days becomes minutes. We are not selling root cause analysis. We are selling the two days back.

*[Output card, then hold on the closing band.]*

---

## Delivery notes

- **Your pace is the constraint, not the content.** At 135 wpm this is 2:48. Drift to 120 wpm and it becomes 3:10, which is over. Time one read-through before you record.
- **Two lines carry the whole pitch:** the zero point six percent finding, and learning to defer. Give each a clear beat before and after. Everything else can move at pace.
- **Do not read citations aloud.** "A twenty twenty six audit" is enough. The arXiv reference is on the slide for anyone who wants it.
- **If you run long,** cut the sentence beginning "Prediction is not intervention" first. Never cut the hallucination line, the two gates, or learning to defer: those three are the pitch.
- **If you run short,** add after the 0.6% line: "That is why we lead with time saved, not with a feature name."
- Say numbers as words: "eight percent", "zero point eight two", "three of four".



---



# 9. Design System — README

*Source: `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\05_Design_System\case-deck-design-system\README.md`*

---

# Case Deck Design System

A CSS system for building **dense, evidence-first case-competition slides** in HTML — the
"consulting poster" style that actually places in product case competitions, rather than the
sparse McKinsey-whitespace style that reads well in a boardroom and loses in a judging room.

The components are reverse-engineered from two decks that were shortlisted: a HiLabs healthcare
PS3 deck and a Flipkart/Netflix constraint-redesign deck. Everything here — the tab navigation,
the dark impact plates with accent numerals, the pain→solution blocks, the heat-shaded journey
tables, the risk grids — is a pattern lifted from those, generalised and themed.

## Why HTML and not PowerPoint

Because these layouts are grid-heavy and text-dense. In PowerPoint every block is a hand-placed
box that breaks the moment a sentence changes length. In CSS the grid reflows, the theme is one
class swap, and the whole deck is diffable text you can keep in git. Export to PDF at the end —
most competitions accept PDF, and the fidelity is exact.

## Quick start

```bash
git clone <this repo>
cd case-deck-design-system
python -m http.server 8000     # any static server
# open http://localhost:8000/examples/aic-round1.html
```

Or just open `examples/aic-round1.html` directly in a browser.

## Files

```
src/
  tokens.css       colours, type scale, spacing, radii — four themes
  layout.css       slide canvas, tabs, title bar, grids, bands, print rules
  components.css   every content block and chart primitive
examples/
  aic-round1.html  a real 3-slide competition submission
  components.html  showcase of every component, in two themes
CLAUDE.md          instructions for Claude Design / Claude Code
COMPONENTS.md      copy-paste markup catalogue
```

## Using it with Claude

Point Claude at this repo and it will follow `CLAUDE.md` automatically. A prompt that works:

> Using this design system, build a 3-slide deck for `<problem statement>`. Theme: civic.
> Slide 1 proves the problem is real with sourced statistics and two verbatim user quotes.
> Slide 2 is the solution, with a chevron process bar and a worked example flow.
> Slide 3 is why it matters, with a before/after, four success metrics, and a risk grid.

The important constraint to repeat: **compose from existing classes, never write new CSS.**
That is what keeps twenty slides looking like one deck.

## Themes

| Class | Look | Use for |
|---|---|---|
| `theme-civic` | White · royal blue · yellow highlight · heavy borders | Analytical, enterprise, B2B, healthcare, ops |
| `theme-spotlight` | Near-black · saturated red · high contrast | Consumer, D2C, media, bold narrative |
| `theme-accenture` | White · Accenture purple · gold accent | Accenture Innovation Challenge |
| `theme-forest` | White · deep green · amber accent | Sustainability, agri, public sector |

Put the class on `<body>` for the whole deck, or on one `.slide` to switch mid-deck.
Adding a theme means adding one block of variables to `tokens.css` — no component changes.

## Exporting

**PDF (recommended).** Chrome → Print → Destination *Save as PDF* → Margins *None* →
Background graphics **ON**. Each slide becomes one landscape page at exactly 16:9.

**PNG per slide.** Chrome headless:
```bash
chrome --headless=new --disable-gpu --hide-scrollbars \
       --window-size=1700,2050 --screenshot=out.png \
       http://localhost:8000/examples/aic-round1.html
```

**PowerPoint.** Export to PDF first, then insert the pages as images. Do not rebuild these
layouts natively in PowerPoint — you will lose the grid behaviour that makes them hold together.

## Design rules worth keeping

1. **Density is credibility.** A judge skims. Sparse slides read as thin thinking. The reference
   decks fill every inch — but in organised, bordered blocks, never as a wall of prose.
2. **Every number carries a source.** A cited stat beats an uncited one every time, and it costs
   you eleven pixels of caption.
3. **Lead each bullet with a bold claim.** The judge reads the bold text first; the explanation
   is there for the ones who lean in.
4. **The slide title is a claim, not a label.** "Dashboards show what moved — never why" tells the
   story even if nothing else is read.
5. **Answer the risk question before it is asked.** Every reference deck has a risk/mitigation
   grid. It signals that you have thought past the demo.
6. **One highlight colour, used twice per slide.** More and nothing stands out.



---



# 10. Manifest — binary deliverables and every related file

Full paths, so any of these can be opened directly from this document.


## Final submission (Accenture Innovation Challenge, Round 1)

- **SouthernHustlers_BusinessIntelligence.ai.pptx** (26.6 MB) — Submitted deck — Arial, no dashes, technical solution slide, team details filled in
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\01_Final_Submission\SouthernHustlers_BusinessIntelligence.ai.pptx`
- **SouthernHustlers_BusinessIntelligence.ai.mp4** (7.1 MB) — Recorded pitch video
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\01_Final_Submission\SouthernHustlers_BusinessIntelligence.ai.mp4`
- **SouthernHustlers_BusinessIntelligence.ai.pdf** (1.3 MB) — Exported PDF of the final deck
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\01_Final_Submission\SouthernHustlers_BusinessIntelligence.ai.pdf`
- **Team SouthernHustlers IIT Madras.pdf** (4.0 MB) — Team registration / details document
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\01_Final_Submission\Team SouthernHustlers IIT Madras.pdf`

## Prior deck iterations (superseded by the final submission above)

- SouthernHustlers_BusinessIntelligence.ai_Round1.pptx (18.6 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\SouthernHustlers_BusinessIntelligence.ai_Round1.pptx`
- SouthernHustlers_BusinessIntelligence.ai_Round1_FINAL.pptx (18.7 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\SouthernHustlers_BusinessIntelligence.ai_Round1_FINAL.pptx`
- BusinessIntelligence_ai_McKinsey_Deck.pptx (206 KB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\BusinessIntelligence_ai_McKinsey_Deck.pptx`
- The_Diagnostic_Blueprint.pptx (2.6 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\The_Diagnostic_Blueprint.pptx`
- The_Signal_Through_the_Noise.pptx (10.0 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\The_Signal_Through_the_Noise.pptx`
- The_Signal_Through_the_Noise.pdf (7.9 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\02_Prior_Deck_Versions\The_Signal_Through_the_Noise.pdf`

## Slide artwork (standalone PNGs)

- AIC_Problem_Slide.png (202 KB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\03_Slide_Artwork\AIC_Problem_Slide.png`
- AIC_Solution_Slide.png (269 KB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\03_Slide_Artwork\AIC_Solution_Slide.png`

## Research corpus (raw scraped/coded data)

- Reddit_BusinessIntelligence.md (16 KB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\04_Research_Docs\Reddit_BusinessIntelligence.md`
- G2/Capterra scraped review datasets and coded theme counts: referenced in section 3 (Research Findings) above; raw `.xlsx` exports were processed from `C:\Users\rakes\Downloads`

## Competition source materials

- 6a7c763e089e4_aic_2026.zip (19.2 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\06_Competition_Source\6a7c763e089e4_aic_2026.zip`
- AIC_Talent-Brand_PPT-Template (1).pptx (17.7 MB)
  `C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\06_Competition_Source\AIC_Talent-Brand_PPT-Template (1).pptx`

## Design system (git repo — reusable across future case decks)

`C:\Users\rakes\OneDrive\Desktop\BusinessIntelligence_AI_AIC2026\05_Design_System\case-deck-design-system`

Contains: `src/tokens.css`, `src/layout.css`, `src/components.css`, `CLAUDE.md`, `COMPONENTS.md`, `README.md`, and `examples/` (the rendered problem/solution slides as editable HTML). Version-controlled with git; run `git log --oneline` inside the repo for the full change history.