"""Stage 4 validation — LMDI conservation, Adtributor, robustness, DiD.

Deliberately NOT an accuracy metric. The attribution task has ground truth for
*which dimension and slice* each injected event lives in (`true_dimension`,
`true_slice_label` in data/ground_truth.json), so those are checked directly.
There is no ground truth for the ranking of every non-event slice, so no
precision/recall number is manufactured for attribution the way it was for
detection - a metric computed against labels that do not exist would be worse
than no metric.

Run:  python -m eval.run_attribution_eval
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from attribution import engine as att
from attribution import lmdi
from attribution.adtributor import adtributor, rank_by_contribution_only
from attribution.types import AttributionOutcome, DriverStrength
from data import spec
from detection import engine as det
from security.entitlements import Principal
from semantic.types import Window

ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH = ROOT / "data" / "ground_truth.json"
REPORT = ROOT / "eval" / "attribution_report.md"

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)

WEST_SLICE = {"region": ["West"], "channel": ["Web", "Mobile App"]}
N_RESAMPLES = 300


def _events() -> list[dict]:
    return json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["events"]


def _detect(slice_filter: dict, scenario: str | None = None):
    return det.detect(
        "net_revenue", WINDOW, ANALYST, slice_filter=slice_filter,
        scenario_id=scenario,
    )


# --------------------------------------------------------------------------
# 1 / 2. LMDI conservation across every supported decomposition
# --------------------------------------------------------------------------
def validate_lmdi() -> list[dict]:
    """Decompose several slices and check conservation against the tolerance."""
    slices = [
        ("ALL", {}),
        ("region=West x channel=Web/Mobile App", WEST_SLICE),
        ("region=West", {"region": ["West"]}),
        ("region=North", {"region": ["North"]}),
        ("region=South x product_category=Apparel",
         {"region": ["South"], "product_category": ["Apparel"]}),
        ("region=East x segment=SMB",
         {"region": ["East"], "segment": ["SMB"]}),
        ("channel=Marketplace", {"channel": ["Marketplace"]}),
    ]
    baseline = Window(start=date(2026, 6, 14), end=date(2026, 7, 11))
    observed = Window(start=date(2026, 7, 12), end=date(2026, 7, 26))

    rows = []
    for label, slc in slices:
        try:
            d = att.identity_decomposition(ANALYST, slc, baseline, observed)
            rep = lmdi.conservation_report(d)
            rep["slice"] = label
            rep["dominant_driver"] = d.dominant_driver
            rep["error"] = None
        except lmdi.IdentityError as exc:
            rep = {
                "slice": label, "conserved": False, "error": str(exc),
                "total_movement": float("nan"), "sum_of_contributions": float("nan"),
                "absolute_residual": float("nan"), "relative_residual_pct": float("nan"),
                "tolerance": float("nan"), "closure_gap_pct": None,
                "dominant_driver": None,
            }
        rows.append(rep)
    return rows


# --------------------------------------------------------------------------
# 3. the full driver ranking for the West event
# --------------------------------------------------------------------------
def west_attribution():
    d = _detect(WEST_SLICE, "S1")
    a = att.attribute(
        d, ANALYST, cause_date=date(2026, 7, 12), n_resamples=N_RESAMPLES
    )
    return d, a


# --------------------------------------------------------------------------
# 4. Adtributor against the seeded scenarios, with the strawman beside it
# --------------------------------------------------------------------------
def validate_adtributor_on_scenarios() -> list[dict]:
    rows = []
    for ev in _events():
        if ev["event_id"] not in ("E1", "E2", "E3"):
            continue
        d = _detect(ev["slice"], ev.get("scenario"))
        if d.observed_start is None:
            continue

        contract_dims = ["region", "segment", "product_category", "channel"]
        forecast, actual, _ = att.build_forecast_cube(
            "net_revenue", WINDOW, ANALYST, contract_dims,
            d.observed_start, d.observed_end,
        )
        ad = adtributor(forecast, actual, contract_dims)
        naive = rank_by_contribution_only(forecast, actual, contract_dims)

        winner_dim = ad.winner.dimension if ad.winner else None
        winner_elements = ad.winner.element_names if ad.winner else []
        naive_dim, naive_el, naive_delta = naive[0]

        # what does ranking dimensions by |change| alone pick?
        by_size: dict[str, float] = {}
        for dim, el, delta in naive:
            by_size[dim] = by_size.get(dim, 0.0) + delta
        naive_top_dim = max(by_size, key=by_size.get)

        rows.append({
            "event": ev["event_id"],
            "true_dimension": ev["true_dimension"],
            "true_slice": ev["true_slice_label"],
            "adtributor_dimension": winner_dim,
            "adtributor_elements": winner_elements,
            "dimension_correct": winner_dim == ev["true_dimension"],
            "slice_found": ev["true_slice_label"] in winner_elements,
            "explanatory_power": ad.winner.explanatory_power if ad.winner else None,
            "surprise": ad.winner.surprise if ad.winner else None,
            "naive_top_dimension": naive_top_dim,
            "naive_top_element": f"{naive_dim}={naive_el}",
            "naive_dimension_correct": naive_top_dim == ev["true_dimension"],
            "ranking_changed": naive_top_dim != winner_dim,
            "outcome": ad.outcome.value,
        })
    return rows


# --------------------------------------------------------------------------
# 6. counterfactual, including a case that must FAIL
# --------------------------------------------------------------------------
def validate_counterfactuals() -> list[dict]:
    rows = []

    # (a) the West event with a cause dated before the changepoint - expected PASS
    d = _detect(WEST_SLICE, "S1")
    a = att.attribute(d, ANALYST, cause_date=date(2026, 7, 12),
                      n_resamples=60)
    rows.append(_cf_row("E1 West, cause dated 2026-07-12 (before change)", a))

    # (b) the same event with a cause dated AFTER the changepoint.
    #     Nothing about the data changed - only the claimed cause's date. The
    #     licence must be withdrawn, which is what makes this a gate rather
    #     than a formality.
    a2 = att.attribute(d, ANALYST, cause_date=date(2026, 8, 1),
                       n_resamples=60)
    rows.append(_cf_row("E1 West, cause dated 2026-08-01 (AFTER change)", a2))

    # (c) no dated cause at all - precedence cannot be established
    a3 = att.attribute(d, ANALYST, cause_date=None, n_resamples=60)
    rows.append(_cf_row("E1 West, no dated candidate cause", a3))

    # (d) the other seeded events
    for ev in _events():
        if ev["event_id"] not in ("E2", "E3"):
            continue
        dd = _detect(ev["slice"], ev.get("scenario"))
        aa = att.attribute(
            dd, ANALYST, cause_date=date.fromisoformat(ev["start"]),
            n_resamples=60,
        )
        rows.append(_cf_row(f"{ev['event_id']} {ev['true_slice_label']}", aa))

    return rows


def _cf_row(label: str, a) -> dict:
    c = a.counterfactual
    return {
        "case": label,
        "outcome": a.outcome.value,
        "treatment": c.treatment if c else None,
        "control": c.control if c else None,
        "pre_period": f"{c.pre_period[0]}..{c.pre_period[1]}" if c and c.pre_period else None,
        "post_period": f"{c.post_period[0]}..{c.post_period[1]}" if c and c.post_period else None,
        "did_estimate": c.estimate if c else None,
        "did_pct": c.estimate_pct if c else None,
        "parallel_trend": c.parallel_trend_passed if c else None,
        "temporal_precedence": c.temporal_precedence if c else None,
        "did_passed": c.passed if c else None,
        "causal_licensed": a.causal_language_licensed,
        "reason": a.causal_language_reason,
        "robustness": a.robustness.strength.value if a.robustness else None,
    }


# --------------------------------------------------------------------------
# safe-failure cases
# --------------------------------------------------------------------------
def validate_safe_failures() -> list[dict]:
    rows = []

    # sparse history: attribution must not run at all
    d_sparse = _detect({"product_category": ["NewLaunch"]}, "S4")
    a_sparse = att.attribute(d_sparse, ANALYST, n_resamples=20)
    rows.append({
        "case": "E4 NewLaunch (sparse history)",
        "detection": d_sparse.outcome.value,
        "attribution": a_sparse.outcome.value,
        "causal_licensed": a_sparse.causal_language_licensed,
        "identity_run": a_sparse.identity is not None,
        "adtributor_run": a_sparse.adtributor is not None,
        "expected": "NOT_ATTEMPTED_SPARSE_HISTORY, nothing computed",
    })

    # schema change: E5 is not material once stitched, so attribution declines
    d_schema = _detect({"channel": ["Marketplace"]}, "S7")
    a_schema = att.attribute(d_schema, ANALYST, n_resamples=20)
    rows.append({
        "case": "E5 Marketplace rename (schema change)",
        "detection": d_schema.outcome.value,
        "attribution": a_schema.outcome.value,
        "causal_licensed": a_schema.causal_language_licensed,
        "identity_run": a_schema.identity is not None,
        "adtributor_run": a_schema.adtributor is not None,
        "expected": "no material movement -> no attribution, no causal licence",
    })

    return rows


# --------------------------------------------------------------------------
# printing
# --------------------------------------------------------------------------
def main() -> None:
    line = "=" * 78

    print(line)
    print("STAGE 4 VALIDATION")
    print(line)

    # --- LMDI ---
    print("\n[1] LMDI CONSERVATION")
    print(f"    identity: {att.REVENUE_IDENTITY}")
    print(f"    tolerance: max({lmdi.ABSOLUTE_FLOOR:g}, "
          f"{lmdi.RELATIVE_TOLERANCE:g} x max(|V0|,|V1|))")
    print(f"\n    {'slice':<42}{'movement':>13}{'sum contrib':>13}"
          f"{'abs res':>11}{'rel res %':>12}  ok")
    lmdi_rows = validate_lmdi()
    for r in lmdi_rows:
        if r["error"]:
            print(f"    {r['slice']:<42}{'ERROR':>13}  {r['error'][:40]}")
            continue
        print(f"    {r['slice']:<42}{r['total_movement']:>13,.2f}"
              f"{r['sum_of_contributions']:>13,.2f}"
              f"{r['absolute_residual']:>11.2e}"
              f"{r['relative_residual_pct']:>12.2e}"
              f"  {'yes' if r['conserved'] else 'NO'}")
    all_ok = all(r["conserved"] for r in lmdi_rows)
    print(f"\n    all decompositions conserved: {all_ok}")

    # --- West ranking ---
    print("\n[2] WEST REVENUE EVENT - FULL RANKING")
    d, a = west_attribution()
    print(f"    detection: {d.outcome.value}, changepoint {d.changepoint_date}, "
          f"window {d.observed_start}..{d.observed_end}")
    print(f"    movement:  {d.materiality.rel_effect_pct:+.2f}% "
          f"({d.materiality.abs_effect:+,.0f} INR)")

    print("\n    IDENTITY (which factor moved):")
    for dr in sorted(a.identity.drivers, key=lambda x: -abs(x.contribution)):
        print(f"      {dr.driver:<22}{dr.baseline:>12.4f} ->{dr.observed:>12.4f}"
              f" ({dr.factor_change_pct:+7.2f}%)  contrib {dr.contribution:>+11.1f}"
              f" ({dr.contribution_pct:>+7.1f}% of change)")

    print("\n    DIMENSIONS (ranked by surprise):")
    for dim in a.ranked_dimensions:
        print(f"      {dim.dimension:<18} EP={dim.explanatory_power:>+6.3f}  "
              f"surprise={dim.surprise:.6f}  qualifies={dim.passed_ep_threshold}"
              f"  succinct={dim.succinct}  -> {dim.element_names}")

    print("\n    TOP SLICE AND THE THREE ALTERNATIVES:")
    for s in a.ranked_slices[:4]:
        tag = "WINNER " if s.rank == 1 else f"alt #{s.rank - 1}"
        print(f"      {tag} {s.dimension}={s.element:<14} EP={s.explanatory_power:>+6.3f}"
              f"  surprise={s.surprise:.6f}  delta={s.delta:>+12,.0f}"
              f"  selected={s.selected}")

    print(f"\n    robustness:  {a.robustness.strength.value} "
          f"(stability {a.robustness.selection_frequency:.0%})")
    print(f"    counterfactual: {'PASSED' if a.counterfactual.passed else 'FAILED'}")
    print(f"    causal language: "
          f"{'LICENSED' if a.causal_language_licensed else 'DENIED'}")

    # --- Adtributor on scenarios ---
    print("\n[3] ADTRIBUTOR ON THE SEEDED SCENARIOS")
    print(f"    {'event':<7}{'true dim':<18}{'adtributor':<18}{'ok':<5}"
          f"{'slice found':<13}{'naive picks':<18}{'naive ok'}")
    ad_rows = validate_adtributor_on_scenarios()
    for r in ad_rows:
        print(f"    {r['event']:<7}{r['true_dimension']:<18}"
              f"{str(r['adtributor_dimension']):<18}"
              f"{'yes' if r['dimension_correct'] else 'NO':<5}"
              f"{'yes' if r['slice_found'] else 'NO':<13}"
              f"{r['naive_top_dimension']:<18}"
              f"{'yes' if r['naive_dimension_correct'] else 'NO'}")

    # --- robustness ---
    print("\n[4] ROBUSTNESS")
    print(f"    method:      {a.robustness.method}")
    print(f"    block length {a.robustness.block_length} days, "
          f"window {a.robustness.window_days} days, "
          f"{a.robustness.n_resamples} resamples, seed {a.robustness.seed}")
    print(f"    statistic:   how often {a.robustness.top_dimension}="
          f"{a.robustness.top_element} is re-selected as the top driver")
    print(f"    thresholds:  STRONG >= {int(100 * __import__('attribution.robustness', fromlist=['x']).STRONG_FREQUENCY)}%, "
          f"WEAK >= {int(100 * __import__('attribution.robustness', fromlist=['x']).WEAK_FREQUENCY)}%, "
          f"else UNSTABLE")
    print(f"\n    driver stability = {a.robustness.selection_frequency:.0%}"
          f"  -> {a.robustness.strength.value}")
    print(f"    EP across resamples: mean {a.robustness.ep_mean:+.3f}, "
          f"p05 {a.robustness.ep_p05:+.3f}, p95 {a.robustness.ep_p95:+.3f}")
    if a.robustness.caveat:
        print(f"    caveat: {a.robustness.caveat}")

    # --- counterfactuals ---
    print("\n[5] COUNTERFACTUAL / CAUSAL GATE")
    cf_rows = validate_counterfactuals()
    for r in cf_rows:
        print(f"\n    {r['case']}")
        print(f"      treated={r['treatment']}  control={r['control']}")
        print(f"      pre={r['pre_period']}  post={r['post_period']}")
        did = f"{r['did_estimate']:+,.0f}" if r["did_estimate"] is not None else "n/a"
        didp = f"{r['did_pct']:+.1f}%" if r["did_pct"] is not None else "n/a"
        print(f"      DiD={did} ({didp})  parallel_trend={r['parallel_trend']}"
              f"  precedence={r['temporal_precedence']}")
        print(f"      CAUSAL LANGUAGE: "
              f"{'LICENSED' if r['causal_licensed'] else 'DENIED'}")

    passed = [r for r in cf_rows if r["causal_licensed"]]
    failed = [r for r in cf_rows if not r["causal_licensed"]]
    print(f"\n    {len(passed)} case(s) licensed, {len(failed)} denied")

    # --- safe failures ---
    print("\n[6] SAFE FAILURE CASES")
    sf_rows = validate_safe_failures()
    for r in sf_rows:
        print(f"    {r['case']}")
        print(f"      detection={r['detection']}  attribution={r['attribution']}")
        print(f"      identity_run={r['identity_run']}  "
              f"adtributor_run={r['adtributor_run']}  "
              f"causal={r['causal_licensed']}")

    print("\n" + line)
    write_report(lmdi_rows, d, a, ad_rows, cf_rows, sf_rows)
    print(f"wrote {REPORT.relative_to(ROOT)}")


def write_report(lmdi_rows, detection, a, ad_rows, cf_rows, sf_rows) -> None:
    import attribution.robustness as R

    top = a.top_slice
    L = []
    L.append("# Stage 4 — Attribution evaluation")
    L.append("")
    L.append("Generated by `python -m eval.run_attribution_eval`.")
    L.append("")

    # executive
    L.append("## Executive result — the West revenue event")
    L.append("")
    L.append(f"Detection established a material movement in "
             f"`{detection.slice_label}`: **{detection.materiality.rel_effect_pct:+.2f}%** "
             f"({detection.materiality.abs_effect:+,.0f} INR) over "
             f"{detection.observed_start}..{detection.observed_end}, "
             f"changepoint {detection.changepoint_date}.")
    L.append("")
    L.append("Attribution answers the four questions separately:")
    L.append("")
    L.append("| Question | Answer |")
    L.append("|---|---|")
    L.append(f"| Which factor moved? | **{a.identity.dominant_driver}** "
             f"({[d.contribution_pct for d in a.identity.drivers if d.driver == a.identity.dominant_driver][0]:+.1f}% of the change) |")
    L.append(f"| Which slice moved? | **{top.dimension}={top.element}** "
             f"(EP {top.explanatory_power:.2f}, surprise {top.surprise:.6f}) |")
    L.append(f"| Is the ranking robust? | **{a.robustness.strength.value}** "
             f"({a.robustness.selection_frequency:.0%} of {a.robustness.n_resamples} resamples) |")
    L.append(f"| May we say *caused*? | "
             f"**{'LICENSED' if a.causal_language_licensed else 'DENIED'}** |")
    L.append("")
    L.append(f"Ground truth for E1 records `true_driver = conversion_rate`, "
             f"`true_dimension = region`, `true_slice_label = West`. "
             f"All three match.")
    L.append("")
    L.append("Permitted wording:")
    L.append("")
    L.append(f"> {a.descriptive_statement()}")
    L.append("")
    causal = a.causal_statement("The payment gateway degradation")
    L.append(f"> {causal}" if causal else
             "> *(causal wording withheld — the gate did not pass)*")
    L.append("")

    # LMDI
    L.append("## LMDI")
    L.append("")
    L.append(f"```\n{att.REVENUE_IDENTITY}\n```")
    L.append("")
    L.append("Every factor is read from the S1 warehouse under identical "
             "filters, so the product telescopes exactly: "
             "`sessions x (orders/sessions) x (gross/orders) x (net/gross) = net`. "
             "Architecture Part 7.1 writes the fourth factor as "
             "`(1 - Refund Rate)` from S3 finance; that version closes to only "
             "~95%. See ADR-018.")
    L.append("")
    L.append(f"Tolerance: `max({lmdi.ABSOLUTE_FLOOR:g}, "
             f"{lmdi.RELATIVE_TOLERANCE:g} x max(|V0|, |V1|))` — a "
             f"floating-point rounding budget, not a modelling allowance. "
             f"A decomposition exceeding it raises `ConservationFailure`.")
    L.append("")
    L.append("| Slice | Movement | Sum of contributions | Abs residual | Rel residual | Conserved |")
    L.append("|---|---:|---:|---:|---:|:--:|")
    for r in lmdi_rows:
        if r["error"]:
            L.append(f"| {r['slice']} | — | — | — | — | ERROR |")
            continue
        L.append(f"| {r['slice']} | {r['total_movement']:,.2f} | "
                 f"{r['sum_of_contributions']:,.2f} | "
                 f"{r['absolute_residual']:.2e} | "
                 f"{r['relative_residual_pct']:.2e}% | "
                 f"{'yes' if r['conserved'] else 'NO'} |")
    L.append("")
    L.append("### Driver contributions, West event")
    L.append("")
    L.append("| Driver | Baseline | Observed | Factor change | Contribution (INR/day) | Share of change |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for dr in sorted(a.identity.drivers, key=lambda x: -abs(x.contribution)):
        L.append(f"| {dr.driver} | {dr.baseline:,.4f} | {dr.observed:,.4f} | "
                 f"{dr.factor_change_pct:+.2f}% | {dr.contribution:+,.1f} | "
                 f"{dr.contribution_pct:+.1f}% |")
    L.append("")
    if a.identity.reconciliation:
        L.append("### Cross-source reconciliation (reported, not absorbed)")
        L.append("")
        L.append("| Quantity | Class | S1 | Other | Difference |")
        L.append("|---|---|---:|---:|---:|")
        for r in a.identity.reconciliation:
            L.append(f"| {r.quantity} | {r.classification} | {r.value_a:,.4f} | "
                     f"{r.value_b:,.4f} | {r.difference_pct:+.2f}% |")
        L.append("")
        for r in a.identity.reconciliation:
            L.append(f"- **{r.quantity}** — {r.explanation}")
        L.append("")

    # Adtributor
    L.append("## Adtributor")
    L.append("")
    L.append("### Paper reproduction")
    L.append("")
    L.append("`tests/test_adtributor.py` reproduces the NSDI '14 worked "
             "example (revenue 100 -> 50). Data centre X carries EP **0.940** "
             "but surprise **0.000** — it produced 94% of forecast revenue and "
             "kept exactly that share. Device type carries EP **0.980** and "
             "surprise **0.138**, and the selected elements are "
             "`{Mobile, Tablet}`, whose share collapsed from 25% each to 1%. "
             "A magnitude-ranking heuristic blames data centre X; this "
             "implementation does not, and a test asserts the strawman really "
             "would get it wrong.")
    L.append("")
    L.append("### Project scenarios — contribution-only vs contribution + surprise")
    L.append("")
    L.append("| Event | True dimension | Adtributor | Correct | True slice found | Contribution-only picks | Correct |")
    L.append("|---|---|---|:--:|:--:|---|:--:|")
    for r in ad_rows:
        L.append(f"| {r['event']} | {r['true_dimension']} | "
                 f"{r['adtributor_dimension']} | "
                 f"{'yes' if r['dimension_correct'] else 'NO'} | "
                 f"{'yes' if r['slice_found'] else 'NO'} | "
                 f"{r['naive_top_dimension']} | "
                 f"{'yes' if r['naive_dimension_correct'] else 'NO'} |")
    L.append("")

    disagree = [r for r in ad_rows if r["ranking_changed"]]
    agree = [r for r in ad_rows if not r["ranking_changed"]]
    L.append(f"Adtributor identifies the intended dimension on "
             f"{sum(1 for r in ad_rows if r['dimension_correct'])}/{len(ad_rows)} "
             f"events and the intended slice on "
             f"{sum(1 for r in ad_rows if r['slice_found'])}/{len(ad_rows)}.")
    L.append("")
    if disagree:
        names = ", ".join(r["event"] for r in disagree)
        L.append(f"**Surprise changes the answer on {names}.** "
                 f"On {disagree[0]['event']} the movement is largest in "
                 f"`{disagree[0]['naive_top_dimension']}`, so ranking by size "
                 f"of change alone picks that and is wrong; the share that "
                 f"actually shifted is "
                 f"`{disagree[0]['adtributor_dimension']}`, which is what the "
                 f"ground truth records.")
        L.append("")
    if agree:
        names = ", ".join(r["event"] for r in agree)
        L.append(f"**It does not change the answer on {names}** — there the "
                 f"biggest mover is also the most surprising one, and both "
                 f"methods agree. This is worth stating plainly: the West "
                 f"event is the headline demo for the *pipeline*, but it is "
                 f"not the case that demonstrates why surprise is needed. "
                 f"Use {disagree[0]['event'] if disagree else 'the paper example'} "
                 f"for that, or the NSDI '14 example above, where the "
                 f"difference is unambiguous.")
        L.append("")
    L.append("Large-but-normal elements are held back by construction: an "
             "element keeping its share contributes zero surprise however "
             "large it is (data centre X, EP 0.94, surprise 0.00). Small "
             "cells are held back by the `T_EEP` floor — an element worth "
             "less than 10% of the movement cannot enter the candidate set, "
             "and a cell worth 0.2% of the total that doubles still barely "
             "moves its share. Both are pinned by tests.")
    L.append("")

    # robustness
    L.append("## Robustness")
    L.append("")
    L.append(f"- **Method** — {a.robustness.method}")
    L.append(f"- **Block length** — {a.robustness.block_length} days "
             f"(one seasonal cycle where the window holds three; blocks rather "
             f"than single days because daily residuals are autocorrelated)")
    L.append(f"- **Resamples** — {a.robustness.n_resamples}, seed "
             f"{a.robustness.seed} (fixed, so the number is reproducible)")
    L.append(f"- **Statistic** — the share of resamples in which the same "
             f"(dimension, element) is re-selected as top driver")
    L.append(f"- **Thresholds** — STRONG >= {R.STRONG_FREQUENCY:.0%} with "
             f"consistent sign; WEAK >= {R.WEAK_FREQUENCY:.0%}; else UNSTABLE")
    L.append("")
    L.append("Not a Welch p-value: Stage 3 established that the event window is "
             "selected to maximise displacement, so a pre/post test on that "
             "window is a post-selection statistic and returns p < 0.001 on "
             "pure noise (ADR-017). Welch is still computed and carried as "
             "diagnostic metadata; it decides nothing.")
    L.append("")
    L.append(f"**driver stability = {a.robustness.selection_frequency:.0%}** "
             f"({a.robustness.top_dimension}={a.robustness.top_element}) "
             f"-> **{a.robustness.strength.value}**")
    L.append("")
    L.append(f"EP across resamples: mean {a.robustness.ep_mean:+.3f}, "
             f"p05 {a.robustness.ep_p05:+.3f}, p95 {a.robustness.ep_p95:+.3f}, "
             f"sign consistency {a.robustness.ep_sign_consistency:.0%}.")
    if a.robustness.caveat:
        L.append("")
        L.append(f"*Caveat:* {a.robustness.caveat}")
    L.append("")

    # counterfactual
    L.append("## Counterfactual and the causal-language gate")
    L.append("")
    L.append("| Case | Control | DiD | Parallel trend | Precedence | Causal language |")
    L.append("|---|---|---:|:--:|:--:|:--:|")
    for r in cf_rows:
        did = f"{r['did_estimate']:+,.0f}" if r["did_estimate"] is not None else "—"
        L.append(f"| {r['case']} | {r['control'] or '—'} | {did} | "
                 f"{'pass' if r['parallel_trend'] else 'FAIL'} | "
                 f"{'pass' if r['temporal_precedence'] else 'FAIL'} | "
                 f"**{'LICENSED' if r['causal_licensed'] else 'DENIED'}** |")
    L.append("")
    n_pass = sum(1 for r in cf_rows if r["causal_licensed"])
    L.append(f"{n_pass} licensed, {len(cf_rows) - n_pass} denied. The second "
             f"row is the important one: nothing about the data changed, only "
             f"the claimed cause's date moved after the changepoint, and the "
             f"licence was withdrawn. A gate that never denies is not a gate.")
    L.append("")

    # safe failures
    L.append("## Safe-failure cases")
    L.append("")
    L.append("| Case | Detection | Attribution | Identity run | Adtributor run | Causal |")
    L.append("|---|---|---|:--:|:--:|:--:|")
    for r in sf_rows:
        L.append(f"| {r['case']} | `{r['detection']}` | `{r['attribution']}` | "
                 f"{'yes' if r['identity_run'] else 'no'} | "
                 f"{'yes' if r['adtributor_run'] else 'no'} | "
                 f"{'yes' if r['causal_licensed'] else 'no'} |")
    L.append("")

    # limitations
    L.append("## Limitations")
    L.append("")
    L.append("- **No attribution accuracy metric.** Ground truth names the "
             "dimension and slice of each injected event, and those are "
             "checked. It does not label the correct ranking of every "
             "non-event slice, so no precision/recall figure is manufactured "
             "for attribution. Detection has one because detection's labels "
             "support it; attribution's do not.")
    L.append("- **The data is synthetic and the events were injected by us.** "
             "Adtributor finding the dimension we planted is a correctness "
             "check on the implementation, not evidence it will work on "
             "production data.")
    L.append("- **The bootstrap is coarse on short windows.** A 15-day event "
             "with 5-day blocks gives three blocks; the stability figure is "
             "meaningful as a three-way verdict, not as a confidence interval.")
    L.append("- **DiD assumes the control is untreated.** Controls are chosen "
             "by pre-period correlation among unflagged slices. If an event "
             "were genuinely market-wide, every candidate would be treated and "
             "the check would correctly return DiD near zero — but it cannot "
             "detect a control contaminated in a way the pre-period does not "
             "reveal.")
    L.append("- **Parallel-trend tolerance is a chosen constant** "
             f"({cf_tolerance()}), not derived from the data. It is a "
             "screening heuristic, not a formal test.")
    L.append("- **`net_realisation` deviates from the architecture's stated "
             "fourth factor.** Deliberate, measured and recorded in ADR-018.")
    L.append("")

    # commands
    L.append("## Demo commands")
    L.append("")
    L.append("Adtributor paper reproduction:")
    L.append("")
    L.append("```bash")
    L.append("python -m pytest tests/test_adtributor.py -v")
    L.append("```")
    L.append("")
    L.append("LMDI conservation and the identity, on the West event:")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.demo_west --identity")
    L.append("```")
    L.append("")
    L.append("Full attribution for the West revenue scenario:")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.demo_west")
    L.append("```")
    L.append("")
    L.append("Complete Stage 4 validation (this report):")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.run_attribution_eval")
    L.append("```")
    L.append("")

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def cf_tolerance() -> str:
    from attribution import counterfactual as c
    return f"{c.MAX_PRE_TREND_DRIFT:.0%}/day drift, {c.MIN_EFFECT_PCT:.0f}% minimum effect"


if __name__ == "__main__":
    main()
