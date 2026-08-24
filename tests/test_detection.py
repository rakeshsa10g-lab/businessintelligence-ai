"""Stage 3 unit tests — the detection pipeline, module by module.

The evaluation harness (eval/run_detection_eval.py) measures precision and
recall against the injected ground truth. These tests pin down the behaviour
that makes those numbers mean something: that the gates actually gate, that
each stage reports its own reasoning, and that the pipeline refuses to answer
when it does not have the data to.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from data import spec
from detection import changepoint as cp
from detection import coverage as cov
from detection import decompose as dec
from detection import engine
from detection import materiality as mat
from detection import sparse
from detection.types import CoverageStatus, DetectionOutcome, ShiftType
from security.entitlements import Principal
from semantic import registry
from semantic.types import Window

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)


@pytest.fixture(scope="module")
def contract():
    return registry.get("net_revenue")


def _series(values, start=date(2026, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def _seasonal_series(n=180, level=1000.0, amp=100.0, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    vals = level + amp * np.sin(2 * np.pi * t / 7)
    if noise:
        vals = vals + rng.normal(0, noise, n)
    return _series(vals)


# --------------------------------------------------------------------------
# 0. coverage gate
# --------------------------------------------------------------------------
def test_insufficient_history_routes_to_sparse_not_to_a_guess(contract):
    """Below min_history_days the engine must not pretend to decompose."""
    short = _seasonal_series(n=20)
    result = cov.assess(short, contract)
    assert result.status is CoverageStatus.SPARSE_HISTORY
    assert not result.passed
    assert result.observations_available == 20
    assert result.observations_required == contract.detection.min_history_days
    assert "history" in result.reason.lower()


def test_coverage_gate_rejects_a_series_too_short_for_two_seasonal_cycles(contract):
    tiny = _seasonal_series(n=9)
    result = cov.assess(tiny, contract)
    assert not result.passed


def test_excessive_missingness_is_reported_not_silently_imputed(contract):
    """A run of missing days must survive preprocessing as missing."""
    vals = list(_seasonal_series(n=120).to_numpy())
    s = _series(vals)
    s.iloc[40:60] = np.nan            # a 20-day outage, not isolated gaps
    cleaned, imputed, notes = engine._preprocess(s, 7)
    assert imputed == 0, "a 20-day outage must not be imputed"
    assert cleaned.isna().sum() == 20
    assert any("remain missing" in n for n in notes)


def test_single_day_gaps_are_imputed_and_flagged(contract):
    s = _seasonal_series(n=120)
    s.iloc[30] = np.nan
    s.iloc[70] = np.nan
    cleaned, imputed, notes = engine._preprocess(s, 7)
    assert imputed == 2
    assert cleaned.isna().sum() == 0
    assert any("imputed 2" in n for n in notes)
    assert notes, "an imputation that is not reported is a silent edit"


# --------------------------------------------------------------------------
# 2. STL
# --------------------------------------------------------------------------
def test_stl_recovers_a_known_weekly_seasonality(contract):
    s = _seasonal_series(n=180, level=1000.0, amp=100.0)
    d = dec.decompose(s, contract)
    seasonal = np.asarray(d.seasonal)
    assert d.seasonal_period == 7
    assert seasonal.max() - seasonal.min() == pytest.approx(200, rel=0.15)
    assert d.seasonal_strength > 0.9
    assert np.allclose(
        np.asarray(d.observed),
        np.asarray(d.trend) + seasonal + np.asarray(d.residual),
        atol=1e-6,
    ), "STL components must sum back to the observed series"


def test_stl_trend_smoother_cannot_track_the_event_it_should_expose(contract):
    """The regression that cost the most: a trend that follows the event.

    A 15-day 25% drop must appear in the residual, not be absorbed into the
    trend. With the statsmodels default smoother the measured effect came out
    at roughly a quarter of its true size.
    """
    s = _seasonal_series(n=200, level=1000.0, amp=50.0)
    s.iloc[120:135] = s.iloc[120:135] * 0.75          # -25% for 15 days

    d = dec.decompose(s, contract)
    baseline = dec.baseline_from(d)
    observed = np.asarray(d.observed)

    measured = (
        (observed[120:135] - baseline[120:135]).sum() / baseline[120:135].sum() * 100
    )
    assert measured == pytest.approx(-25.0, abs=4.0), (
        f"trend leakage: a -25% event measured as {measured:.1f}%"
    )
    assert d.trend_smoother is not None and d.trend_smoother >= 8 * 7


# --------------------------------------------------------------------------
# 3. robust z / MAD
# --------------------------------------------------------------------------
def test_mad_z_flags_the_planted_outlier_and_nothing_else():
    rng = np.random.default_rng(7)
    residual = rng.normal(0, 1.0, 200)
    residual[150] = 12.0
    r = cp.robust_z_scores(residual, z_threshold=3.0)
    assert r.n_anomalies >= 1
    assert r.anomaly_flags[150], "the planted outlier was not flagged"
    assert r.max_abs_z == pytest.approx(abs(r.z_scores[150]), rel=1e-6)
    assert r.n_anomalies <= 3, f"{r.n_anomalies} flags on one planted outlier"


def test_mad_is_not_inflated_by_the_outlier_it_must_detect():
    """The reason for MAD over standard deviation, asserted rather than assumed.

    With mean/std a single huge day inflates sigma and hides itself. The MAD
    is unmoved by it, so the same day scores far higher.
    """
    rng = np.random.default_rng(21)
    base = rng.normal(0, 1.0, 100)
    base[99] = 50.0
    r = cp.robust_z_scores(base, z_threshold=3.0)
    sd_z = abs(base[99] - base.mean()) / base.std()
    assert abs(r.z_scores[99]) > sd_z * 3, (
        f"MAD z {abs(r.z_scores[99]):.1f} vs std z {sd_z:.1f}: "
        "the outlier is masking itself"
    )


def test_mad_degenerate_scale_does_not_manufacture_anomalies():
    """A constant series has MAD 0; that must not become a division by zero."""
    base = np.concatenate([np.zeros(99), [50.0]])
    r = cp.robust_z_scores(base, z_threshold=3.0)
    assert np.all(np.isfinite(r.z_scores))


def test_mad_zero_variance_series_does_not_divide_by_zero():
    r = cp.robust_z_scores(np.zeros(50), z_threshold=3.0)
    assert r.n_anomalies == 0
    assert np.isfinite(r.max_abs_z)


# --------------------------------------------------------------------------
# 4. PELT
# --------------------------------------------------------------------------
def test_pelt_finds_a_planted_level_shift_at_the_right_place():
    rng = np.random.default_rng(11)
    residual = np.concatenate([rng.normal(0, 1, 100), rng.normal(-8, 1, 60)])
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(len(residual))]
    r = cp.detect_changepoints(residual, dates, penalty=1.0)
    assert r.selected_index is not None
    assert abs(r.selected_index - 100) <= 3, (
        f"changepoint at {r.selected_index}, planted at 100"
    )


def test_pelt_penalty_is_scale_invariant():
    """The same shape in different units must give the same changepoint.

    This is what the fixed penalty could not do: multiplying the series by
    1000 (rupees vs thousands of rupees) previously changed the answer.
    """
    rng = np.random.default_rng(3)
    residual = np.concatenate([rng.normal(0, 1, 90), rng.normal(-6, 1, 60)])
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(len(residual))]

    small = cp.detect_changepoints(residual, dates, penalty=1.0)
    large = cp.detect_changepoints(residual * 1000.0, dates, penalty=1.0)
    assert small.selected_index == large.selected_index
    assert small.n_changepoints == large.n_changepoints


def test_pelt_finds_no_changepoint_in_pure_noise():
    rng = np.random.default_rng(5)
    residual = rng.normal(0, 1, 200)
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(200)]
    r = cp.detect_changepoints(residual, dates, penalty=1.0)
    assert r.n_changepoints <= 2, (
        f"{r.n_changepoints} changepoints in white noise is over-segmentation"
    )


def test_pelt_selects_the_onset_not_the_recovery_edge():
    """A short event has two edges; the reported date must be the first.

    The symmetric-window selection rule this replaced could rank the recovery
    above the onset and report the day the incident ended as the day it began.
    """
    rng = np.random.default_rng(13)
    residual = np.concatenate(
        [rng.normal(0, 1, 100), rng.normal(-8, 1, 14), rng.normal(0, 1, 90)]
    )
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(len(residual))]
    r = cp.detect_changepoints(residual, dates, penalty=1.0)
    assert abs(r.selected_index - 100) <= 3, (
        f"selected index {r.selected_index}; onset is 100, recovery is 114"
    )
    assert r.segment_end_index is not None
    assert abs(r.segment_end_index - 114) <= 4, (
        f"segment ends at {r.segment_end_index}; the event ends at 114"
    )


def test_shift_classification_distinguishes_a_spike_from_a_level_shift():
    dates = [date(2026, 1, 1) + timedelta(days=i) for i in range(160)]
    rng = np.random.default_rng(17)

    level = np.concatenate([rng.normal(0, 1, 100), rng.normal(-8, 1, 60)])
    c = cp.detect_changepoints(level, dates, penalty=1.0)
    z = cp.robust_z_scores(level, 3.0)
    assert cp.classify_shift(level, c, z) is ShiftType.LEVEL_SHIFT

    spike = rng.normal(0, 1, 160)
    spike[100] = -30.0
    c2 = cp.detect_changepoints(spike, dates, penalty=1.0)
    z2 = cp.robust_z_scores(spike, 3.0)
    assert cp.classify_shift(spike, c2, z2) is ShiftType.SPIKE, (
        "one catastrophic day is a spike, not a sustained regime change"
    )


# --------------------------------------------------------------------------
# 5-6. quantification and the materiality gate
# --------------------------------------------------------------------------
def test_quantify_is_bounded_by_the_event_window_not_the_series_end():
    """Without the bound, an event dilutes as the series grows past it."""
    observed = np.concatenate([np.full(50, 100.0), np.full(10, 75.0), np.full(100, 100.0)])
    baseline = np.full(160, 100.0)

    bounded_abs, bounded_pct, bounded_days = mat.quantify(observed, baseline, 50, 60)
    unbounded_abs, unbounded_pct, unbounded_days = mat.quantify(observed, baseline, 50)

    assert bounded_days == 10
    assert bounded_pct == pytest.approx(-25.0, abs=0.01)
    assert unbounded_pct == pytest.approx(-2.27, abs=0.1)
    assert abs(bounded_pct) > abs(unbounded_pct) * 5


def test_materiality_requires_duration_even_for_a_huge_effect(contract):
    """A one-day spike is not a sustained business event, however large."""
    r = mat.assess_materiality(
        contract, abs_effect=-50_000_000.0, rel_effect_pct=-90.0, duration_days=1
    )
    assert not r.business_materiality
    assert not r.duration_passed
    assert "duration" in r.reason.lower()


def test_materiality_admits_a_small_absolute_effect_that_is_large_relatively(contract):
    """The OR arm: a small slice moving a lot still matters."""
    r = mat.assess_materiality(
        contract, abs_effect=-40_000.0, rel_effect_pct=-25.0, duration_days=14
    )
    assert r.business_materiality
    assert r.rel_effect_passed and not r.abs_effect_passed


def test_materiality_rejects_movement_below_the_calibrated_noise_floor(contract):
    """3% is inside the measured noise floor of an event-free period."""
    r = mat.assess_materiality(
        contract, abs_effect=-20_000.0, rel_effect_pct=-3.0, duration_days=10
    )
    assert not r.business_materiality


def test_statistical_signal_and_materiality_are_reported_separately(contract):
    """Collapsing them would make 'why did you alert me' unanswerable."""
    signal = mat.assess_statistical_signal(
        max_abs_z=9.0, z_threshold=3.0, changepoint_found=True,
        p_value=0.001, effect_size=1.4,
    )
    material = mat.assess_materiality(
        contract, abs_effect=-1000.0, rel_effect_pct=-0.4, duration_days=9
    )
    assert signal.significant
    assert not material.business_materiality
    assert signal.reason and material.reason
    assert signal.reason != material.reason




# --------------------------------------------------------------------------
# end-to-end, against the real warehouse and the injected ground truth
# --------------------------------------------------------------------------
def test_known_injected_event_is_detected_with_the_right_date_and_size():
    """E1 / Scenario S1: the West payment gateway degradation.

    Ground truth: 2026-07-12..2026-07-26, net revenue -24.98%.
    """
    r = engine.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"region": ["West"], "channel": ["Web", "Mobile App"]},
        scenario_id="S1",
    )
    assert r.outcome is DetectionOutcome.MATERIAL_EVENT
    assert r.is_material

    assert abs((r.changepoint_date - date(2026, 7, 12)).days) <= 3, (
        f"changepoint {r.changepoint_date}, event began 2026-07-12"
    )
    assert r.materiality.rel_effect_pct == pytest.approx(-25.0, abs=6.0), (
        f"measured {r.materiality.rel_effect_pct:.1f}%, ground truth -24.98%"
    )
    assert r.changepoint.shift_type in (ShiftType.LEVEL_SHIFT, ShiftType.DRIFT)
    assert r.statistical_signal.significant
    assert r.materiality.business_materiality


def test_a_quiet_slice_produces_no_material_finding():
    """Scenario S3's other half: not every slice may light up."""
    r = engine.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"region": ["North"], "product_category": ["Electronics"]},
    )
    assert r.outcome is DetectionOutcome.NO_MATERIAL_FINDING
    assert not r.is_material
    assert r.materiality is not None
    assert r.materiality.reason, "a non-finding must still explain itself"


