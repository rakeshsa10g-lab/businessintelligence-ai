# Synthetic data realism audit

The prototype legitimately uses simulated data — the Round 2 case explicitly
says teams are not expected to have real proprietary data. The question this
audit asks is different and harder:

> **Is the data constructed so that the correct answer is trivially available,
> rather than requiring the analytical pipeline?**

The answer, before this audit, was **partly yes** — in one specific and
material way. It has been fixed, and the fix made the measured numbers *worse*.

---

## Headline finding

| | Before | After | |
|---|---:|---:|---|
| Distinct support-ticket bodies | **13** / 895 (1.5%) | **30** / 895 (3.4%) | |
| Distinct CRM note bodies | 5 / 334 (1.5%) | 12 / 329 (3.6%) | |
| Distinct texts among E1's 34 planted tickets | **5** | **11** | |
| BM25 precision@5 | 0.810 | **0.552** | ↓ |
| BM25 recall@10 | 0.957 | **0.654** | ↓ |
| Dense recall@10 | 0.933 | **0.778** | ↓ |
| Hard negatives in top 5 | **0** | **2–3** | ↑ |

Every retrieval number fell. That is the point: the previous corpus contained
**13 distinct strings repeated verbatim across 895 documents**, which made
retrieval close to a lookup table rather than a search problem.

**The change also resolved a standing embarrassment in the retrieval report.**
It previously had to concede that hybrid retrieval did not beat BM25 —
*"hybrid is insurance we can afford, not hybrid improved our numbers"*. On a
13-template corpus there were no paraphrases for dense retrieval to catch, so
the capability that justifies it was invisible. On the wider corpus **dense
recall@10 (0.778) now clearly beats BM25 (0.654)**.

### What was preserved

The change was made to the generator's language pools only:

- `data/ground_truth.json` — **byte-identical** (verified by `git diff`).
- `data/scenario_manifest.json` — **byte-identical**.
- Planted evidence per event — unchanged: E1 34 tickets + 1 market event, E2 11 CRM + 6 market, E3 2, E4 4, E5 12, E6 5.
- Detection: **precision 1.000, recall 1.000, 16 TP, 0 FP, 0 FN** — unchanged.
- All 8 scenario terminals and decisions — unchanged; graph still agrees 8/8 with the direct-module path.

Only *background* CRM volume shifted (334 → 329), because adding a random draw
for paraphrase selection moved the generator's RNG stream. A test that pinned
the corpus size to the literal `1341` failed on this and was corrected to
derive the expected size — a literal count cannot distinguish a legitimate
regeneration from a corpus dropping rows.

---

## Structured data

| Property | Finding | Verdict |
|---|---|---|
| **Magnitudes** | Daily net revenue in the hundreds of thousands INR; order values realistic for the modelled retailer | ✅ plausible |
| **Dimensions** | 4 regions, 3 segments, 5 product categories, 5 channels | ✅ realistic cardinality |
| **Volume** | 105,216 orders / 205,440 sessions / 821,760 funnel steps over 535 days | ✅ |
| **Seasonality** | Day-of-week structure present; STL is configured with period 7 and finds it | ✅ |
| **Refresh cadence** | Genuinely heterogeneous: S1 daily, S2 hourly, S3 weekly at T+3 | ✅ load-bearing, not cosmetic |
| **Missingness** | ~3.5% null `region` in `fact_sessions` (unknown geo) | ✅ forces a real completeness check |
| **Schema drift** | `marketplace` → `Marketplace` renamed mid-series on 2026-06-14; both spellings persist | ✅ this is E5/S7 |
| **Outliers** | The injected events are themselves the outliers | ⚠ see limitation 2 |

### Deliberate quirks that make the data non-trivial

Recorded in `data/SCENARIOS.md` and each one exists to defeat a naive approach:

1. **The Monday spike in support-ticket volume** — a naive day-over-day count comparison mis-reads every Monday as signal.
2. **The T+3 finance watermark** — the most recent week is genuinely unavailable, not zero. A system that treats absent as zero reports a false collapse.
3. **The channel rename** — severs the series into 164 + 65 days unless stitched. Detection stitches and correctly does **not** fire a material event at the rename; that is scenario S7.
4. **`NewLaunch` has no history before 2026-06-27** — 52 of the 56 days a seasonal baseline needs, which is S4.

---

## Unstructured evidence

