"""Reproducible demonstration of Stage 4 on the West revenue event.

    python -m eval.demo_west              full attribution
    python -m eval.demo_west --identity   the LMDI identity only
    python -m eval.demo_west --naive      Adtributor beside its own strawman

The last one is the 30-second demo beat: run the ranking with surprise
disabled and watch it blame whatever is biggest; re-enable it and watch it
find the slice whose share actually moved.
"""

from __future__ import annotations

import sys
from datetime import date

from attribution import engine as att
from attribution import lmdi
from attribution.adtributor import adtributor, rank_by_contribution_only
from data import spec
from detection import engine as det
from security.entitlements import Principal
from semantic.types import Window

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
SLICE = {"region": ["West"], "channel": ["Web", "Mobile App"]}
DIMS = ["region", "segment", "product_category", "channel"]
GATEWAY_DEPLOY = date(2026, 7, 12)

RULE = "=" * 78


def _detect():
    return det.detect(
        "net_revenue", WINDOW, ANALYST, slice_filter=SLICE, scenario_id="S1"
    )


def show_identity() -> None:
    d = _detect()
    baseline = Window(start=d.baseline_start, end=d.baseline_end)
    observed = Window(start=d.observed_start, end=d.observed_end)
    dec = att.identity_decomposition(ANALYST, SLICE, baseline, observed)
    report = lmdi.assert_conserved(dec)

    print(RULE)
    print("LMDI IDENTITY DECOMPOSITION — net revenue, West / Web + Mobile App")
    print(RULE)
    print(f"identity : {dec.identity}")
    print(f"method   : {dec.method}")
    print(f"baseline : {baseline.start}..{baseline.end}")
    print(f"observed : {observed.start}..{observed.end}")
    print()
    print(f"{'driver':<24}{'baseline':>14}{'observed':>14}{'change':>10}"
          f"{'contribution':>16}{'share':>9}")
    for dr in sorted(dec.drivers, key=lambda x: -abs(x.contribution)):
        print(f"{dr.driver:<24}{dr.baseline:>14,.4f}{dr.observed:>14,.4f}"
              f"{dr.factor_change_pct:>9.2f}%{dr.contribution:>+16,.1f}"
              f"{dr.contribution_pct:>8.1f}%")
    print("-" * 78)
    print(f"{'TOTAL':<24}{dec.baseline:>14,.2f}{dec.observed:>14,.2f}"
          f"{'':>10}{report['sum_of_contributions']:>+16,.1f}")
    print()
    print(f"movement              {report['total_movement']:>+16,.4f}")
    print(f"sum of contributions  {report['sum_of_contributions']:>+16,.4f}")
    print(f"absolute residual     {report['absolute_residual']:>16.6e}")
    print(f"relative residual     {report['relative_residual_pct']:>16.6e} %")
    print(f"tolerance             {report['tolerance']:>16.6e}")
    print(f"CONSERVED             {str(report['conserved']):>16}")
    print(f"closure vs warehouse  {dec.closure_gap_pct:>16.9f} %")

    if dec.reconciliation:
        print()
        print("cross-source reconciliation (reported, never absorbed):")
        for r in dec.reconciliation:
            print(f"  - {r.quantity} [{r.classification}]: "
                  f"S1 {r.value_a:,.4f} vs {r.source_b} {r.value_b:,.4f} "
                  f"({r.difference_pct:+.2f}%)")
    print(RULE)


def show_naive_comparison() -> None:
    d = _detect()
    forecast, actual, _ = att.build_forecast_cube(
        "net_revenue", WINDOW, ANALYST, DIMS, d.observed_start, d.observed_end
    )

    print(RULE)
    print("CONTRIBUTION-ONLY  vs  CONTRIBUTION + SURPRISE")
    print(RULE)

    naive = rank_by_contribution_only(forecast, actual, DIMS)
    print("\nRanked by size of change alone (Adtributor's own strawman,")
    print("measured at 20% accuracy in the paper against 95%):")
    for dim, el, delta in naive[:6]:
        print(f"    {dim:<18}{el:<16}|change| {delta:>14,.0f}")

    ad = adtributor(forecast, actual, DIMS)
    print("\nRanked by surprise (Adtributor):")
    for dimension in ad.dimensions:
        print(f"    {dimension.dimension:<18}EP={dimension.explanatory_power:>+6.3f}"
              f"  surprise={dimension.surprise:.6f}"
              f"  -> {dimension.element_names}")
    print(f"\n    WINNER: {ad.winner.dimension} = {ad.winner.element_names}")
    print(RULE)


def show_full() -> None:
    d = _detect()
    a = att.attribute(d, ANALYST, cause_date=GATEWAY_DEPLOY, n_resamples=300)

    print(RULE)
    print("STAGE 4 ATTRIBUTION — net revenue, West / Web + Mobile App (E1 / S1)")
    print(RULE)
    print(f"detection : {d.outcome.value}, changepoint {d.changepoint_date}")
    print(f"movement  : {d.materiality.rel_effect_pct:+.2f}% "
          f"({d.materiality.abs_effect:+,.0f} INR) over "
          f"{d.observed_start}..{d.observed_end}")
    print()
    print(a.explain())
    print()
    print("Wording the engine permits:")
    print(f"  descriptive : {a.descriptive_statement()}")
    causal = a.causal_statement("The payment gateway degradation")
    print(f"  causal      : {causal if causal else '(withheld - gate did not pass)'}")
    print(RULE)


def main() -> None:
    args = set(sys.argv[1:])
    if "--identity" in args:
        show_identity()
    elif "--naive" in args:
        show_naive_comparison()
    else:
        show_full()


if __name__ == "__main__":
    main()