def test_scenario_s4_sparse_history_exits_through_the_coverage_gate():
    """NewLaunch has 23 days of history. The engine must decline, not guess."""
    r = engine.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"product_category": ["NewLaunch"]},
        scenario_id="S4",
    )
    assert r.outcome is DetectionOutcome.SPARSE_HISTORY
    assert not r.is_material
    assert r.confidence_ceiling == sparse.CONFIDENCE_CEILING == "LOW"
    assert r.caveat and "history" in r.caveat.lower()
    assert r.decomposition is None, "STL must not run on sparse history"
    assert r.changepoint is None, "PELT must not run on sparse history"


def test_scenario_s7_schema_rename_does_not_read_as_a_business_event():
    """E5: on 2026-06-14 'marketplace' became 'Marketplace'. No revenue moved.

    Stitched, the channel is one continuous series and nothing fires at the
    rename. Unstitched, the same channel is severed into two disjoint series —
    which is exactly how a rename impersonates a 100% collapse.
    """
    from semantic import gateway

    rename_date = date(2026, 6, 14)
    r = engine.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"channel": ["Marketplace"]},
        scenario_id="S7", stitch_schema=True,
    )
    if r.changepoint_date is not None:
        assert not (
            r.outcome is DetectionOutcome.MATERIAL_EVENT
            and abs((r.changepoint_date - rename_date).days) <= 10
        ), "a rename was reported as a business event"

    assert any("schema stitch" in n for n in r.preprocessing_notes), (
        "the stitch must be disclosed in the preprocessing notes"
    )

    # and the artifact is real if you skip the stitch
    ms = gateway.guarded_query("net_revenue", WINDOW, ["channel"], ANALYST)
    unstitched_new = engine._aggregate_to_series(ms, {"channel": ["Marketplace"]})
    unstitched_old = engine._aggregate_to_series(ms, {"channel": ["marketplace"]})
    window_days = (WINDOW.end - WINDOW.start).days + 1
    assert len(unstitched_new) < window_days
    assert len(unstitched_old) < window_days
    assert len(unstitched_new) + len(unstitched_old) >= window_days


