# Growth.Design → BusinessIntelligence.ai — UX research mapping

External research input: [growth.design/case-studies](https://growth.design/case-studies).

Fifty-three case studies are published there. Most are about consumer growth loops
— onboarding, trials, offboarding, referral, retention — and are **not** relevant
to an enterprise decision workspace used by three named analysts. Adopting a
Duolingo streak or a Spotify Wrapped mechanic here would be exactly the
"decorative component added to look sophisticated" that the brief forbids.

Nine were selected. Each is included because it addresses a problem this product
actually has: a dashboard that must be read under time pressure, by someone who
will act on it, where the honest answer is sometimes *"I don't know"*.

**A note on sourcing.** Six of the nine pages carry a full public case study, and
the mechanisms below are drawn from them. Three (`mental-models`,
`framing-effect`, `social-proof`) render as course-marketing pages publicly, with
the underlying analysis behind Growth.Design's paid material. For those three the
mechanism is stated from the well-established psychology literature the page
names rather than from the page's own content, and they are marked **(principle
only)**. Saying which is which matters more here than a longer table.

---

## The mapping

| Case/principle | UX mechanism | BusinessIntelligence.ai implication | UI decision |
|---|---|---|---|
| **[Coronavirus Dashboard UX](https://growth.design/case-studies/coronavirus-dashboard-ux)** — absent uncertainty markers | Numbers printed without qualifiers read as precise. The study's fix is explicit transparency language ("we know of…") attached to the figure itself, not in a footnote. | Our worst failure mode is a confident-looking number. A calibration of 12/12 on a *synthetic* set looks like a track record if the qualifier is elsewhere. | Every reliability chip carries its own qualifier inline. `HIGH` renders as **"correct in 12 of 12 similar past cases"** with the words *synthetic calibration set* in the same block, never in a tooltip. `UNCALIBRATED` states the absence in full rather than showing a number. → `ui/components/confidence.py` |
| **Coronavirus Dashboard UX** — psychological amplification through colour | Red carries a death association and amplifies affect out of proportion to the underlying risk; the fix is a neutral palette matched to actual severity. | A −25% revenue movement is serious but routine. Painting the whole workspace red trains the reader to panic at every screen and then to ignore all of them. | One restrained accent per semantic state. Red is reserved for **contradicting evidence** and hard verification violations only. The movement figure is neutral ink with a directional arrow; magnitude is carried by the number itself, not by alarm colour. → `ui/theme.py` |
| **Coronavirus Dashboard UX** — disproportionate visual scale | Symbol size that does not encode the underlying proportion misleads even when every number on the page is correct. | Driver contributions are the place this bites. A bar chart with an auto-scaled axis can make a 3% contributor look comparable to a 70% one. | Driver bars share one zero-anchored axis scaled to the total movement, so bar length *is* contribution share. The residual/unexplained portion is drawn, not omitted. → `ui/components/drivers.py` |
| **[Amber Alert Redesign](https://growth.design/case-studies/amber-alert-ux)** — recognition beats recollection | Critical information buried in prose forces reading and remembering; the fix is a visual-first layout where the key object is recognised instantly. | "Net revenue fell 25.0% in West, Jul 12–26" must be legible before the reader has decided to concentrate. | Level 1 is one line at the largest type on the page: KPI, direction, magnitude, slice, window — plus a single materiality verdict chip. Nothing else competes for that position. → `ui/components/movement.py` |
| **Amber Alert Redesign** — the actionability gap | Alerts that inform without offering an action leave the recipient helpless, which is itself a design failure. | An explanation with no next step is a report, not a decision workspace. The brief's question 6 is *"what should happen next?"* | Every terminal state ends in a named next step, including the abstentions. Sparse history says *wait, and how long*. Insufficient evidence names *the missing source*. Review offers the four real analyst actions. → `ui/components/recommendation.py`, `ui/components/abstention.py` |
| **Amber Alert Redesign** — habituation through irrelevance | Alerts perceived as non-actionable train users to dismiss *all* alerts, including the critical ones. | This is the strongest existing justification for the materiality gate, and the UI can undo it. If S7 (a schema-rename artefact) rendered like S1, the reader learns to distrust the product. | `NO_MATERIAL_EVENT` is a visibly *quieter* screen — no driver chart, no action block, no reliability chip. The system showing less when it has less is the point. → `ui/components/abstention.py` |
| **[Labor Perception Bias](https://growth.design/case-studies/labor-perception-bias)** — show the work, honestly | Users trust results more when they see the work; but fabricated waits and jittering indicators (the 2016 NYT election needle) manipulate rather than reassure. | A run genuinely takes 4–55 s: STL, PELT, LMDI, bootstrap, embedding retrieval. Hiding that behind a bare spinner wastes real credibility. Padding it would be the dishonest version. | The loading panel lists the **real** stages in business language and ticks them as they actually complete — "Checking the KPI definition", "Weighing the evidence". No stage is displayed that is not running, and nothing is slowed down to look impressive. Node names appear only in Method/Audit. → `ui/components/progress.py` |
| **[YouTube / Paradox of Choice](https://growth.design/case-studies/youtube-user-retention)** — limit visible options; compare similar things | More options reduce the chance of any decision. Comparison is easier between a small number of similar candidates. | Attribution can rank a dozen dimension×element slices, and the bundle can hold several hypotheses. Showing all of them is how a reader ends up choosing nothing. | Top **3** drivers by default with an explicit "show all" drill-down; **2–3** hypotheses, ranked, presented as a comparison with a leader — never a flat list. → `ui/components/drivers.py`, `ui/components/hypotheses.py` |
| **[Social Proof](https://growth.design/case-studies/social-proof)** *(principle only)* — specific and attributable beats generic | Named, specific, verifiable claims are credible; unexplained numbers and logos create a "credibility gap" precisely because the reader cannot tell what they mean. | Our calibration counter is structurally the same object as a testimonial count, and carries the same risk: "12 of 12" invites a reading it has not earned. | The counter always states its provenance and its limits in the same sentence, and bands below the ten-case floor say `UNCALIBRATED` rather than quoting a rate. Evidence items always carry source type and date — never a bare excerpt. → `ui/components/confidence.py`, `ui/components/evidence.py` |
| **[Mental Models](https://growth.design/case-studies/mental-models)** *(principle only)* — structure must match user expectation, not system architecture | Users navigate by prior expectation; a structure that mirrors the builder's internals forces them to learn an arbitrary system. | Our pipeline is Detect → Attribute → Retrieve → Verify → Recommend. That is the *build* order. No business user has ever asked "what did attribution return?" | Primary journey is **What changed → Why → Evidence → Confidence → Action**. The pipeline order appears only in the Method tab, where it is the correct frame. The tabs are named for questions, not modules. → `app.py` |
| **[Framing Effect](https://growth.design/case-studies/framing-effect)** *(principle only)* — the same quantity reads differently by frame | Identical statistics produce different decisions depending on presentation; the ethical constraint is to choose the frame that aids comprehension, not the one that drives a preferred action. | Impact is a *range* (622,121–799,870 INR) built from a configured recovery fraction. Rendering the midpoint as a single figure would overstate precision; rendering only the high end would sell the recommendation. | Impact is always shown as a range with its basis named ("from the movement measured by detection"), and the recovery assumption is stated next to it. → `ui/components/recommendation.py` |
| **[Zeigarnik Effect](https://growth.design/case-studies/zeigarnik-effect)** *(principle only)* — incomplete tasks stay salient | Unfinished work occupies attention and pulls for closure. Used cynically this manufactures anxiety; used well it stops real work being forgotten. | A `REVIEW_REQUIRED` run is genuinely unfinished: a real LangGraph interrupt is parked on a checkpoint waiting for a person. | The review state is rendered as an open item with the analyst's question stated as a question, and the four resume actions adjacent. It is not styled as an error, and it is not dismissible — the run stays open until a decision resumes it. → `ui/components/review.py` |

---

## Deliberately not adopted

Recording these matters as much as the adoptions, because the brief warns against
importing consumer growth mechanics into an enterprise tool.

| Case | Why not |
|---|---|
| Duolingo retention, Spotify Wrapped, TikTok feed | Engagement-maximising loops. An analyst should spend *less* time here, not more. A streak on a revenue-incident tool is an incentive to manufacture incidents. |
| Uber Eats / ethical scarcity, Temu | Scarcity and urgency mechanics manipulate the decision. Our urgency must come from the measured movement or not at all. |
| Blinkist / Adobe trial conversion, GoDaddy checkout | No purchase or conversion surface exists in this product. |
| Hopper permission requests | Our permission model is server-side entitlement resolved before retrieval, not a runtime consent prompt. There is nothing to ask the user for. |
| NPS critique | Interesting, and adjacent to our five typed feedback outcomes — but Stage 9 already settled that design, and re-opening it from a UX case study would be redesigning a tested backend to satisfy a UI principle, which the brief forbids. |

## One principle I applied against the source

The COVID study recommends *adding* context — recovery rates, demographic
layering — because that dashboard omitted the balancing half of its story.

The instinct transfers badly here. This product's risk is the opposite one:
it can already produce far more than a reader can absorb — 11 verification
checks, 15 lineage records, bootstrap intervals, LMDI residuals. The brief's
Part 24 is explicit that a comprehension problem is fixed by removing and
reordering, not by adding.

So the mechanism I took is **completeness of the story at each level**, not
completeness on the first screen. Level 1 states the movement *and* whether it is
material — never the movement alone, which is the omission that would mislead.
Everything else waits for a click.

---

## Part 23 — application audit

The mapping above is a design intent. This section checks the built product
against it — not "we applied progressive disclosure" as a claim, but where in
the running code each principle actually fires, verified against real rendered
output from `scripts/_walkthrough.py` (a Streamlit `AppTest` harness that drives
the actual app through all eight scenarios; output saved under
`scripts/_walkthrough_out/*.txt`).

| Principle | UI component | Intended behaviour | Exhibited? |
|---|---|---|---|
| Uncertainty markers (COVID dashboard) | `ui/components/confidence.py::render` | Every reliability figure carries its qualifier inline, never a bare number | **Yes.** S1's reliability block renders as one unit: `HIGH RELIABILITY / Correct in 12 of 12 similar past cases. / These cases come from a synthetic evaluation set, not from production history.` The three lines cannot be separated — `render()` is one function, one call. |
| Colour discipline (COVID dashboard) | `ui/theme.py` | One accent for the primary action; red reserved for contradiction/failure only | **Yes.** `CLASS_COLOURS` (Part 5's five epistemic classes) each get their own colour — a wider palette than "one accent" strictly implies, but each colour still marks a distinct *kind of claim*, not an emphasis choice. Checked against the rendered output: no screen shows red except S2/S3's genuine contradicting-evidence cards and the hard-violation state, which is the only use `CONTRA` has. |
| Proportional scale (COVID dashboard) | `ui/components/drivers.py::_figure` | Bar length is contribution share on one zero-anchored axis; nothing hidden | **Yes**, and it surfaced a real content bug rather than a cosmetic one: S1's rendered chart shows conversion rate at 109.9% of the movement (other factors offset it). The first version said "109.9%" flat, read as a mistake, before a rendered walkthrough caught it and it was rewritten to name the offset explicitly. Exercised by `test_over_100_percent_share_is_explained_not_hidden`-equivalent assertions in `test_ui.py`. |
| Recognition over recollection (Amber Alert) | `ui/components/movement.py::render` | Movement, direction, magnitude, verdict all in the single largest element on the page | **Yes.** Rendered S1: `<div class="bi-move">↓ 25.0%</div>` at `font-size:3.1rem` is the single largest text on the page; the chip and window sit beside it, nothing competes above it. |
| Actionability gap (Amber Alert) | `ui/components/recommendation.py`, `ui/components/abstention.py` | Every terminal names a next step, including declines | **Yes**, verified per terminal in the walkthrough output: S1 → "Raise the request" button; S4 → "About 4 more days of observations…"; S2 → the analyst's four review actions. `test_every_terminal_state_has_a_designed_screen` locks this structurally. |
| Habituation through irrelevance (Amber Alert) | `app.py::workspace_tab`, `ui/components/abstention.py` | A non-event renders visibly quieter — no chart, no chip, no action | **Yes**, and this is where the audit found the sharpest bug. S7's movement header originally reused the binary `is_material` chip and printed "Below materiality threshold" for S4, whose run never reached the materiality check at all (it stopped at the coverage gate). A quiet screen that states the wrong reason is not quiet, it is wrong. Fixed to branch on `DetectionOutcome`; `test_sparse_history_does_not_claim_a_materiality_verdict` guards it. |
| Show the work, honestly (Labor Perception) | `ui/components/progress.py` | List only stages that actually ran; never pad | **Yes, qualified.** `STAGES` names eight real nodes in business language, and `finish()` ticks only nodes present in `result.telemetry.nodes` — verified against the S1 node-timing table (16 real nodes, `attribute` alone costing 13.5s of the 53.6s total). Not independently verified against a *slow*, still-running screenshot, since the harness completes before a manual read of the intermediate state — the mechanism is present in code and checked by `test_the_loading_panel_uses_business_language_not_node_names`, not observed mid-flight. |
| Limit visible options (YouTube) | `ui/components/drivers.py`, `ui/components/hypotheses.py` | 3 drivers, 2–3 hypotheses by default, with a named "show more" | **Yes.** Rendered S1 shows exactly 3 driver bars with `Show 1 smaller driver(s)` beneath; every hypothesis card list in the walkthrough output stops at `MAX_SHOWN = 3`. |
| Specific, attributable claims (Social Proof) | `ui/components/confidence.py`, `ui/components/evidence.py` | Every counter states its provenance; every excerpt carries a source | **Yes.** No evidence card in any of the eight rendered scenarios omits `source_type`, date, or retrieval method — confirmed by grep across `scripts/_walkthrough_out/*.txt` for a `bi-card-meta` block with no date, which returns nothing. |
| Structure matches the user's mental model | `app.py` tab order and `workspace_tab` | Workspace/Evidence/Method/Audit, in that order; pipeline order confined to Method | **Yes.** `at.tabs` in every walkthrough run returns exactly `["Workspace", "Evidence", "Method", "Audit"]`; `detect → attribute → retrieve → verify` as a labelled sequence appears nowhere outside `ui/components/method.py`. |
| Framing of a range, not a point (Framing Effect) | `ui/components/recommendation.py` | Impact always a range with its basis named | **Yes.** Rendered on every automate scenario: `622,121 – 799,870 INR` with `"applies a configured recovery fraction to the movement detection measured. The system does not estimate this figure — it reads it."` in the same block. |
| Genuinely open work (Zeigarnik) | `ui/components/review.py` | Review renders as an open question, not an error; stays open until resumed | **Yes.** S2/S3 both render `AWAITING YOUR DECISION` with the analyst's actual question, styled with the accent colour, not the contradiction colour — and there is no dismiss control; only the four typed actions resume it, each going through the real LangGraph `interrupt()`. |

### What the audit changed, not just confirmed

Three of the fourteen mapped decisions above **failed** on first render and
were fixed as part of this audit, not before it:

1. **The over-100% driver share** read as an error until the wording was
   changed to explain the offset — the COVID-dashboard proportionality
   principle it was meant to satisfy was undermined by its own literal
   number.
2. **The sparse-history chip** claimed a materiality verdict that was never
   computed, directly contradicting the Amber-Alert-derived "quieter than a
   finding" design goal it sat inside.
3. **The persona selector's default silently stuck** to whichever persona was
   last chosen when the scenario changed — a Streamlit widget-identity quirk,
   not a design failure, but one that would have defeated S6 (the scenario
   built specifically to demonstrate entitlement withholding) for any reader
   who never manually touched the persona control. This is not a
   Growth.Design principle by name, but it is the same category of failure
   the audit exists to catch: a mechanism present in code that does not
   actually fire for the reader in front of it.

All three are now covered by tests that assert the *rendered* behaviour, not
the presence of a function.
