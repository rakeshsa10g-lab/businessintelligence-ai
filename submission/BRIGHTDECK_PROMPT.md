# BrightDeck generation prompt — BusinessIntelligence.ai Round 2

*Single consolidated prompt. Paste the entire block below into BrightDeck as one input.*

---

## 1. DECK OBJECTIVE

Generate a 10-slide, consulting-grade executive pitch deck for **BusinessIntelligence.ai**, Team SouthernHustlers' submission to the Accenture Innovation Challenge 2026, Round 2, Problem Track 3 ("KPI intelligence-to-action engine"). This deck presents both the business proposal and the working prototype for judge evaluation (per R2-DEL-3: "presenting both the proposal and the prototype for evaluation").

The deck must prove three things and make each memorable on its own:

1. **It knows when NOT to answer.** Conflicting or insufficient evidence routes to human review or abstention — the system does not manufacture a root cause.
2. **Numbers are computed, not generated.** Deterministic statistics and business rules own every quantitative fact. The LLM writes sentences inside a schema, against a frozen evidence bundle, and cannot compute, query, or invent a number.
3. **Automation is bounded.** The system can raise an approved request (e.g., escalate to Engineering); it cannot autonomously execute a remediation, rollback, or any action outside a named, permitted scope.

Everything else in the deck is in service of these three ideas. If a slide does not advance the problem/solution/trust/value logic or reinforce one of the three ideas, cut it.

---

## 2. AUDIENCE

Accenture Innovation Challenge judges evaluating a **prototype-stage submission**, not a funded startup or a production vendor. Assume three judge archetypes are in the room simultaneously:

- **Business/product judge** — wants the problem, the differentiation from Power BI/Tableau/Copilot, and the value mechanism. Will ask "why does this need to exist" and "what's the business value" — the honest answer to the latter is a stated limitation (no ROI is claimed), not a fabricated number.
- **Technical judge** — wants to know why an LLM doesn't just query the warehouse, how hallucination is structurally prevented (not prompted away), and why LangGraph rather than a custom orchestrator or a multi-agent framework.
- **Skeptical judge** — will probe the synthetic dataset, ask whether the detector's evaluation is circular (it is, partially — say so), and ask what breaks the story. Reward for volunteering a limitation before being asked is real; reward for waiting to be caught is negative.

Design every slide so it survives being read cold, without narration — a judge flipping back to slide 4 during Q&A must be able to reconstruct the point from the exhibit alone.

---

## 3. TONE

Strategy-consulting register: declarative, evidence-first, unemotional about limitations. Confidence comes from precision, not adjectives. Never use "revolutionary," "cutting-edge," "seamless," "game-changing," "powerful AI," or similar filler. State what is true, cite what supports it, and state plainly what is not yet known.

