# Overengineering audit

Every major component judged against four tests:

1. Does it satisfy a Round 2 requirement?
2. Does it materially improve **correctness**?
3. Does it materially improve **trust/safety**?
4. Does it materially improve the **judge/user experience**?

If none apply, it is a candidate for removal or V2. Safety-critical
infrastructure is **not** removed for being invisible — that is the whole point
of it.

---

## Verdicts

| Component | R2 req | Correctness | Trust | UX | **Verdict** |
|---|:---:|:---:|:---:|:---:|---|
| Semantic contracts | ✅ MPE-2 | ✅ | ✅ | — | **KEEP** |
| Entitlement + chokepoint | ✅ MPE-7, CX-8 | — | ✅✅ | ✅ | **KEEP** |
| Detection (STL/MAD/PELT) | ✅ OBJ-1, MPE-4 | ✅✅ | ✅ | — | **KEEP** |
| LMDI identity | ✅ OBJ-3, CX-1 | ✅✅ | ✅ | ✅ | **KEEP** |
| Adtributor | ✅ OBJ-3 | ✅ | — | ✅ | **KEEP — simplify surfacing** |
| Difference-in-differences | ✅ OBJ-5 | ✅ | ✅✅ | — | **KEEP — hide from default UI** |
| Retrieval (BM25+dense+RRF) | ✅ OBJ-4, MPE-8 | ✅ | ✅ | ✅ | **KEEP** |
| EvidenceBundle freeze | ✅ MPE-8 | ✅ | ✅✅ | — | **KEEP** |
| Verification (Gate 2) | ✅ OBJ-4 | ✅ | ✅✅ | — | **KEEP** |
| LLM narration | ✅ OBJ-4, MPE-9 | — | — | ✅ | **KEEP — already optional** |
| Recommendation levers | ✅ OBJ-6 | ✅ | ✅ | ✅✅ | **KEEP** |
| Confidence + calibration | ✅ OBJ-5, CX-6 | ✅ | ✅✅ | ✅ | **KEEP** |
| Cost-sensitive deferral | ✅ OBJ-6 | ✅ | ✅✅ | ✅ | **KEEP — surface simplified** |
| LangGraph | ✅ OBJ-8 | — | ✅ | ✅ | **KEEP** |
| Streamlit workspace | ✅ DEL-2 | — | ✅ | ✅✅ | **KEEP** |
| Telemetry | ✅ MPE-10, CX-10 | — | ✅ | ✅ | **KEEP — Audit only** |
| Feedback loop | ✅ OBJ-7 | — | ✅ | — | **KEEP — V2 for the learning half** |
| Bootstrap robustness | — | ✅ | ✅ | — | **KEEP — but see cost note** |
| Cohort aggregation | ✅ MPE-8 | — | ✅ | ✅ | **KEEP** |
| Adtributor strawman ranking | — | — | — | — | **REMOVE IF SAFE** (eval-only) |

**No component is REMOVE.** One eval-only helper is a candidate. That is not a
claim of restraint — it is the outcome of the four tests, and the two
components that came closest to failing are named below.

---

## The components that came closest to failing the test

### Adtributor — KEEP, but its output does not belong on the default screen

**Why it stays:** it answers "*which slice*", which LMDI cannot — LMDI
decomposes the identity (sessions × conversion × AOV × realisation), not the
dimensional cut. Without it, S1 could say conversion rate fell but not that it
fell in West × Web/Mobile App. MPE-4 asks for the affected slice.

**Where it was overengineered:** the full Adtributor output is explanatory
power, surprise (Jensen-Shannon), and succinctness per dimension-element pair
— a dozen numbers with no external referent for a business reader. The UI
shows exactly one line: *"Most affected slice: channel = Web/Mobile App,
region = West"*. Everything else is Method-tab only.

**Honest note:** the surprise floor (`T_SURPRISE = 1e-9`, ADR-019) exists
because the paper's formulation admitted degenerate qualifications. That is
real complexity serving correctness, but it is complexity a judge will not ask
about and should not be pitched.

### Difference-in-differences — KEEP, HIDE FROM DEFAULT UI

**Why it stays, emphatically:** it is the only thing standing between "these
moved together" and "this caused that". It is the mechanism behind
`causal_language_licensed`, and Gate 2 rejects causal wording without it. On
S3 the licence is **denied** — the control moved with the treated slice — and
the UI degrades to "Association only". Remove DiD and the system's central
safety claim becomes an instruction to a model rather than a gate.