| Property | Finding | Verdict |
|---|---|---|
| **Source heterogeneity** | 3 types: 895 support tickets, 329 CRM notes, 112 market events | ✅ |
| **Signal-to-noise** | Only 48 of 895 tickets are planted; **94.6% is background** | ✅ strong |
| **Paraphrase** | 11 distinct phrasings across E1's 34 planted tickets, incl. register variation and error codes | ✅ after fix |
| **Rare exact tokens** | `PG-504`, `ERR_TXN_TIMEOUT` present — what BM25 catches and dense misses | ✅ after fix |
| **Distractors** | 12 decoy tickets + 1 decoy market event, deliberately mis-timed or mis-sliced | ✅ |
| **Contradictory evidence** | S2 carries genuine contradicting market events; S3 has 1 supporting vs 1 contradicting | ✅ |
| **Duplicate concentration** | Near-identical tickets cluster in the event window; the UI collapses them with `(+N near-identical)` | ✅ realistic — real ticket streams do duplicate |
| **Temporal variation** | Tickets spread across the window at varying hours, not stacked on one timestamp | ✅ |

---

## Is the correct cause too obvious?

**No — and this is the strongest part of the data design.**

The brief's example of a weak scenario is a ticket saying *"Payment gateway
failure caused revenue decline"*. Nothing in this corpus does that. The E1
planted tickets are customer-voice symptom reports:

> *"Card was declined repeatedly at the payment step. Tried twice, same error."*
> *"Payment page hung and then timed out. No confirmation received."*
> *"Pressed pay and the spinner never stopped. Had to close the tab."*
> *"Saw error code PG-504 after entering card details. Retried on mobile, same result."*

None names a cause. None mentions revenue. To reach *"a product or platform
failure in Web/Mobile App and West"* the system must:

1. detect the movement and clear materiality,
2. decompose it and find **conversion rate** is the driver (LMDI),
3. localise it to **West × Web/Mobile App** (Adtributor),
4. retrieve a **cohort** of symptom tickets concentrated in that window and slice,
5. correlate a **deploy changelog** entry timed to the changepoint,
6. and pass a **difference-in-differences** test before it may say "caused".

That is the pipeline doing the work, which is what the brief asks for.

### Ground-truth labels do not leak

`support_tickets`, `crm_notes` and `market_events` each carry `planted_for`
and `is_decoy` columns. These are **evaluation labels only**:

- `retrieval/corpus.py` selects `subject`, `body` and `headline` — never the label columns.
- Verified by grep: no module under `retrieval/` or `evidence/` references either column.
- The retrieval benchmark's own description states it: *"planted_for is a label only and is never read by any module under retrieval/."*

A leak here would have made retrieval trivially perfect, which is exactly the
failure mode this audit exists to catch.

---

## Remaining limitations — documented, not fixed

### 1. Diversity is improved but still far below reality

3.4% distinct texts is much better than 1.5%, and it is not what a real
support queue looks like. A production corpus would have near-unique text per
ticket, typos, multi-turn threads, and mixed languages.

**Consequence:** retrieval numbers here remain optimistic relative to
production. **Not fixed further** because generating genuinely unique prose for
895 documents needs a generative model, which would introduce a dependency and
a non-reproducibility that the seeded generator exists to avoid.

### 2. The injected events are detectable by construction

They were designed with magnitudes and durations that clear the materiality
rule. Recall of 1.000 over injected events is therefore **not** recall over
reality.

**What the figure does support:** the harder half — **0 false positives across
the 48 slices with no injected event**. That is not guaranteed by construction.

**Not fixed:** weakening the events would destabilise the validated detection
benchmark for cosmetic realism, which the brief explicitly warns against.

### 3. `customer_email` exists and is synthetic

`fact_orders` carries a `customer_email` column: 91,329 distinct values of the
form `cust_xx#####@example.com`. `example.com` is RFC 2606 reserved and
non-routable, so no value can correspond to a real person.

**This corrects an overstatement in `eval/security_audit.md`**, which said the
dataset contains "no names, emails, addresses". The column exists; the values
are synthetic and unroutable. Corrected there.

### 4. `is_test_account` has no variance

All 105,216 rows are `False`. The column models a real data-quality concern
(test orders polluting a metric) but never exercises it. Harmless, and honest
to note: it is scaffolding for a case the data never presents.

### 5. Market event headlines remain low-diversity

5 distinct headlines across 112 rows. The pool was widened to 7 but selection
is a deterministic `idx % len` cycle over a smaller planted set. Lower impact
than the ticket corpus — market events are the smallest source and mostly act
as contradicting evidence — but it is the least-improved of the three.

---

## Verdict

| Question | Answer |
|---|---|
| Is the data obviously scripted? | **It was.** 13 templates across 895 documents. Now 30, with register variation, error codes and paraphrase. |
| Is the correct answer trivially available? | **No.** No document names a cause; the explanation requires detection + decomposition + localisation + retrieval + counterfactual. |
| Do ground-truth labels leak? | **No.** Verified — the corpus reads text columns only. |
| Are the benchmarks still valid? | **Yes.** Ground truth byte-identical; detection unchanged at 1.000/1.000; all 8 scenario decisions unchanged. |
| Did realism cost accuracy? | **Yes, and deliberately.** Retrieval fell from 0.810 to 0.552 p@5. The weaker number is the more truthful one, and it is what finally justified the hybrid retriever. |
