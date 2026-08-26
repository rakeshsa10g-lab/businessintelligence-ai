# Claim audit

Every significant claim this project makes, classified by what actually backs
it. The purpose is not to remove synthetic results — they are legitimate and
they are most of what a prototype can produce — but to make sure no reader can
mistake one class of evidence for another.

| Class | Meaning |
|---|---|
| `MEASURED` | Observed by running the system. Reproducible from this repository. |
| `SYNTHETIC_EVALUATION` | Real measurement, on a dataset this repository generates and whose ground truth it therefore knows by construction. |
| `RESEARCH_SOURCED` | From a cited external paper. Not our result. |
| `ASSUMPTION` | A configured value chosen to make the system demonstrable. Not derived from data. |
| `ILLUSTRATIVE` | A worked example. Directionally meaningful, numerically arbitrary. |

---

## 1. Detection

| Claim | Class | Backing | Correction applied |
|---|---|---|---|
| Precision 1.000, recall 1.000 | `SYNTHETIC_EVALUATION` | `eval/detection_report.md`, 64 slices, 16 injected events | **Yes.** The report carried **no provenance marker at all** — the single most overstate-able number in the project. A banner now names the dataset and adds: a recall of 1.000 means every *injected* event was found; the injected events were built to be detectable by this method's own assumptions |
| STL/MAD/PELT is appropriate for this data | `ASSUMPTION` | Method choice justified in ADR-015–017 | Unchanged — the reasoning is documented |

## 2. Attribution and causality

| Claim | Class | Backing | Note |
|---|---|---|---|
| LMDI identity closes to 0.000000000% | `MEASURED` | `eval/attribution_report.md` | Exact arithmetic property, not a fit quality. Reproducible |
| Conversion rate contributes 109.9% of the S1 movement | `SYNTHETIC_EVALUATION` | LMDI on generated data | The UI states *why* it exceeds 100% rather than printing a bare figure |
| "A product or platform failure caused the decline" | **Licensed, not asserted** | `causal_language_licensed` from difference-in-differences | The strongest guard in the system: causal wording is permitted only when the counterfactual passes, and Gate 2 rejects it otherwise. On S3 the licence is **denied** and the UI says "Association only" |
| Adtributor / LMDI are the right methods | `RESEARCH_SOURCED` | Bhagwan et al. NSDI '14; LMDI literature | Cited in the architecture |

## 3. Confidence and calibration

| Claim | Class | Backing | Note |
|---|---|---|---|
| "Correct in 12 of 12 similar past cases" | `SYNTHETIC_EVALUATION` | 64-case seeded calibration set | Always rendered with "These cases come from a synthetic evaluation set, not from production history" **in the same block** — never a footnote |
| HIGH band ⇒ p(model correct) = 0.929 | `SYNTHETIC_EVALUATION` | Laplace-smoothed 12/12 | 12/12 is deliberately *not* treated as 100%: raw 1.0 made the deferral rule degenerate to "always automate" |
| MEDIUM / LOW reliability | **Not claimed** | Below the 10-case floor | Reported as `UNCALIBRATED`. The system says it does not know how often a medium call has been right, because it does not |
| Confidence weights | `ASSUMPTION` | `config/confidence.yaml` | Chosen, not learned. Stated in the Method tab: "The weights are configuration, not learned" |

## 4. Business impact

| Claim | Class | Backing | Note |
|---|---|---|---|
| "Expected recovery 622,121 – 799,870 INR" | `ILLUSTRATIVE` | Configured recovery fraction × measured movement | Always a **range**, never a midpoint, with the basis named inline: "it applies a configured recovery fraction to the movement detection measured. The system does not estimate this figure — it reads it" |
| `recovery_fraction: 0.90 / 0.70` | `ASSUMPTION` | `config/levers.yaml` | Not derived from any historical intervention |
| Decision values (500k / 750k / 2M INR per persona) | `ASSUMPTION` | `config/deferral.yaml` | Plausible placeholders. They move the automate/defer boundary directly — stated in `eval/recommendation_report.md` |
| `p_human` per cause bucket | `ASSUMPTION` | `config/deferral.yaml` | **Seeded, not measured.** The human arm of the comparison rests on an assumption until real escalations resolve |
| "Automating saves ~74,679 INR of expected risk" | `ILLUSTRATIVE` | Arithmetic over two assumptions above | Correct arithmetic on inputs that are themselves assumptions |