**Where it was overengineered:** parallel-trend testing, drift measurement in
%/day, a specificity floor, and temporal precedence checks produce a paragraph
of statistics. None of it belongs on the decision screen. The default UI shows
one chip; the reasoning lives in Method.

### Bootstrap robustness — KEEP, with a stated cost

300–400 resamples of a moving-block bootstrap is **the single largest runtime
cost in the system** — 3.7–14.2 s of every run, dominating everything else
combined.

**Why it stays:** it is the difference between "conversion ranked first" and
"conversion ranked first in 100% of 300 resamples". It feeds the `robustness`
component of confidence, which replaced the p-value after ADR-017 showed the
p-value was post-selection and read p<0.001 on noise. Removing it would leave
confidence resting on a statistic known to be invalid here.

**Honest note:** the demo harness uses `n_resamples=30`, the default is 400.
The reported timings therefore *understate* the default configuration. This is
the one place where a real production system would want a cheaper
approximation.

---

## The one removal candidate

**`attribution/adtributor.py::rank_by_contribution_only`** — a strawman ranker
used once, in the attribution evaluation, to show that contribution-only
ranking picks a different driver than Adtributor does.

- Not on the runtime path.
- Not imported by `graph/`, `ui/`, or any engine.
- Its value is entirely evidential: it is the comparison that justifies using Adtributor at all.

**Verdict: REMOVE IF SAFE — but not removed.** It costs nothing at runtime and
it is the answer to a judge asking "why not just rank by contribution?". A
strawman you can run is worth more than a paragraph asserting the same thing.

---

## What is hidden from the default UI, and why

The default Workspace shows five things: movement, why, evidence posture,
reliability, action. Everything below is one click away or one tab away.

| Hidden | Where it lives | Why hiding it is right |
|---|---|---|
| Adtributor explanatory power / surprise | Method | Numbers with no external referent |
| DiD parallel-trend statistics | Method | A paragraph of statistics under a one-word verdict |
| Confidence component weights | Method | Six weighted components; the band is the answer |
| Expected-loss arithmetic | Method (exact) / Workspace (prose) | Stage 11 P2-01: `E[loss\|model] < E[loss\|human]` asks a business reader to parse conditional-expectation notation |
| Gate 2 check names | Method | 10 checks; "0 hard violations" is the answer |
| Node timings, lineage, graph path | Audit | 15 lineage records is an audit trail, not a screen |
| Raw detector strings | Audit | Stage 11 P2-03 |

This is progressive disclosure doing real work: the technical sophistication a
judge wants to see is **two clicks away and complete**, while the business
screen answers the five questions in one scroll.

---

## Where complexity was already removed

Recorded because restraint that is invisible looks like it never happened:

| Removed | ADR | Reason |
|---|---|---|
| LangChain agent layer | ADR-001 | A model that can re-query data is the thing this architecture exists to prevent |
| Vector database | CLAUDE.md rule 5 | 1,341 documents. Brute-force cosine over a numpy array is correct at this size |
| Multi-agent architecture | CLAUDE.md rule 4 | No agent may re-query data or negotiate an answer |
| Gate 1b `clarify` branch | ADR-029 | A second implementation of a judgement `deferral/` already made better |
| Weighted-sum hypothesis score | ADR-022 | Could not discriminate — 5 of 6 components had spread 0.000 |
| `(1 - p_value)` in confidence | ADR-017 | Post-selection; read p<0.001 on noise |
| Separate identity/attribute/counterfactual nodes | Stage 10 | Would have meant calling private helpers to re-assemble a result the module already assembles |
| FastAPI / microservices | Stage 12 | A network boundary with nothing on the other side |
| Docker / K8s / Terraform | Stage 12 | Infrastructure with nothing behind it |

---

## Summary

| Verdict | Count |
|---|---:|
| KEEP | 19 |
| KEEP with surfacing simplified / hidden from default UI | 5 of those |
| REMOVE IF SAFE | 1 (eval-only strawman, retained deliberately) |
| V2 ONLY | 1 (the *learning* half of the feedback loop) |

The system is not free of complexity — LMDI, Adtributor, DiD, RRF and a
bootstrap are all genuinely complex. Each earns its place against a specific
requirement, and each is **hidden by default**. The judge-facing surface is
five questions; the defensibility is two clicks deeper.
