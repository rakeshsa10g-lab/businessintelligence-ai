"""Stage 4 tests — LMDI, ratio routing, robustness, DiD, and the causal gate.

The Adtributor algorithm itself is pinned separately by
`tests/test_adtributor.py`, which reproduces the published example. This file
covers the engine around it, and it leans deliberately towards the negative
cases: an attribution engine is only trustworthy if it refuses when it should.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from attribution import counterfactual as cf
from attribution import engine as att
from attribution import lmdi
from attribution import robustness as rob
from attribution.adtributor import adtributor
from attribution.types import (
    AttributionOutcome,
    DriverStrength,
)
from data import spec
from detection import engine as det
from security.entitlements import Principal
from semantic.types import Window

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
WEST = {"region": ["West"], "channel": ["Web", "Mobile App"]}
GATEWAY_DEPLOY = date(2026, 7, 12)


@pytest.fixture(scope="module")
def west_detection():
    return det.detect(
        "net_revenue", WINDOW, ANALYST, slice_filter=WEST, scenario_id="S1"
    )


@pytest.fixture(scope="module")
def west_attribution(west_detection):
    return att.attribute(
        west_detection, ANALYST, cause_date=GATEWAY_DEPLOY, n_resamples=120
    )


# ==========================================================================
# LMDI
# ==========================================================================
def test_lmdi_conserves_exactly_on_a_synthetic_identity():
    """The mathematical guarantee, checked without any data access."""
    f0 = {"a": 100.0, "b": 2.0, "c": 0.5}
    f1 = {"a": 90.0, "b": 2.2, "c": 0.45}
    d = lmdi.decompose(f0, f1, kpi="v", identity="a*b*c")

    assert d.conserved
    summed = sum(x.contribution for x in d.drivers)
    assert summed == pytest.approx(d.total_change, abs=1e-9)
    assert d.conservation_error <= d.conservation_tolerance


def test_lmdi_is_order_independent():
    """The property a naive sequential split does not have."""
    f0 = {"a": 100.0, "b": 2.0, "c": 0.5}
    f1 = {"a": 90.0, "b": 2.2, "c": 0.45}
    forward = lmdi.decompose(f0, f1, kpi="v", identity="a*b*c")
    reversed_ = lmdi.decompose(
        dict(reversed(list(f0.items()))),
        dict(reversed(list(f1.items()))),
        kpi="v", identity="c*b*a",
    )
    a = {x.driver: x.contribution for x in forward.drivers}
    b = {x.driver: x.contribution for x in reversed_.drivers}
    for k in a:
        assert a[k] == pytest.approx(b[k], rel=1e-12)


def test_lmdi_contribution_percentages_sum_to_one_hundred():
    # 100 x 2.0 = 200 -> 80 x 2.2 = 176, a real movement of -24
    f0 = {"a": 100.0, "b": 2.0}
    f1 = {"a": 80.0, "b": 2.2}
    d = lmdi.decompose(f0, f1, kpi="v", identity="a*b")
    assert d.total_change != 0
    assert sum(x.contribution_pct for x in d.drivers) == pytest.approx(100.0, abs=1e-6)


def test_lmdi_percentages_are_zero_when_the_product_did_not_move():
    """Offsetting factors: 100 x 2.0 and 80 x 2.5 are both 200.

    There is no movement to take a share of, so the shares are zero rather
    than an arbitrary split of nothing.
    """
    d = lmdi.decompose(
        {"a": 100.0, "b": 2.0}, {"a": 80.0, "b": 2.5}, kpi="v", identity="a*b"
    )
    assert d.total_change == pytest.approx(0.0, abs=1e-9)
    assert all(x.contribution_pct == 0.0 for x in d.drivers)
    # the factors did move, even though their product did not
    assert any(abs(x.contribution) > 1.0 for x in d.drivers)


def test_lmdi_handles_an_unchanged_identity():
    f = {"a": 10.0, "b": 3.0}
    d = lmdi.decompose(dict(f), dict(f), kpi="v", identity="a*b")
    assert d.total_change == pytest.approx(0.0)
    assert all(x.contribution == pytest.approx(0.0) for x in d.drivers)
    assert d.conserved


def test_lmdi_refuses_a_zero_factor_rather_than_substituting_an_epsilon():
    """A factor reaching zero is a real event, not a numerical inconvenience."""
    with pytest.raises(lmdi.IdentityError, match="strictly positive"):
        lmdi.decompose(
            {"a": 10.0, "b": 1.0}, {"a": 10.0, "b": 0.0},
            kpi="v", identity="a*b",
        )


def test_lmdi_refuses_mismatched_factor_sets():
    with pytest.raises(lmdi.IdentityError, match="factor sets differ"):
        lmdi.decompose({"a": 1.0}, {"b": 1.0}, kpi="v", identity="x")


def test_logarithmic_mean_limit_when_the_two_values_are_equal():
    assert lmdi.logarithmic_mean(7.0, 7.0) == pytest.approx(7.0)
    assert lmdi.logarithmic_mean(1.0, np.e) == pytest.approx(np.e - 1.0)


def test_conservation_failure_is_raised_not_swallowed():
    """A decomposition that does not conserve must fail loudly.

    Hand-built: the contributions are corrupted after the fact, which is the
    only way to produce a non-conserving LMDI result. If this ever passes
    silently, every percentage downstream is meaningless.
    """
    d = lmdi.decompose(
        {"a": 100.0, "b": 2.0}, {"a": 90.0, "b": 2.2}, kpi="v", identity="a*b"
    )
    d.drivers[0].contribution += 5.0            # corrupt it
    with pytest.raises(lmdi.ConservationFailure, match="residual"):
        lmdi.assert_conserved(d)


def test_identity_closes_on_a_single_population(west_detection):
    """ADR-018: every factor from S1, so the product telescopes exactly."""
    baseline = Window(start=west_detection.baseline_start,
                      end=west_detection.baseline_end)
    observed = Window(start=west_detection.observed_start,
                      end=west_detection.observed_end)
    d = att.identity_decomposition(ANALYST, WEST, baseline, observed)
    report = lmdi.assert_conserved(d)

    assert report["conserved"]
    assert report["relative_residual_pct"] < 1e-9
    # the reconstructed identity must equal the warehouse figure, not merely
    # approximate it
    assert d.closure_gap_pct == pytest.approx(0.0, abs=1e-6), (
        f"identity closes to {d.closure_gap_pct:.6f}% of the warehouse figure; "
        "a non-zero gap means factors came from different populations"
    )


def test_mixed_source_identity_fails_conservation(west_detection):
    """Pin the bug ADR-018 fixed, so it cannot return silently.

    Using S2 product-analytics sessions with S1 AOV — the architecture's
    literal identity — leaves the reconstructed value several percent away
    from the booked figure. The point is not that it is slightly off; it is
    that LMDI's conservation guarantee then applies to a quantity that is not
    net revenue.
    """
    from semantic import gateway

    baseline = Window(start=west_detection.baseline_start,
                      end=west_detection.baseline_end)
    days = (baseline.end - baseline.start).days + 1

    s1_sessions, _, _ = att._s1_aggregate("sessions", baseline, ANALYST, WEST)
    _, gross, orders = att._s1_aggregate(
        "average_order_value", baseline, ANALYST, WEST
    )
    net, _, _ = att._s1_aggregate("net_revenue", baseline, ANALYST, WEST)
    _, s2_orders, s2_sessions = att._s1_aggregate(
        "conversion_rate", baseline, ANALYST, WEST
    )

    # the S2 population is genuinely smaller
    assert s2_sessions < s1_sessions
    gap = abs(s2_sessions / s1_sessions - 1.0)
    assert gap > 0.02, f"expected a material S1/S2 population gap, got {gap:.4%}"

    mixed = (s2_sessions / days) * (s2_orders / s2_sessions) * (gross / orders)
    single = (s1_sessions / days) * (orders / s1_sessions) * (gross / orders)

    assert single == pytest.approx(gross / days, rel=1e-12)
    assert mixed != pytest.approx(gross / days, rel=1e-6), (
        "the mixed-source identity should NOT reconstruct gross revenue"
    )


# ==========================================================================
# ratio KPI routing
# ==========================================================================
@pytest.mark.parametrize(
    "ratio_kpi", ["conversion_rate", "average_order_value", "refund_rate"]
)
def test_ratio_kpis_are_routed_to_a_fundamental_measure(ratio_kpi):
    """Explanatory power over a ratio is not well defined (CMMD)."""
    target, chain = att.resolve_attribution_kpi(ratio_kpi)
    from semantic import registry

    assert chain, f"{ratio_kpi} must declare attribute_via"
    assert registry.get(target).additive, (
        f"{ratio_kpi} routed to {target}, which is not additive"
    )
    assert target != ratio_kpi


def test_additive_kpi_is_attributed_directly():
    target, chain = att.resolve_attribution_kpi("net_revenue")
    assert target == "net_revenue"
    assert chain is None


@pytest.mark.parametrize(
    "ratio_kpi", ["conversion_rate", "average_order_value", "refund_rate"]
)
def test_adtributor_refuses_to_run_on_a_ratio_directly(ratio_kpi):
    """The guard, not just the routing: refuse even if called directly."""
    with pytest.raises(att.AttributionError, match="non-additive"):
        att.assert_attributable(ratio_kpi)


def test_attributing_a_ratio_records_the_redirection(west_detection):
    """The result must say it was redirected, not quietly answer a different
    question."""
    d = det.detect(
        "conversion_rate", WINDOW, ANALYST,
        slice_filter={"region": ["West"]}, scenario_id="S1",
    )
    a = att.attribute(d, ANALYST, n_resamples=20, run_robustness=False)
    if a.outcome in (
        AttributionOutcome.NOT_ATTEMPTED_NOT_MATERIAL,
        AttributionOutcome.NOT_ATTEMPTED_SPARSE_HISTORY,
    ):
        pytest.skip("conversion_rate movement was not material in this window")
    assert a.attributed_via, "the attribute_via chain must be recorded"
    assert a.attribution_kpi != "conversion_rate"
    assert any("ratio" in n for n in a.notes)


# ==========================================================================
# Adtributor edge cases on our own data shapes
# ==========================================================================
def test_sparse_cells_do_not_dominate_the_ranking():
    """A tiny cell that doubles is not an explanation of a large movement.

    Its share barely moves, so its surprise stays small, and the T_EEP floor
    keeps it out of the candidate set regardless.
    """
    f = pd.DataFrame([
        ("Big", 1000.0), ("Small", 2.0),
    ], columns=["dim", "value"])
    a = pd.DataFrame([
        ("Big", 500.0), ("Small", 4.0),
    ], columns=["dim", "value"])
    result = adtributor(f, a, ["dim"])
    winner = result.winner
    assert winner is not None
    assert "Small" not in winner.element_names, (
        "a cell worth 0.2% of the total must not be offered as the cause"
    )


def test_a_dimension_that_moved_proportionally_has_no_surprise():
    """Everything shrinking equally is not localisable to any element."""
    f = pd.DataFrame([("A", 50.0), ("B", 30.0), ("C", 20.0)],
                     columns=["dim", "value"])
    a = pd.DataFrame([("A", 25.0), ("B", 15.0), ("C", 10.0)],
                     columns=["dim", "value"])
    result = adtributor(f, a, ["dim"])
    assert result.dimensions[0].surprise == pytest.approx(0.0, abs=1e-9)


def test_multi_dimensional_case_is_reported_not_guessed():
    """The cause lives in the (A,X) and (B,Y) cells, not in d1 or d2.

    Both marginals still read 50/50 afterwards, so neither dimension has
    redistributed at all - yet explanatory power reaches 1.0 by naming every
    element. This is precisely the case Adtributor cannot localise and
    HotSpot/Squeeze exist for, so it must be declined rather than answered.
    """
    f = pd.DataFrame([
        ("A", "X", 25.0), ("A", "Y", 25.0),
        ("B", "X", 25.0), ("B", "Y", 25.0),
    ], columns=["d1", "d2", "value"])
    a = pd.DataFrame([
        ("A", "X", 15.0), ("A", "Y", 25.0),
        ("B", "X", 25.0), ("B", "Y", 15.0),
    ], columns=["d1", "d2", "value"])
    result = adtributor(f, a, ["d1", "d2"])

    # the trap: EP alone says both dimensions fully explain the movement
    for dim in result.dimensions:
        assert dim.passed_ep_threshold
        assert dim.surprise == pytest.approx(0.0, abs=1e-12)

    assert result.outcome is AttributionOutcome.MULTI_DIMENSIONAL_CASE
    assert result.winner is None
    assert "combination" in result.reason


def test_a_one_dimensional_cause_is_still_attributed():
    """Guard the guard: the multi-dimensional rule must not swallow real cases."""
    f = pd.DataFrame([
        ("A", "X", 25.0), ("A", "Y", 25.0),
        ("B", "X", 25.0), ("B", "Y", 25.0),
    ], columns=["d1", "d2", "value"])
    a = pd.DataFrame([
        ("A", "X", 5.0), ("A", "Y", 5.0),
        ("B", "X", 25.0), ("B", "Y", 25.0),
    ], columns=["d1", "d2", "value"])
    result = adtributor(f, a, ["d1", "d2"])
    assert result.outcome is AttributionOutcome.ATTRIBUTED
    assert result.winner.dimension == "d1"
    assert result.winner.element_names == ["A"]


# ==========================================================================
# robustness
# ==========================================================================
def _cube(pattern, days=15, dims=("A", "B", "C")):
    """Build a (forecast, actual) pair from a per-element multiplier."""
    frows, arows = [], []
    start = date(2026, 7, 12)
    for i in range(days):
        d0 = start + timedelta(days=i)
        for name in dims:
            frows.append({"dim": name, "date": d0, "value": 100.0})
            arows.append({"dim": name, "date": d0, "value": 100.0 * pattern(name, i)})
    return pd.DataFrame(frows), pd.DataFrame(arows)


def test_a_consistent_driver_is_reported_strong():
    f, a = _cube(lambda name, i: 0.4 if name == "A" else 1.0)
    r = rob.assess(f, a, ["dim"], n_resamples=200)
    assert r.strength is DriverStrength.STRONG
    assert r.top_element == "A"
    assert r.selection_frequency >= rob.STRONG_FREQUENCY


def test_a_ranking_that_depends_on_which_days_are_sampled_is_not_strong():
    """Two elements, each collapsing in a different half of the window.

    Which one "explains" the movement then depends entirely on which days the
    resample happens to draw - the exact failure mode a selected event window
    can hide, and the reason this check exists.

    Note what this test does NOT claim: an event concentrated in two days is
    still a *stable* attribution, because the same slice wins every time. The
    bootstrap measures stability of the ranking, not the duration of the
    effect; duration is the materiality gate's job (Stage 3).
    """
    def pattern(name, i):
        if name == "A" and i < 7:
            return 0.10
        if name == "B" and i >= 8:
            return 0.10
        return 1.0

    f, a = _cube(pattern)
    r = rob.assess(f, a, ["dim"], n_resamples=200)
    assert r.strength in (DriverStrength.WEAK, DriverStrength.UNSTABLE), (
        f"a ranking that flips with the window was reported "
        f"{r.strength.value} at {r.selection_frequency:.0%} stability"
    )


def test_a_short_but_consistent_driver_is_still_stable():
    """The companion to the test above, so the distinction is explicit."""
    def pattern(name, i):
        return 0.05 if (name == "A" and i in (3, 4)) else 1.0

    f, a = _cube(pattern)
    r = rob.assess(f, a, ["dim"], n_resamples=200)
    assert r.top_element == "A"
    assert r.selection_frequency > rob.WEAK_FREQUENCY


def test_robustness_is_reproducible_from_its_seed():
    f, a = _cube(lambda name, i: 0.5 if name == "A" else 1.0)
    first = rob.assess(f, a, ["dim"], n_resamples=100, seed=123)
    again = rob.assess(f, a, ["dim"], n_resamples=100, seed=123)
    assert first.selection_frequency == again.selection_frequency
    assert first.ep_mean == pytest.approx(again.ep_mean)


def test_robustness_declines_on_a_window_too_short_to_resample():
    f, a = _cube(lambda name, i: 0.5 if name == "A" else 1.0, days=3)
    r = rob.assess(f, a, ["dim"], n_resamples=50)
    assert r.strength is DriverStrength.UNSTABLE
    assert "too short" in r.reason


# ==========================================================================
# counterfactual — the negative cases matter most here
# ==========================================================================
def _series(values, start=date(2026, 6, 1)):
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def test_temporal_precedence_rejects_a_cause_dated_after_the_change():
    ok, reason = cf.check_temporal_precedence(
        date(2026, 7, 20), date(2026, 7, 12)
    )
    assert not ok
    assert "AFTER" in reason


def test_temporal_precedence_accepts_a_cause_dated_before_the_change():
    ok, reason = cf.check_temporal_precedence(
        date(2026, 7, 10), date(2026, 7, 12)
    )
    assert ok
    assert "precedes" in reason


def test_temporal_precedence_without_a_dated_cause_is_not_established():
    ok, _ = cf.check_temporal_precedence(None, date(2026, 7, 12))
    assert not ok


def test_did_denies_causal_language_when_the_control_moved_too():
    """A market-wide movement must not be narrated as slice-specific."""
    rng = np.random.default_rng(11)
    base = 100 + rng.normal(0, 1, 60)
    treated = _series(np.concatenate([base[:40], base[40:] * 0.7]))
    control = _series(np.concatenate([base[:40] * 1.01, base[40:] * 0.7 * 1.01]))

    result = cf.difference_in_differences(
        treated, {"control": control},
        treatment_label="t", treatment_slice={},
        pre_start=date(2026, 6, 12), pre_end=date(2026, 7, 10),
        post_start=date(2026, 7, 11), post_end=date(2026, 7, 30),
        cause_date=date(2026, 7, 1), changepoint=date(2026, 7, 11),
    )
    assert not result.passed
    assert not result.causal_language_licensed
    assert "market-wide" in result.reason


def test_did_licenses_causal_language_when_the_control_held_steady():
    rng = np.random.default_rng(12)
    base = 100 + rng.normal(0, 1, 60)
    treated = _series(np.concatenate([base[:40], base[40:] * 0.7]))
    control = _series(base * 1.01)

    result = cf.difference_in_differences(
        treated, {"control": control},
        treatment_label="t", treatment_slice={},
        pre_start=date(2026, 6, 12), pre_end=date(2026, 7, 10),
        post_start=date(2026, 7, 11), post_end=date(2026, 7, 30),
        cause_date=date(2026, 7, 1), changepoint=date(2026, 7, 11),
    )
    assert result.parallel_trend_passed
    assert result.passed
    assert result.causal_language_licensed


def test_did_denies_when_no_suitable_control_exists():
    treated = _series(100 + np.random.default_rng(3).normal(0, 1, 60))
    result = cf.difference_in_differences(
        treated, {},
        treatment_label="t", treatment_slice={},
        pre_start=date(2026, 6, 12), pre_end=date(2026, 7, 10),
        post_start=date(2026, 7, 11), post_end=date(2026, 7, 30),
        cause_date=date(2026, 7, 1), changepoint=date(2026, 7, 11),
    )
    assert not result.passed
    assert result.control is None
    assert "no comparable control" in result.reason


def test_did_denies_when_pre_period_trends_were_already_diverging():
    """Parallel trends is an assumption, and it is tested rather than assumed.

    The control here is highly *correlated* with the treated slice - they share
    a noise component and both rise - so it passes control selection. What it
    fails is the parallel-trend check: the gap between them was already
    widening before the event, so a difference-in-differences on it would
    attribute pre-existing divergence to the event.
    """
    n = 60
    rng = np.random.default_rng(31)
    shared = rng.normal(0, 1.0, n)
    treated = _series(100 + np.arange(n) * 2.0 + shared)   # climbing fast
    control = _series(100 + np.arange(n) * 0.5 + shared)   # climbing slowly

    result = cf.difference_in_differences(
        treated, {"control": control},
        treatment_label="t", treatment_slice={},
        pre_start=date(2026, 6, 12), pre_end=date(2026, 7, 10),
        post_start=date(2026, 7, 11), post_end=date(2026, 7, 30),
        cause_date=date(2026, 7, 1), changepoint=date(2026, 7, 11),
    )
    assert not result.parallel_trend_passed
    assert not result.passed
    assert "diverging" in result.parallel_trend_reason


def test_control_selection_ignores_the_event_window():
    """Controls are chosen on the pre-period only.

    Choosing on the full window would let the event influence its own
    counterfactual.
    """
    pre = 100 + np.random.default_rng(9).normal(0, 1, 40)
    treated = _series(np.concatenate([pre, pre[:20] * 0.5]))
    # tracks well before the event, diverges after
    good = _series(np.concatenate([pre * 1.02, pre[:20] * 1.02]))
    # tracks badly before, coincidentally matches after
    bad = _series(np.concatenate([pre[::-1] * 1.02, pre[:20] * 0.5]))

    name, corr, considered = cf.select_control(
        treated, {"good": good, "bad": bad},
        date(2026, 6, 1), date(2026, 7, 10),
    )
    assert name == "good"
    assert set(considered) == {"good", "bad"}


# ==========================================================================
# the causal-language gate, end to end
# ==========================================================================
def test_causal_language_is_licensed_on_the_high_confidence_scenario(
    west_attribution,
):
    a = west_attribution
    assert a.outcome is AttributionOutcome.ATTRIBUTED
    assert a.causal_language_licensed
    assert a.causal_statement("The payment gateway change") is not None


def test_causal_language_is_withdrawn_when_the_cause_postdates_the_change(
    west_detection,
):
    """The gate exists in code, not in documentation.

    Nothing about the data changes here - only the claimed cause's date. The
    licence must be withdrawn, and `causal_statement` must return None rather
    than a differently-worded sentence.
    """
    a = att.attribute(
        west_detection, ANALYST,
        cause_date=date(2026, 8, 1),          # after the changepoint
        n_resamples=40,
    )
    assert not a.causal_language_licensed
    assert a.causal_statement("The payment gateway change") is None
    # the descriptive statement is still permitted
    assert a.descriptive_statement()
    assert "West" in a.descriptive_statement()


def test_descriptive_statement_never_asserts_a_cause(west_attribution):
    text = west_attribution.descriptive_statement().lower()
    for word in ("caused", "because", "due to", "led to", "resulted in"):
        assert word not in text, f"descriptive wording contains '{word}'"


def test_causal_statement_requires_the_licence_not_the_phrasing(west_detection):
    """There is exactly one way to obtain causal wording."""
    a = att.attribute(
        west_detection, ANALYST, cause_date=None, n_resamples=40
    )
    assert not a.causal_language_licensed
    assert a.causal_statement("anything at all") is None


# ==========================================================================
# safe failure
# ==========================================================================
def test_sparse_history_prevents_attribution_entirely():
    """Attribution must not explain a movement detection never established."""
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"product_category": ["NewLaunch"]}, scenario_id="S4",
    )
    a = att.attribute(d, ANALYST, n_resamples=10)

    assert a.outcome is AttributionOutcome.NOT_ATTEMPTED_SPARSE_HISTORY
    assert a.identity is None, "LMDI must not run on sparse history"
    assert a.adtributor is None, "Adtributor must not run on sparse history"
    assert a.counterfactual is None
    assert not a.causal_language_licensed
    assert a.requires_human_review


def test_a_non_material_movement_is_not_attributed():
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"region": ["North"], "product_category": ["Electronics"]},
    )
    a = att.attribute(d, ANALYST, n_resamples=10)
    assert a.outcome is AttributionOutcome.NOT_ATTEMPTED_NOT_MATERIAL
    assert a.adtributor is None
    assert not a.causal_language_licensed


def test_schema_change_event_does_not_become_a_driver():
    """E5 is a rename with no real movement.

    Temporal adjacency to the changepoint must not be enough to make it the
    explanation; detection already found nothing material, so attribution
    must decline rather than rank the rename as a cause.
    """
    d = det.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"channel": ["Marketplace"]}, scenario_id="S7",
    )
    a = att.attribute(d, ANALYST, n_resamples=10)

    assert not a.causal_language_licensed
    if a.outcome is AttributionOutcome.ATTRIBUTED:
        # if a movement was found at all, it must not be dated at the rename
        rename = date(2026, 6, 14)
        assert d.changepoint_date is not None
        assert abs((d.changepoint_date - rename).days) > 10, (
            "the schema rename date was reported as the movement"
        )
    else:
        assert a.outcome is AttributionOutcome.NOT_ATTEMPTED_NOT_MATERIAL


def test_unstable_ranking_blocks_causal_language_even_if_did_passes(
    west_detection, monkeypatch
):
    """Two independent gates, and either one can deny.

    Asserting causation about a slice that changes between resamples would be
    unsound however clean the counterfactual looks.
    """
    real = rob.assess

    def unstable(*args, **kwargs):
        r = real(*args, **kwargs)
        r.strength = DriverStrength.UNSTABLE
        r.reason = "forced unstable for this test"
        return r

    monkeypatch.setattr(att.rob, "assess", unstable)
    a = att.attribute(
        west_detection, ANALYST, cause_date=GATEWAY_DEPLOY, n_resamples=40
    )
    assert not a.causal_language_licensed
    assert "UNSTABLE" in a.causal_language_reason


# ==========================================================================
# result completeness
# ==========================================================================
def test_attribution_result_is_complete_enough_to_audit(west_attribution):
    a = west_attribution
    assert a.kpi_id == "net_revenue"
    assert a.contract_version
    assert a.movement.changepoint_date is not None
    assert a.identity is not None and a.identity.conserved
    assert a.adtributor is not None and a.adtributor.winner is not None
    assert a.ranked_dimensions and a.ranked_slices
    assert a.explanatory_power is not None and a.surprise is not None
    assert a.robustness is not None
    assert a.counterfactual is not None
    assert a.method and "LMDI" in a.method and "adtributor" in a.method
    assert a.explain()
    # serialisable, because this object is the input to the hypothesis layer
    assert a.model_dump_json()


def test_demoted_slices_are_kept_visible(west_attribution):
    """'Considered, not selected' is itself a trust signal."""
    a = west_attribution
    assert any(not s.selected for s in a.ranked_slices), (
        "every candidate was selected; demoted slices must still be reported"
    )
    assert a.ranked_slices[0].selected


def test_attribution_reads_only_through_the_gateway(west_detection, monkeypatch):
    """Entitlement filtering happens before any ranking is computed."""
    from semantic import gateway

    seen = []
    real = gateway.guarded_query

    def spy(kpi_id, *args, **kwargs):
        seen.append(kpi_id)
        return real(kpi_id, *args, **kwargs)

    monkeypatch.setattr(gateway, "guarded_query", spy)
    att.attribute(west_detection, ANALYST, n_resamples=10, run_robustness=False)
    assert seen, "attribution performed no guarded reads"
    assert all(isinstance(k, str) for k in seen)