The deck should read like a McKinsey/BCG/Bain diligence deck for a technology asset, not like a startup pitch deck and not like an engineering design review. It is not selling excitement; it is demonstrating that a hard, specific problem (analysts spend days manually reconciling *why* a KPI moved, and no existing tool says when it doesn't know) has been solved with discipline that can be tested, not just claimed.

---

## 4. VISUAL STYLE — DESIGN SYSTEM (Round 1 continuity, mandatory)

Preserve the verified Round 1 visual identity recovered directly from the submitted Round 1 deck (`SouthernHustlers_BusinessIntelligence.ai.pptx`) and the `case-deck-design-system` repo it was built from (`theme-accenture`). Do **not** invent a new brand.

| Element | Specification |
|---|---|
| **Canvas** | 1600×900, one slide = one canvas. Never shrink content to fit — cut words instead. |
| **Typeface** | Arial only, everywhere. No secondary font. |
| **Primary purple** | `#A100FF` |
| **Deep purple** | `#460073` |
| **Light purple / panel tint** | `#F4EAFF` |
| **Ink (body text)** | `#1B1B25` |
| **Muted grey (captions/sources)** | `#5F6070` |
| **Accent gold (highlight only, use sparingly)** | `#FFC53D` |
| **Danger / negative** | `#C0245C` |
| **Success / positive** | `#0B7B5C` |
| **Dark plate (section bands, impact numerals)** | `#2E1046` |
| **Background** | White or the light-purple tint only. No gradients, no dark-mode slides except the deliberate dark "impact plate" and closing-band accents already specified per slide below. |
| **Slide title grammar** | `<two-digit number>  |  <claim, not a label>`. Title states the conclusion. Example: `04  |  A 25% West revenue decline is decomposed, evidenced, and delivered as one reviewable decision`. Never a bare noun phrase like "Architecture" or "User Personas." |
| **Numbered slide structure** | Every slide carries its sequence number in the title bar, consistent with Round 1. |
| **Source strip** | Every content slide ends with a one-line, non-bold, small-caption sources strip naming the artefact(s) behind its claims (e.g., `Sources: eval/attribution_report.md · eval/graph_report.md`). Never a bare URL list; never omitted. |
| **Density** | Dense, evidence-first "consulting poster" style — not sparse whitespace-heavy startup-deck style. Each slide should carry 3–5 distinct visual blocks (a stat row, a diagram, a card grid, a closing takeaway band), not one big idea floating in whitespace. But dense ≠ crowded: maintain consistent margins, aligned grid columns, and one clear reading path per slide. |
| **Iconography** | None generic. No stock AI/robot/brain imagery, no 3D icons, no gradients-on-icons. If a symbol is needed, use a simple geometric glyph (arrow, chevron, plate) consistent with the process-flow and stat-card language already established. |
| **Diagram style** | Flat, labelled, rectilinear. Process flows as left-to-right chevron/step sequences with arrows. Architecture as a top-to-bottom layered stack with labelled boundaries. Comparisons as tables or 2-column before/after blocks — not decorative infographics. |

---

## 5. SLIDE COUNT

**Exactly 10 slides** (plus, if BrightDeck requires them structurally, a title/cover and closing/thank-you frame that carry no independent content — do not count those against the 10). No slide should be added "because there's room" and none of the 10 below should be split or merged further.

---

## 6. EXACT SLIDE-BY-SLIDE STORYLINE

For each slide: **Takeaway title** (verbatim — do not rephrase), **purpose**, **exhibit(s)**, **content to include**, **data points with evidence class**, **what NOT to put on this slide**.

Evidence classes, used throughout — carry these letters inline next to every number:
**[M]** measured on the running system · **[S]** synthetic evaluation (real measurement, synthetic dataset, ground truth known by construction) · **[R]** research-sourced external citation · **[A]** stated assumption · **[I]** illustrative worked example.

---

### Slide 1 — Executive hook

**Takeaway title:** `01  |  Business leaders can see what changed; the harder problem is knowing why they should trust the explanation`

**Purpose:** Open on the concrete moment, not an abstraction. One KPI event, minimal text, the investigation gap implied rather than lectured.

**Exhibit:** A single large stat block — "Net Revenue · West × Web/Mobile App, ↓25.0%" with the date window — paired with a short, quiet caption: *"A dashboard will show this number. It will not show why, how sure to be, or what to do next."* No process diagram yet — that's slide 2/3.

**Content:**
- The movement figure itself: **↓25.0%**, West × Web/Mobile App, 12 Jul → 26 Jul 2026 **[S]** (from S1, the demonstration scenario — label it as such, not as a live customer event).
- One line naming the gap: detection ≠ explanation ≠ trust ≠ action.
- Do **not** yet reveal the driver, the evidence, or the recommendation — that is the payoff of Slide 4, not Slide 1.

**Do not include:** logos, mission statements, team introduction, technology names (LangGraph, LLM, etc.) — none of that belongs on the hook.

---

### Slide 2 — Problem

**Takeaway title:** `02  |  Traditional BI stops at the signal, leaving analysts to manually stitch together the explanation`

**Purpose:** Establish the cost of the status quo with sourced, external evidence — not opinion.

**Exhibit:** A left-to-right process flow (5–6 steps) showing today's manual path: `Dashboard flags a drop` → `Analyst pulls data across 4+ tools` → `Cross-references tickets, CRM, changelogs` → `Writes an unranked narrative` → `Decision window has closed`. Pair it with a 4-stat-card row above or below.

**Content — four stat cards, all research-sourced [R]:**
- **73%** of BI implementations fail on the diagnostic gap, not on technology.
- **~21%** of employees actively use dashboards that can't answer "why."
- **~70%** of analyst time is spent investigating alerts that prove legitimate.
- **22%** decline in detection accuracy once an analyst reviews 30+ alerts/day.

**Supporting quotes (verbatim, sourced), 2–3 max, in a "verified market voice" panel:**
- *"Dashboards are great at telling you what's happening, but the moment you ask why…"* — ThoughtSpot user, G2.
- *"…correlations that aren't actually meaningful without manual review."* — Tellius user, G2.

**Structural framing (three bullets, not paragraphs):**
1. Detection is not explanation — tools flag movement, the mechanism stays manual.
2. Evidence lives in two worlds — metrics in the warehouse, causes in tickets/CRM/changelogs.
3. Confidence is unpriced — no tool states how sure it is.

**Sources strip:** sranalytics.io BI failure study · Gartner 2025 · G2 & Capterra verified reviews · r/BusinessIntelligence.

**Do not include:** anything about *our* product yet. This slide is 100% about the world before BusinessIntelligence.ai exists.

---

### Slide 3 — Solution

**Takeaway title:** `03  |  BusinessIntelligence.ai closes the gap from KPI movement to evidence-backed business action`

**Purpose:** Introduce the five-stage product loop as the spine the rest of the deck will hang off. This is the single most-referenced diagram in the deck — make it unambiguous and reusable in miniature on later slides if BrightDeck supports repeating a motif.

**Exhibit:** Five-step chevron flow, each step answering the question a business user actually asks:

`1 DETECT — Is it real, and does it matter?` → `2 ATTRIBUTE — What drove it, and where?` → `3 EXPLAIN — What does the evidence support?` → `4 RECOMMEND — What should happen, and who acts?` → `5 VERIFY — Can every claim be checked?`

**Content:**
- One line under the flow: *"Internally the system runs Detect → Attribute → Retrieve → Verify → Recommend. The user never sees that computation order — only the decision."*
- One short line stating the product is a decision workspace, not a chatbot: *"There is no chat box, by design. A conversational surface invites questions the model must not answer, from data it must not reach."*

**Do not include:** the technical architecture stack (that's Slide 6), specific tool names (LangGraph, DuckDB, etc. — none of that belongs here), or numeric evaluation results (Slide 7).

---

### Slide 4 — Hero case + decision workspace

**Takeaway title:** `04  |  A 25% West revenue decline is decomposed, evidenced, and delivered as one reviewable decision`

**Purpose:** This is the visual centrepiece of the deck. Pay off Slide 1's hook with the full worked example, and simultaneously establish that the product surface is a single decision screen (progressive disclosure), not a dashboard or a chat transcript. Merge what would otherwise be two separate slides — do not split this into a "hero case" slide and a separate "UX" slide; the screenshot *is* the UX proof.

**Exhibit — the actual product screenshot, not a mockup:** use the real Streamlit screenshot at `submission/deck/assets/hero_s1_workspace.png` (captured live from the running app, S1, Workspace tab) as the dominant visual, occupying roughly 60% of the slide width. Beside it, a short annotated list mapping the five things the screen answers, in the order a business user asks them, not the order the system computes them: **What changed? → Why? → Evidence? → How reliable? → What do I do?**

**Content, all drawn from the same real run — label each [S] (synthetic demonstration scenario):**
- Movement: **↓25.0%**, West × Web/Mobile App, 12 Jul → 26 Jul 2026; 52,750 INR against a 211,204 INR baseline. Chip reads **MATERIAL MOVEMENT** — a business rule with both a statistical and a business leg, not a bare percentage threshold.
- Driver: **conversion rate** is the largest contributor, accounting for **more than the whole movement — 109.9%** — because sessions rose and partly offset it. This is an exact LMDI index decomposition that closes to **0.000000000% residual [M]** — call this out explicitly as the single strongest visual proof that the number is computed, not generated: *no language model produces a self-explaining share above 100%.*
- Localisation: most affected slice is channel = Web/Mobile App, region = West.
- Evidence: the live screenshot shows a specific supporting-document count — **read the exact number directly off the screenshot you are given, do not assume 7 or 8.** (Note for the deck author: the business proposal's earlier static mockup said 7; a fresh live capture on 2026-08-24 showed 8 — both are real counts from real runs of the same scenario; the corpus is regenerated between runs. Use whatever the actual embedded screenshot shows and do not silently pick a different number.)
- Reliability: **"High reliability · Correct in 12 of 12 similar past cases"**, with the caveat rendered inline, in the same visual block, never a footnote: *these cases come from a synthetic evaluation set, not production history* **[S]**.
- Recommendation: **"Escalate payment gateway to Engineering"** — owner named (Engineering Lead), monitoring metric named (Checkout Conversion Rate, 2-day window), expected recovery shown as a **range**, **622,121–799,870 INR [I]**, with the basis stated inline: a configured recovery fraction applied to the measured movement — the system reads this figure, it does not estimate it.
- The action button reads **"Raise the request"** — call this out as visual proof of bounded automation (message 3): the system can automate *raising* the request; it cannot automate the technical fix, which stays with the owning team.

**Do not include:** any invented screenshot, any screenshot from a different scenario relabelled as S1, or a redrawn/simplified illustration standing in for the real UI. If the real screenshot cannot be embedded for a technical reason, say so explicitly in speaker notes rather than substituting a mockup silently.

**Sources strip:** Live capture of the running Streamlit app · `eval/attribution_report.md` · `eval/recommendation_report.md`.

---

### Slide 5 — Trust differentiator

**Takeaway title:** `05  |  When evidence conflicts, BusinessIntelligence.ai refuses to manufacture a root cause`

**Purpose:** Prove Core Message 1 with a second real scenario. This is the slide most likely to "win the room" — do not rush it, do not crowd it with other content.

**Exhibit:** A two-column conflict diagram — **Hypothesis A** vs. **Hypothesis B** — converging into a single **"Review Required"** state, rendered as a decision-tree fork rather than a simple table.

**Content, from scenario S2 [S]:**
- Event: South × Apparel, **−21.9%**.
- Hypothesis A: competitive pressure. Hypothesis B: stock availability. Both **equally supported by evidence** and — critically — **implying different owners** (one is a pricing problem, one is a supply problem).
- The system's behaviour: it stops, states the question, and hands it to a person — a real interrupt on a durable checkpoint, not a chat message. Resuming produces the same run with an **identical evidence bundle hash**, so the reviewer's decision attaches to exactly what they reviewed.
- Reliability for this case reads **UNCALIBRATED**, not a fabricated confidence score — because fewer than 10 comparable cases exist in the synthetic evaluation set. State plainly: *the system could not automate this decision even if it wanted to, because the cost arithmetic that would justify automating isn't available.*

**Explicit contrast box (small, two rows, high-contrast):**
| Generic LLM approach | BusinessIntelligence.ai |
|---|---|
| Choose a plausible story | Preserve uncertainty and escalate |

**Closing line for the slide (as a dark band, not a paragraph):** *"A system that always answers cannot be trusted on the answer it gives."*

**Do not include:** the full abstention taxonomy (there are six typed abstention states in the system — do not enumerate all six here; one worked example is stronger than a list). Do not use scenario S4 or S7 here — reserve those for Slide 7's evidence table, where they belong as additional proof points, not narrative centrepieces.

---

### Slide 6 — AI control boundary + architecture

**Takeaway title:** `06  |  Five controlled layers keep the LLM restricted to evidence-backed narration; it never owns the numbers, the data, or the decision`

**Purpose:** The single most technically defensible slide in the deck. Combine the control-boundary argument and the system architecture into one slide — they are the same fact viewed at two levels of detail, and splitting them invites a slide that is architecture for its own sake. Do not put 25 modules on this slide.

**Exhibit — a top-to-bottom layered stack, major components only:**

`User` → `Streamlit (presentation only)` → `LangGraph (workflow orchestration)` → `Semantic contract + Entitlements (row/column/source security, applied before ranking)` → `Detection (STL + robust MAD z-score + PELT)` → `Attribution (LMDI + Adtributor)` → `Evidence Retrieval (hybrid BM25 + dense)` → `EvidenceBundle (frozen, hashed)` → `Verification (10 deterministic checks)` → `LLM (narration only)` → `Recommendation / Deferral` → `Human review / Deliver`

Beside or beneath the stack, a two-column **CAN / CANNOT** box — this is the payload of the slide:

| The LLM CAN | The LLM CANNOT |
|---|---|
| Synthesize a sentence from the frozen evidence bundle | Calculate any KPI or statistic |
| Personalize wording to the persona | Choose the numerical driver or its ranking |
| Explain a decomposition already computed | Query the data warehouse — the request carries no `tools` key, absent, not empty |
| — | Invent or select evidence |
| — | Assign or state a confidence — `Narrative` has no `confidence` field, there is nowhere to write one |
| — | Bypass verification — every narrative passes 10 deterministic checks against the frozen bundle before delivery, or fails closed to a verified template |
| — | Choose or execute what happens next — routing is decided by pure functions over deterministic state, never by reading model output |

**One proof line, stated plainly, not as a boast:** *"The gate has demonstrably blocked our own fallback template when a bug caused it to cite evidence the frozen bundle no longer held — a gate that only ever passes what we produce is not a gate."* **[M]**

**Sources strip:** `docs/FINAL_SYSTEM_ARCHITECTURE.md` · `eval/verification_report.md` · `test_the_client_never_offers_tools` · `test_no_routing_predicate_reads_a_narrative`.

**Do not include:** package names, file counts, LangChain/LangGraph internals, node counts, or any implementation detail below the layer level shown above. A technical judge who wants depth will ask in Q&A — that is what the depth is for.

---

### Slide 7 — Proof

**Takeaway title:** `07  |  The prototype has been tested across eight failure-aware business scenarios, not just the happy path`

**Purpose:** Move from narrative to measured evidence. This slide carries the highest density of numbers in the deck — every one must be labelled with its evidence class, no exceptions.

**Exhibit:** A two-column evidence table (Measured **[M]** | Synthetic evaluation **[S]**) plus a small outcome-split stat row (automate / review / decline).

**Content — Measured on this system [M]:**
- **574** automated tests passing, 0 failures. *(Note: an earlier interim traceability snapshot recorded 571 before later fixes; 574 is the current, final count — use 574.)*
- **8 / 8** scenarios run end to end through the real orchestration graph.
- **8 / 8** agreement between the orchestrated graph and the direct-module path — orchestration changed no decision.
- LMDI identity closure: **0.000000000%** residual.
- **32** security tests, including a 6-stage evidence-leak chain with a non-vacuity control; **0** restricted items reached any stage.
- Orchestration overhead: **13–42 ms (0.08–0.80%)** of total runtime.

**Content — Synthetic evaluation [S], seed 20260821, 6 injected events, ground truth known by construction:**
- Detection precision/recall: **1.000 / 1.000** — state the honest reading inline: recall of 1.000 means every event *injected* was found, and those events were built to be detectable by this method's own assumptions. The figure that is *not* guaranteed by construction — and therefore the meaningful one — is:
- **0 false positives across 48 clean slices.**
- Retrieval: dense recall@10 **0.778**, BM25 recall@10 **0.654** — dense now measurably beats BM25 (the first evidence that **dense retrieval** earns its place — **not** that fusion does: RRF recall@10 is 0.697, *between* the two), after a realism audit widened the document corpus and every retrieval score *fell* (report this direction explicitly — a lower, more honest number is the point, not a weakness to hide).
- Verification: **0 of 10** false acceptances on hand-built corrupt narratives; **0 of 6** false rejections on valid ones.
- Outcome split across the 8 demonstration scenarios: **50% automated · 25% routed to a human · 25% declined.** State plainly that this mix describes a demonstration set built to exercise every terminal state, not a production traffic distribution.

**Do not include:** any number not traceable to `submission/R2_BUSINESS_PROPOSAL_SOURCE.md` or a current `eval/` report. Do not claim live LLM performance, token cost, or latency under a real model — none of that has been measured (no API key was available during development); say so as a stated gap, not silently.

**Sources strip:** `eval/final_evaluation_report.md` · `eval/round2_traceability.md` · `eval/data_realism_audit.md` · `eval/graph_report.md`.

---

### Slide 8 — Business value

**Takeaway title:** `08  |  The value is faster, more governed decision-making — not another AI dashboard`

**Purpose:** State the value mechanism honestly, in four MECE categories, without inventing a dollar figure. This is the slide most likely to be challenged — the discipline here is the credibility asset.

**Exhibit:** A 2×2 or four-column card grid — one card per value category, each with a one-line mechanism and an explicit "what we can/cannot evidence" pair.

**Content — four categories, mutually exclusive, collectively covering the value story:**

1. **Operational** — less manual investigation. *Can evidence:* the pipeline completes and its output is verified, in 4–50 seconds **[M]**. *Cannot evidence:* how much analyst time that displaces — no baseline investigation time has been measured **[A]**.
2. **Decision** — shorter signal-to-action. *Can evidence:* every finding carries an owner, a monitoring metric, and a bounded action **[M]**. *Cannot evidence:* cycle-time reduction in a real organisation **[A]**.
3. **Risk** — fewer unsupported conclusions. This is the strongest, most measured category: 0 false acceptances on corrupt narratives **[S]**, causal licence denied on scenario S3 with the UI degrading to "association only" **[M]**, 25% abstention rate across demonstration scenarios **[M]**.
4. **Governance** — traceability and entitlement. *Can evidence:* every read is audited including denials, correlated to the run the user saw; 15 lineage records per run **[M]**. *Cannot evidence:* that this trail satisfies any specific regulatory regime — no compliance assessment has been performed **[A]**.

**One explicit statement, rendered as its own line, not buried:** *"No revenue, cost-saving, or time-saved figure is claimed anywhere in this project. The recovery range shown in the product is a measured movement multiplied by a configured, stated assumption — not an ROI estimate."*

**Do not include:** any ROI percentage, payback period, market-size figure, or "X hours saved per week" claim. If quantification is requested by the deck format, use only the explicitly labelled assumptions above, never a synthesized new number.

---

### Slide 9 — Pilot / production path

**Takeaway title:** `09  |  A focused pilot can validate decision-time reduction before enterprise-scale deployment`

**Purpose:** Show the credible, sequenced path from what exists today to something an enterprise could actually run, with each step earning the next rather than skipping straight to "scale."

**Exhibit:** Three-stage horizontal flow: `Round 2 Prototype` → `Pilot` → `Production Platform`, each stage with 3–4 bullet specifics, not paragraphs.

**Content:**
- **Now — Round 2 prototype [M]:** 6 KPI contracts, 3 sources, 3 personas, 8 scenarios, 574 tests, single process, synthetic data, no authentication.
- **Pilot — what it must prove:** one real KPI family, one business function, one team, one quarter. The single measurement that would convert the strongest argument in this deck into a data point: **time-to-explanation against the current baseline.** Also in scope for the pilot: enterprise IAM (currently persona is a dropdown — this is a correctness prerequisite, not a scale trigger, and must land *before* any real data touches the system), and real calibration data replacing the 64-case synthetic evaluation set.
- **Production platform — triggered by conditions, not calendar dates:** enterprise data warehouse (trigger: data exceeds one machine, or a second concurrent writer is needed), managed vector search with per-tenant isolation (trigger: the first customer with a data-isolation requirement — **security before scale**, stated as the ordering principle), durable workflow state across processes (trigger: more than one process), a model gateway for key rotation and cost attribution, and observability with retention.

**One explicit exclusion line, stated as a deliberate boundary, not an oversight:** *"Deliberately not on this roadmap: autonomous agents, agent swarms, or letting the model query the warehouse directly. These are not deferred features — they are the architecture this system exists to avoid."*

**Do not include:** a generic "Year 1 / Year 2 / Year 3" timeline with dates — use trigger conditions, exactly as specified in `docs/PRODUCTION_EVOLUTION.md`, because a condition-based roadmap survives a judge asking "what if adoption is slower/faster than planned" and a date-based one does not.

---

### Slide 10 — Closing

**Takeaway title:** `10  |  The next generation of BI should know both why something happened — and when it does not know`

**Purpose:** Land the central thesis in the fewest possible words. This slide should be readable in five seconds from the back of the room.

**Exhibit:** Minimal — a single dark closing band with the thesis statement, optionally paired with a one-line restatement of the three memorable ideas as a small three-item list beneath it (not three more cards — keep this visually quiet after nine dense slides).

**Content (verbatim closing line, do not rephrase):**

> "A dashboard tells you what moved. A language model will tell you why, confidently, whether or not it knows. This system tells you why, shows the evidence, recommends what to do — and tells you when it cannot."

Beneath it, small and quiet, the three ideas as a closing recap (not restated in full, just named):
**It knows when not to answer. Numbers are computed, never generated. Automation is bounded.**

**Do not include:** a call-to-action slide asking for funding/investment (this is a competition submission, not a fundraise), contact information beyond the team name, or any new claim not already established earlier in the deck. Nothing new should appear on the closing slide.

---

## 7. CONTENT GUIDANCE (applies to every slide)

- **One main message per slide.** If you find yourself writing a second unrelated headline-worthy fact into a slide's body, it belongs on a different slide or should be cut.
- **Titles state conclusions, not topics.** Re-verify every slide title against this rule before finalizing: could this title be true of a *different*, worse version of the same slide? If yes, it's a label, not a takeaway — rewrite it.
- **MECE where comparisons are used.** The CAN/CANNOT box (Slide 6), the four value categories (Slide 8), and the three-stage roadmap (Slide 9) are all deliberately structured to be mutually exclusive and collectively covering — do not let categories overlap or leave a gap a judge would ask about.
- **No paragraphs.** Maximum ~20 words per bullet. If a claim needs more explanation than that, it belongs in speaker notes, not on the slide.

---

## 8. EXHIBIT / DIAGRAM GUIDANCE

Use, in this rough distribution across the 10 slides: 2 process-flow/chevron diagrams (Slides 2, 3), 1 layered architecture stack (Slide 6), 1 decision-tree/conflict diagram (Slide 5), 1 real product screenshot as hero visual (Slide 4), 2–3 stat-card rows (Slides 2, 7, 8), 1 evidence table (Slide 7), 1 three-stage roadmap flow (Slide 9). No pie charts, no 3D bar charts, no radial/spider charts anywhere in the deck — none of the underlying data calls for them, and they read as decoration in a consulting-style deck.

Every diagram must be legible as a static image — no diagram should depend on animation, hover states, or click-through to convey its meaning, since judges will review static exports.

---

## 9. DATA / CLAIM RULES

1. **Every number carries its evidence-class letter** — [M] / [S] / [R] / [A] / [I] — visibly, next to the number, not in a legend judges have to cross-reference.
2. **Source of truth for every number:** `submission/R2_BUSINESS_PROPOSAL_SOURCE.md` and the current files under `eval/`. Do not pull a number from an older draft, an earlier stage's report, or an interim snapshot if a newer, final figure exists (e.g., use **574** tests, not the **571** recorded in an earlier traceability snapshot; both numbers exist in the repository, only 574 is current).
3. **If a number differs between two source documents** (this has already happened once: the business proposal's static S1 mockup says "7 supporting documents," while a live screenshot of the running app shows "8"), **use the live, current implementation's number as authoritative**, and note the discrepancy in speaker notes rather than silently picking one. Never fabricate a reconciled third number.
4. **Never invent:** ROI, cost savings, revenue impact, market share, customer/user counts, adoption figures, productivity-gain percentages, unqualified "accuracy," production-grade performance figures, or live LLM latency/cost/token figures. None of these exist in the evidence base — search for them before writing and if you cannot find a source citation, do not include the claim.
5. **Never say:** "real-time" (a run takes 4–50 seconds), "production-ready" or "enterprise-ready" (the architecture doc argues the opposite explicitly), "autonomous" as an affirmative claim (it appears in this project only as a negation — "not an autonomous agent framework"), or "accurate" without naming the dataset it was measured on.
6. **Synthetic-data honesty:** every evaluation number must be visibly labelled as measured on a *synthetic, seeded dataset with ground truth known by construction* — this is not a weakness to downplay, it is the honest scope of a prototype-stage evaluation, and stating it plainly is itself a credibility signal to a skeptical judge.

---

## 10. SCREENSHOT GUIDANCE

- **Slide 4 is the only slide requiring a mandatory real product screenshot**: `submission/deck/assets/hero_s1_workspace.png`, a live capture of the running Streamlit app (scenario S1, Workspace tab), captured via Playwright — not a mockup, not a redrawn illustration. Embed it directly; do not simplify or re-skin it.
- **Slide 5 (trust differentiator, scenario S2) and Slide 7 (proof) would be strengthened by additional real screenshots** of the S2 "awaiting review" state and, optionally, the S4 sparse-history abstention state, if such captures exist or can be produced using the same method as the S1 capture (`submission/deck/render/_capture_hero.py`, adapted to select scenario S2/S4 before capturing). If no such screenshot is available at generation time, use the labelled diagram/decision-tree exhibit specified for that slide instead — **do not fabricate a screenshot-style image**; a clearly-labelled diagram is honest, a fake screenshot is not.
- No screenshot may be cropped, edited, or annotated in a way that changes any number or word it displays. Callout arrows/highlights drawn *around* a screenshot are fine; altering pixels *inside* it is not.

---

## 11. SPEAKER NARRATIVE GUIDANCE

For every one of the 10 slides, generate separately (not printed on the slide itself):

- **1-sentence purpose** — what this slide must accomplish in the pitch.
- **2–4 talking points** — short, spoken-register sentences, not a restatement of the slide's bullets.
- **One transition sentence** into the next slide.

Total spoken narrative across all 10 slides should fit a **5–7 minute pitch** comfortably, and a **3-minute cut** should be achievable by speaking only Slides 1, 3, 4, 5, and 10 in full and summarizing the rest in one sentence each — design the talking points so this compression is possible without rewriting them. The deck must remain understandable from the slides alone even if the presenter skips talking points under time pressure.

---

## 12. DESIGN-SYSTEM INSTRUCTIONS

Reuse the Round 1 identity as the literal source of truth for every visual token (see Section 4). If BrightDeck's own default consulting template conflicts with any token specified in Section 4 (a different purple, a different title grammar, a sans-serif other than Arial), **the Section 4 specification wins** — do not let a platform default silently override the recovered Round 1 identity. If BrightDeck cannot exactly reproduce a token (e.g., exact hex match), choose the nearest available equivalent and keep every other token exact.

One optional treatment, use only if the deck format has room and it does not cost a numbered slide: a single small transitional band or sub-header, appearing once (e.g., faintly behind Slide 3's title bar or in Slide 3's footnote), reading *"Round 1 proposed the vision. Round 2 built and stress-tested it."* — do not turn this into a full retrospective slide; it is a one-line continuity signal, not deck content.

---

## 13. WHAT NOT TO DO

- Do not produce a technical-documentation deck — no package/module lists, no dependency graphs, no test-suite directory structures.
- Do not produce a generic AI-startup pitch — no "market opportunity" TAM/SAM/SOM slide, no funding ask, no team-bio slide beyond what the closing frame already carries.
- Do not produce a chatbot demo — there is no chat interface in this product; do not draw one.
- Do not list LangChain/LangGraph or any other library/framework name on any customer-facing slide (they may appear only in Slide 6's architecture stack as generic layer labels, e.g., "workflow orchestration," not as a branded technology showcase).
- Do not invent any number, screenshot, quote, or company logo not present in the source material listed in Section 9.
- Do not add slides beyond the 10 specified, even if the format has visual room — pad with whitespace or larger exhibits instead, never with a new eleventh idea.
- Do not soften or omit the stated limitations (no ROI claimed, no real-data validation, no live LLM evaluation, no authentication) — their presence, clearly labelled, is what makes every other claim in the deck credible.
- Do not use decorative stock photography, 3D renders, or generic "AI brain/network" imagery anywhere.

---

## 14. FINAL QUALITY CHECKLIST (BrightDeck: verify before finalizing)

- [ ] Exactly 10 content slides, numbered 01–10, each with a claim-not-label title.
- [ ] Slide 4 contains the real embedded screenshot, not a redrawn mockup.
- [ ] Every number on every slide carries a visible [M]/[S]/[R]/[A]/[I] tag.
- [ ] No ROI, revenue, cost-saving, adoption, or market-size figure appears anywhere.
- [ ] No occurrence of "real-time," "production-ready," "enterprise-ready," or an affirmative use of "autonomous."
- [ ] Every content slide ends with a non-empty sources strip.
- [ ] Palette, typeface (Arial), canvas size (1600×900), and title grammar match Section 4 exactly.
- [ ] The three core messages (abstention, computed-not-generated, bounded automation) are each clearly carried by at least one dedicated slide (5, 6/4, 4/6 respectively) and are restated in the closing recap.
- [ ] Speaker notes exist for all 10 slides in the specified purpose/talking-points/transition format, and the 3-minute compression path (Slides 1, 3, 4, 5, 10) is achievable.
- [ ] Nothing on the closing slide is a new claim not already established earlier in the deck.