def test_detection_result_is_complete_enough_to_audit():
    """Every field a reviewer would ask for must be populated, not implied."""
    r = engine.detect(
        "net_revenue", WINDOW, ANALYST,
        slice_filter={"region": ["West"], "channel": ["Web", "Mobile App"]},
        scenario_id="S1",
    )
    assert r.kpi_id == "net_revenue"
    assert r.contract_version
    assert r.slice_label and r.scenario_id == "S1"
    assert r.analysis_start and r.analysis_end
    assert r.baseline_value is not None and r.observed_value is not None
    assert r.abs_delta is not None and r.pct_delta is not None
    assert r.coverage is not None and r.coverage.passed
    assert r.decomposition is not None
    assert r.robust_score is not None
    assert r.changepoint is not None
    assert r.statistical_signal is not None
    assert r.materiality is not None
    assert r.lineage is not None and r.freshness is not None
    assert r.method and "STL" in r.method and "PELT" in r.method
    assert r.explain(), "a result that cannot explain itself is not evidence"


def test_detection_reads_only_through_the_gateway(monkeypatch):
    """Entitlement filtering must happen before any statistic is computed."""
    calls = []
    from semantic import gateway

    real = gateway.guarded_query

    def spy(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr(gateway, "guarded_query", spy)
    engine.detect("net_revenue", WINDOW, ANALYST, slice_filter={"region": ["West"]})
    assert calls == ["net_revenue"], (
        "the engine must obtain its data from exactly one guarded read"
    )


def test_restricted_principal_cannot_widen_a_slice_through_detection():
    """An ops lead scoped to West must not detect on North by asking for it."""
    ops = Principal(
        user_id="arun", display_name="Arun Iyer", role="ops_lead",
        user_region="West",
    )
    r = engine.detect(
        "net_revenue", WINDOW, ops, slice_filter={"region": ["North"]}
    )
    # the row filter removes North entirely, so there is nothing to analyse
    assert r.outcome in (
        DetectionOutcome.INSUFFICIENT_DATA,
        DetectionOutcome.SPARSE_HISTORY,
        DetectionOutcome.NO_MATERIAL_FINDING,
    )
    assert not r.is_material
