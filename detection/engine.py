"""The detection engine — orchestrates the flow in Part 9.2.

    raw KPI series (entitlement-filtered, via the semantic chokepoint)
      -> 0. COVERAGE GATE      -> SPARSE_HISTORY path when it fails
      -> 1. PREPROCESS         calendar align, impute single-day gaps,
                               schema stitching, hard-fail if >10% imputed
      -> 2. DECOMPOSE          STL(period from contract, robust=True)
      -> 3. POINT ANOMALY      MAD-based robust z
      -> 4. REGIME SHIFT       PELT on the residual, classify the shift
      -> 5. QUANTIFY           effect vs the trend+seasonal counterfactual
      -> 6. MATERIALITY GATE   business rule from the contract
      -> DetectionResult

The engine never opens a database connection. It reads through
`gateway.guarded_query`, so entitlement filtering has already happened by the
time any statistics run — a restricted row cannot influence a detection.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from detection import changepoint as cp
from detection import coverage as cov
from detection import decompose as dec
from detection import materiality as mat
from detection import sparse
from detection.types import (
    CoverageStatus,
    DetectionOutcome,
    DetectionResult,
    ShiftType,
)
from security.entitlements import Principal
from semantic import gateway, registry
from semantic.types import MetricSeries, Window

# Baseline comparison window used to report observed-vs-baseline levels.
BASELINE_DAYS = 28


# --------------------------------------------------------------------------
# series construction
# --------------------------------------------------------------------------
def _aggregate_to_series(ms: MetricSeries, slice_filter: dict) -> pd.Series:
    """Collapse the gateway result to one daily series for the slice.

    Ratio KPIs are re-aggregated as sum(numerator)/sum(denominator). Averaging
    a ratio across slices would be wrong, and the contract already tells us
    which case we are in via `additive`.
    """
    df = ms.df.copy()
    time_key = ms.grain[0]

    for dim, values in (slice_filter or {}).items():
        if dim in df.columns:
            df = df[df[dim].isin(values)]

    if df.empty:
        return pd.Series(dtype=float)

    if ms.additive or "numerator" not in df.columns:
        grouped = df.groupby(time_key)["value"].sum()
    else:
        agg = df.groupby(time_key)[["numerator", "denominator"]].sum()
        grouped = agg["numerator"] / agg["denominator"].replace(0, np.nan)

    grouped.index = pd.to_datetime(grouped.index).date
    return grouped.sort_index()


def _stitch_schema_changes(
    df: pd.DataFrame, renames: list[dict]
) -> tuple[pd.DataFrame, list[str]]:
    """Apply recorded value renames before aggregation.

    Without this the E5 marketplace rename appears as a genuine collapse in
    one series and a sudden appearance in another. This step is the Reddit
    finding made operational (Part 9.3).
    """
    notes: list[str] = []
    for rec in renames:
        col, old, new = rec["column_name"], rec.get("old_value"), rec.get("new_value")
        if col not in df.columns or not old or not new:
            continue
        n = int((df[col] == old).sum())
        if n:
            df[col] = df[col].replace({old: new})
            notes.append(
                f"schema stitch: {col} '{old}' -> '{new}' on "
                f"{rec['changed_at']:%Y-%m-%d} ({n:,} rows), per "
                f"schema_change_log {rec['change_id']}"
            )
    return df, notes


def _preprocess(
    series: pd.Series, period: int
) -> tuple[pd.Series, int, list[str]]:
    """Calendar-align and impute isolated single-day gaps.

    Only single-day gaps are imputed, by the seasonal median (same weekday).
    A run of two or more consecutive missing days is left missing so the
    coverage gate can see it — silently filling a real outage is how a
    detector learns to ignore outages.
    """
    notes: list[str] = []
    if series.empty:
        return series, 0, notes

    full_index = pd.date_range(series.index.min(), series.index.max(), freq="D").date
    aligned = series.reindex(full_index)
    missing = aligned.isna()
    if not missing.any():
        return aligned, 0, notes

    # isolated gaps only: missing, with a present neighbour on both sides
    prev_present = ~missing.shift(1, fill_value=False)
    next_present = ~missing.shift(-1, fill_value=False)
    isolated = missing & prev_present & next_present

    imputed = 0
    if isolated.any():
        weekday = pd.Series([d.weekday() for d in aligned.index], index=aligned.index)
        seasonal_median = aligned.groupby(weekday).transform("median")
        aligned = aligned.where(~isolated, seasonal_median)
        imputed = int(isolated.sum())
        notes.append(
            f"imputed {imputed} isolated single-day gap(s) by same-weekday median"
        )

    still_missing = int(aligned.isna().sum())
    if still_missing:
        notes.append(
            f"{still_missing} day(s) remain missing (runs of 2+ are not imputed)"
        )
    return aligned, imputed, notes


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------
def detect(
    kpi_id: str,
    window: Window,
    principal: Principal,
    *,
    slice_filter: dict[str, list[str]] | None = None,
    scenario_id: str | None = None,
    penalty: float | None = None,
    z_threshold: float | None = None,
    stitch_schema: bool = True,
    peers: dict[str, pd.Series] | None = None,
) -> DetectionResult:
    """Run the full detection pipeline for one KPI and one slice."""
    contract = registry.get(kpi_id)
    slice_filter = slice_filter or {}
    slice_label = (
        " x ".join(f"{k}={'/'.join(v)}" for k, v in slice_filter.items())
        if slice_filter
        else "ALL"
    )

    z_thr = z_threshold if z_threshold is not None else contract.detection.z_threshold
    pen = penalty if penalty is not None else contract.detection.pelt_penalty

    # --- read through the chokepoint ---------------------------------------
    dims = [d for d in slice_filter if d in contract.dimension_names()]
    ms = gateway.guarded_query(kpi_id, window, dims, principal)

    notes: list[str] = []
    df = ms.df
    if stitch_schema:
        renames = gateway.schema_changes()
        df, stitch_notes = _stitch_schema_changes(df.copy(), renames)
        notes.extend(stitch_notes)
        ms = ms.model_copy(update={"df": df})

    raw = _aggregate_to_series(ms, slice_filter)

    base = dict(
        kpi_id=kpi_id,
        contract_version=contract.version,
        slice=slice_filter,
        slice_label=slice_label,
        scenario_id=scenario_id,
        analysis_start=window.start,
        analysis_end=window.end,
        freshness=ms.freshness,
        lineage=ms.lineage,
        computed_at=datetime.now(),
    )

    # --- 1. preprocess ------------------------------------------------------
    series, imputed, pre_notes = _preprocess(raw, contract.detection.seasonality_period)
    notes.extend(pre_notes)

    # --- 0. coverage gate ---------------------------------------------------
    coverage = cov.assess(series, contract)
    coverage.imputed_days = imputed

    if imputed and len(series):
        imputed_rate = imputed / len(series)
        if imputed_rate > cov.MAX_MISSING_RATE:
            coverage.status = CoverageStatus.EXCESSIVE_MISSINGNESS
            coverage.reason = (
                f"{imputed} of {len(series)} days imputed ({imputed_rate:.1%}); "
                f"threshold is {cov.MAX_MISSING_RATE:.0%}."
            )

    if coverage.status is CoverageStatus.SPARSE_HISTORY:
        peer_info = None
        if peers:
            peer_info = sparse.peer_cohort_baseline(
                series.dropna(),
                peers,
                subject_label=slice_label,
                launch_date=series.dropna().index.min(),
            )
        return DetectionResult(
            **base,
            coverage=coverage,
            outcome=DetectionOutcome.SPARSE_HISTORY,
            is_material=False,
            method="coverage_gate -> peer_cohort_baseline",
            preprocessing_notes=notes,
            peer_cohort=peer_info,
            confidence_ceiling=sparse.CONFIDENCE_CEILING,
            caveat=sparse.caveat_text(
                coverage.observations_available,
                coverage.observations_required,
                coverage.seasonal_period,
            ),
        )

    if not coverage.passed:
        return DetectionResult(
            **base,
            coverage=coverage,
            outcome=DetectionOutcome.INSUFFICIENT_DATA,
            is_material=False,
            method="coverage_gate",
            preprocessing_notes=notes,
        )

    clean = series.dropna()

    # --- 2. decompose -------------------------------------------------------
    decomposition = dec.decompose(clean, contract, robust=True)
    residual = np.asarray(decomposition.residual)
    observed = np.asarray(decomposition.observed)
    baseline_curve = dec.baseline_from(decomposition)
    dates = decomposition.dates

    # --- 3. point anomaly ---------------------------------------------------
    robust = cp.robust_z_scores(residual, z_thr)

    # --- 4. regime shift ----------------------------------------------------
    changes = cp.detect_changepoints(residual, dates, penalty=pen)
    changes.shift_type = cp.classify_shift(residual, changes, robust)

    # --- 5. quantify --------------------------------------------------------
    if changes.selected_index is not None:
        split = changes.selected_index
        split_end = changes.segment_end_index
    elif robust.n_anomalies:
        split = int(np.argmax(np.abs(robust.z_scores)))
        split_end = None
    else:
        split = max(0, len(observed) - BASELINE_DAYS)
        split_end = None

    abs_effect, rel_effect_pct, duration = mat.quantify(
        observed, baseline_curve, split, split_end
    )
    p_value, effect_size = mat.welch_test(
        residual, split, split_end, baseline_days=BASELINE_DAYS
    )

    signal = mat.assess_statistical_signal(
        max_abs_z=robust.max_abs_z,
        z_threshold=z_thr,
        changepoint_found=changes.selected_index is not None,
        p_value=p_value,
        effect_size=effect_size,
    )

    # --- 6. materiality gate ------------------------------------------------
    materiality = mat.assess_materiality(
        contract,
        abs_effect=abs_effect,
        rel_effect_pct=rel_effect_pct,
        duration_days=duration,
    )

    is_material = signal.significant and materiality.business_materiality
    outcome = (
        DetectionOutcome.MATERIAL_EVENT
        if is_material
        else DetectionOutcome.NO_MATERIAL_FINDING
    )

    # observed vs baseline levels, for reporting
    pre_slice = observed[max(0, split - BASELINE_DAYS) : split]
    post_slice = observed[split : (split_end if split_end is not None else len(observed))]
    baseline_value = float(np.mean(pre_slice)) if pre_slice.size else None
    observed_value = float(np.mean(post_slice)) if post_slice.size else None
    abs_delta = (
        observed_value - baseline_value
        if baseline_value is not None and observed_value is not None
        else None
    )
    pct_delta = (
        (abs_delta / baseline_value * 100.0)
        if abs_delta is not None and baseline_value
        else None
    )

    return DetectionResult(
        **base,
        baseline_start=dates[max(0, split - BASELINE_DAYS)] if dates else None,
        baseline_end=dates[max(0, split - 1)] if dates else None,
        observed_start=dates[split] if split < len(dates) else None,
        observed_end=(
            changes.segment_end_date
            if changes.segment_end_date is not None
            else (dates[-1] if dates else None)
        ),
        baseline_value=baseline_value,
        observed_value=observed_value,
        abs_delta=abs_delta,
        pct_delta=pct_delta,
        coverage=coverage,
        decomposition=decomposition,
        robust_score=robust,
        changepoint=changes,
        statistical_signal=signal,
        materiality=materiality,
        outcome=outcome,
        is_material=is_material,
        method=(
            f"coverage_gate -> STL(period={decomposition.seasonal_period},robust) "
            f"-> robust_z(MAD,z>={z_thr}) -> PELT(l2,pen={pen}) "
            f"-> materiality({contract.materiality.rule[:40]}...)"
        ),
        preprocessing_notes=notes,
    )


def build_peer_series(
    kpi_id: str,
    window: Window,
    principal: Principal,
    dimension: str,
    peer_values: list[str],
) -> dict[str, pd.Series]:
    """Daily series for each peer value, for the sparse-history comparison."""
    ms = gateway.guarded_query(kpi_id, window, [dimension], principal)
    out: dict[str, pd.Series] = {}
    for value in peer_values:
        s = _aggregate_to_series(ms, {dimension: [value]})
        if not s.empty:
            out[value] = s
    return out