**No claim of revenue impact, cost reduction or time saved is made anywhere.**
Searched for; none found. The impact figure is explicitly a *recovery
potential of a measured movement*, not a benefit attributed to the product.

## 5. LLM quality

| Claim | Class | Backing |
|---|---|---|
| Gate 2 catches numeric, driver and causal violations | `SYNTHETIC_EVALUATION` | 10 hand-written corrupt narratives; 0 false acceptance |
| Retry is capped at one | `MEASURED` | A narrator that raises every time terminates after exactly 2 calls |
| The model never sees a tool | `MEASURED` | Asserted against the recorded request, not the code that builds it |
| First-pass verification rate, latency, tokens, cost | **`LIVE LLM EVALUATION PENDING`** | No API key. **Not estimated** |

The verification report's "0 false acceptance" now carries a caveat: none of
*those* got through — not that no corrupt narrative could.

## 6. Performance

| Claim | Class | Backing |
|---|---|---|
| Graph overhead 13–40 ms (0.08–0.78% on real work) | `MEASURED` | `eval/graph_report.md`; one machine, warm caches |
| S1 end-to-end ~49 s | `MEASURED` | Includes a ~35 s cold model load, reported unadjusted |
| 574 tests | `MEASURED` | Full suite; also verified on a clean CI runner |
| Concurrency / scale behaviour | **Not claimed** | Single-process prototype; untested |

## 7. Security

| Claim | Class | Backing |
|---|---|---|
| Restricted evidence never reaches SQL, ranking, bundle, payload or UI | `MEASURED` | `tests/test_security_chain.py`, 9 tests, with a non-vacuity control |
| One DuckDB caller | `MEASURED` | `tests/test_chokepoint.py` |
| Audit row per read including denials | `MEASURED` | `audit_log`; correlation fixed in Stage 12 |
| "Enterprise-ready" / "production-ready" | **Never claimed** | Searched; no occurrence. `docs/PRODUCTION_EVOLUTION.md` states the opposite |

## 8. Research citations

All external results in `docs/ROUND1_MASTER.md` and
`ROUND2_TECHNICAL_ARCHITECTURE.md` are `RESEARCH_SOURCED`, carry an arXiv or
venue link, and — where relevant — carry the paper's own caveat. The CALM
citation, for example, is recorded with the fact that it *degraded* results on
some datasets, which is why the LLM judge is advisory-only here.

---

## Corrections made during this audit

1. **`eval/detection_report.md`** — "Precision 1.000 / Recall 1.000" had **no** statement of provenance. Now carries a `SYNTHETIC_EVALUATION` banner naming the seed, the injected events, and the specific limitation that recall over injected events is not recall over reality.
2. **`eval/retrieval_report.md`** — added; relevance labels come from a generated benchmark, not human judgement.
3. **`eval/verification_report.md`** — added; "0 false acceptance" now says none of *those* narratives got through, not that none could.
4. **`eval/graph_report.md`** — added; runtimes are one machine, warm caches, single process.
5. Banners are emitted from a shared `eval/provenance.py` so the four reports cannot drift into describing the same dataset differently.

## Claims deliberately kept despite being synthetic

Removing them would hide real properties of the system:

- Detection precision/recall — a real property of the method on a stated dataset.
- The 12/12 calibration — real counts, correctly caveated, and the Laplace smoothing exists precisely because the raw figure would have been misread by the *system itself*.
- Impact ranges — the alternative is showing no impact estimate, which makes the recommendation less actionable without making it more honest.

---

# Stage 13 re-audit

Re-run against the additional terms the final brief names: *autonomous*,
*intelligent*, *real-time*, plus a second pass on impact language.

## New term sweep

| Term | Occurrences in user-facing text | Verdict |
|---|---|---|
| **"autonomous"** | 0 in UI. In docs only as a **negation** — "no autonomous agents", "not an agent framework", `test_no_autonomous_agent_constructs` | ✅ correct usage |
| **"intelligent"** | 0 outside the product name `BusinessIntelligence.ai` | ✅ |
| **"real-time"** | **0** | ✅ correct — the system is not real-time. A run takes 4–50 s and the UI says so |
| **"production-ready" / "enterprise-ready"** | **0** | ✅ `docs/PRODUCTION_EVOLUTION.md` argues the opposite |
| **"accuracy"** | Only in `SYNTHETIC_EVALUATION`-banner context | ✅ |

## Claims changed by the Stage 13 data work

The realism audit widened the document corpus, which **moved measured
numbers**. Every affected claim is restated here rather than silently updated.

| Claim | Was | Now | Class |
|---|---|---|---|
| BM25 precision@5 | 0.810 | **0.552** | `SYNTHETIC_EVALUATION` |
| BM25 recall@10 | 0.957 | **0.654** | `SYNTHETIC_EVALUATION` |
| Dense recall@10 | 0.933 | **0.778** | `SYNTHETIC_EVALUATION` |
| RRF MRR | 0.964 | **0.838** | `SYNTHETIC_EVALUATION` |
| "Hybrid did not beat BM25 on this corpus" | true, and conceded | **partly superseded, and re-corrected.** Dense beats BM25 on recall@10 by 19% relative — that justifies *dense*, not fusion. RRF recall@10 (0.697) sits **between** BM25 (0.654) and dense (0.778), so hybrid still does not beat the best single method. An intermediate revision of the deck overstated this as "the hybrid retriever earns its place"; corrected | `SYNTHETIC_EVALUATION` |
| Detection precision/recall | 1.000 / 1.000 | **unchanged** | `SYNTHETIC_EVALUATION` |
| Corpus size | 1,341 documents | **1,336** | `MEASURED` |

**The direction matters.** Every retrieval figure got *worse*, because the
previous corpus held only 13 distinct texts across 895 documents and was
making retrieval close to a lookup. The lower numbers are the more truthful
ones, and they are the first evidence that the hybrid retriever earns its
place.

## Corrections made in Stage 13

| # | Claim | Where | Correction |
|---|---|---|---|
| 1 | "no names, emails, addresses" | `eval/security_audit.md` | **Overstatement.** `fact_orders.customer_email` exists — 91,329 synthetic `@example.com` values. RFC 2606 reserved, in no KPI `column_map`, unreachable through the gateway. Corrected in place rather than deleted |
| 2 | "The deterministic template cannot fail by construction" | `graph/nodes.py`, `docs/*` | **False.** It failed Gate 2 on S2 with two dangling citations. It was unfailable by *luck*. Builder fixed; docstring corrected to say so |
| 3 | Retrieval figures | `eval/retrieval_report.md` | Regenerated on the wider corpus |

## The one claim I want a judge to test

> *"Every number a user sees is computed by SQL, statistics or a business rule
> — never generated."*

This is the project's central claim and it is `MEASURED`, not asserted:

- Gate 2's numeric allowlist extracts every figure from the narrative and rejects any not derivable from the frozen bundle.
- The narration request carries **no `tools` key** — asserted against the recorded request, not the code that builds it.
- `Narrative` has **no `confidence` field** — there is nowhere to write one.
- 0 false acceptances across 10 hand-built corrupt narratives.

The strongest supporting evidence is that Gate 2 **blocked our own template**
in Stage 13. A gate that only ever passes what we produce is not a gate.
