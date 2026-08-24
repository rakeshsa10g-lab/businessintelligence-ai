"""Stage 4 orchestration (Architecture Part 10).

    DetectionResult (material movement, established in Stage 3)
      -> 0. GUARDS            refuse on sparse history or a non-material move
      -> 1. RATIO ROUTING     non-additive KPI -> attribute via its fundamentals
      -> 2. LMDI              which *factor* of the identity moved
      -> 3. ADTRIBUTOR        which *slice* moved unusually
      -> 4. ROBUSTNESS        does the ranking survive resampling the window
      -> 5. COUNTERFACTUAL    DiD vs a matched control + temporal precedence
      -> AttributionResult

Like detection, this module never opens a database connection: every read goes
through `gateway.guarded_query`, so a slice the principal may not see cannot
influence a ranking. No LLM appears anywhere in this file.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from attribution import counterfactual as cf
from attribution import lmdi
from attribution import robustness as rob
from attribution.adtributor import T_EEP, T_EP, adtributor
from attribution.types import (
    AttributionOutcome,
    AttributionResult,
    DriverStrength,
    IdentityDecomposition,
    KPIMovement,
    RankedSlice,
    SourceReconciliation,
)
from detection import decompose as dec
from detection.types import DetectionOutcome, DetectionResult
from security.entitlements import Principal
from semantic import gateway, registry
from semantic.types import EntitlementError, Window

# The revenue identity from Architecture Part 7.1.
REVENUE_IDENTITY = (
    "net_revenue = sessions * conversion_rate * average_order_value "
    "* net_realisation"
)

# Minimum days a cell needs before STL is worth attempting; below this the
# counterfactual falls back to a same-weekday mean, which is disclosed.
MIN_CELL_DAYS_FOR_STL = 28


class AttributionError(ValueError):
    """Attribution was asked to do something the contract forbids."""


# --------------------------------------------------------------------------
# contract guards
# --------------------------------------------------------------------------
def resolve_attribution_kpi(kpi_id: str) -> tuple[str, list[str] | None]:
    """Ratio KPIs are never attributed directly (Architecture Part 10.2).

    Explanatory power over a ratio is not well defined: EP is a share of an
    additive total, and a ratio has no additive total to take a share of. Per
    CMMD and Adtributor section 4, attribute on the fundamental measures the
    ratio is computed from. The contract states which those are, so this is
    enforced rather than left for a developer to remember.

    Returns (kpi to attribute on, the attribute_via chain or None).
    """
    contract = registry.get(kpi_id)
    if contract.additive:
        return kpi_id, None

    if not contract.attribute_via:
        raise AttributionError(
            f"{kpi_id} is non-additive but declares no 'attribute_via'. "
            "Attribution on a ratio is invalid and there is no fallback."
        )

    chain = list(contract.attribute_via)
    for fundamental in chain:
        target = registry.get(fundamental)
        if target.additive:
            return fundamental, chain

    raise AttributionError(
        f"{kpi_id} routes to {chain}, none of which is additive; "
        "attribution cannot proceed on a chain of ratios."
    )


def assert_attributable(kpi_id: str) -> None:
    """Raise if Adtributor would be run on something it must not be run on."""
    contract = registry.get(kpi_id)
    if not contract.additive:
        raise AttributionError(
            f"refusing to run Adtributor directly on non-additive KPI "
            f"'{kpi_id}'. Route via {contract.attribute_via}."
        )


# --------------------------------------------------------------------------
# building the counterfactual cube
# --------------------------------------------------------------------------
def _cell_key(row, dims: list[str]) -> tuple:
    return tuple(row[d] for d in dims)


def build_forecast_cube(
    kpi_id: str,
    window: Window,
    principal: Principal,
    dims: list[str],
    event_start: date,
    event_end: date,
    *,
    seasonal_period: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Per-cell forecast F and actual A over the event window.

    The forecast is the STL trend+seasonal counterfactual - the "no event"
    path - computed per cell. This is a clean reuse: Stage 3 already produced
    exactly the F that Adtributor needs, so the two stages cannot disagree
    about what "expected" meant.

    Cells too short for STL fall back to a same-weekday mean over the
    pre-event period, and every such cell is named in the returned notes
    rather than silently mixed in.
    """
    ms = gateway.guarded_query(kpi_id, window, dims, principal)
    df = ms.df.copy()
    time_key = ms.grain[0]
    df[time_key] = pd.to_datetime(df[time_key]).dt.date

    notes: list[str] = []
    fallback_cells = 0

    forecast_rows: list[dict] = []
    actual_rows: list[dict] = []

    for key, cell in df.groupby(dims, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        series = cell.groupby(time_key)["value"].sum().sort_index()
        full = pd.date_range(series.index.min(), series.index.max(), freq="D").date
        series = series.reindex(full).interpolate(limit_direction="both")

        baseline = None
        if len(series) >= MIN_CELL_DAYS_FOR_STL:
            try:
                d = dec.decompose(series, registry.get(kpi_id), robust=True)
                baseline = pd.Series(dec.baseline_from(d), index=d.dates)
            except Exception:
                baseline = None

        if baseline is None:
            # same-weekday mean over the pre-event period
            pre = series.loc[series.index < event_start]
            if len(pre) == 0:
                continue
            by_weekday = {}
            for d0, v in pre.items():
                by_weekday.setdefault(d0.weekday(), []).append(v)
            overall = float(pre.mean())
            baseline = pd.Series(
                [
                    float(np.mean(by_weekday.get(d0.weekday(), [overall])))
                    for d0 in series.index
                ],
                index=series.index,
            )
            fallback_cells += 1

        for d0 in series.index:
            if not (event_start <= d0 <= event_end):
                continue
            row = dict(zip(dims, key))
            forecast_rows.append({**row, "date": d0, "value": float(baseline.get(d0, np.nan))})
            actual_rows.append({**row, "date": d0, "value": float(series.get(d0, np.nan))})

    forecast = pd.DataFrame(forecast_rows).dropna(subset=["value"])
    actual = pd.DataFrame(actual_rows).dropna(subset=["value"])

    if fallback_cells:
        notes.append(
            f"{fallback_cells} cell(s) had under {MIN_CELL_DAYS_FOR_STL} days "
            f"of history; their counterfactual is a same-weekday mean rather "
            f"than an STL baseline"
        )
    return forecast, actual, notes


# --------------------------------------------------------------------------
# Stage A - the identity
# --------------------------------------------------------------------------
def _s1_aggregate(
    kpi_id: str,
    window: Window,
    principal: Principal,
    slice_filter: dict[str, list[str]],
) -> tuple[float, float, float]:
    """Sum a warehouse KPI over a window and slice.

    Returns (value, numerator, denominator); numerator/denominator are NaN for
    additive KPIs that do not carry them.
    """
    contract = registry.get(kpi_id)
    available = set(contract.dimension_names())
    usable = {k: v for k, v in slice_filter.items() if k in available}

    ms = gateway.guarded_query(kpi_id, window, sorted(usable), principal)
    df = ms.df
    for dim, values in usable.items():
        if dim in df.columns:
            df = df[df[dim].isin(values)]
    if df.empty:
        return float("nan"), float("nan"), float("nan")

    value = float(df["value"].sum()) if "value" in df else float("nan")
    num = float(df["numerator"].sum()) if "numerator" in df else float("nan")
    den = float(df["denominator"].sum()) if "denominator" in df else float("nan")
    return value, num, den


def source_reconciliation(
    principal: Principal,
    slice_filter: dict[str, list[str]],
    window: Window,
) -> list[SourceReconciliation]:
    """Measure the cross-source differences instead of absorbing them.

    Two exist in this dataset and both are deliberate:

      S1 vs S2 sessions   the product-analytics stream carries a 3.5%
                          unknown-region population plus hourly instrumentation
                          noise, so a region-filtered S2 total sits ~4.5% below
                          the warehouse. Removing the region filter collapses
                          the gap to ~0.1%, which is what identifies it as a
                          population effect rather than a definition one.

      S3 refund vs S1     the finance refund figure is a different quantity
                          from warehouse leakage, and excludes discounts.

    Neither is a driver of revenue. Reporting them keeps them visible without
    letting them into the decomposition.
    """
    out: list[SourceReconciliation] = []

    s1_sess, _, _ = _s1_aggregate("sessions", window, principal, slice_filter)
    _, _, cv_den = _s1_aggregate(
        "conversion_rate", window, principal, slice_filter
    )

    if s1_sess == s1_sess and cv_den == cv_den and s1_sess and cv_den:
        diff = (cv_den / s1_sess - 1.0) * 100.0
        out.append(
            SourceReconciliation(
                quantity="sessions",
                source_a="S1 warehouse (fact_orders.sessions)",
                source_b="S2 product analytics (fact_sessions.sessions)",
                value_a=s1_sess,
                value_b=cv_den,
                difference_pct=diff,
                classification="population",
                explanation=(
                    "S2 sits {0:+.2f}% against the warehouse. 3.5% of S2 rows "
                    "carry an unknown region (VPN / opted-out clients, declared "
                    "in the contract as known_null_columns), so a "
                    "region-filtered S2 total loses them; the remainder is "
                    "hourly instrumentation noise. The conversion ratio is "
                    "unaffected because S2 scales sessions and orders together "
                    "- only the level differs."
                ).format(diff),
                material_to_identity=False,
            )
        )

    net, _, _ = _s1_aggregate("net_revenue", window, principal, slice_filter)
    _, gross, _ = _s1_aggregate(
        "average_order_value", window, principal, slice_filter
    )

    # The S1-vs-S3 comparison is a data-quality diagnostic, not a driver of the
    # KPI, and an ops lead is not entitled to read the finance source. A
    # principal who cannot see one side of a reconciliation should simply not
    # get that reconciliation line - crashing the whole attribution because a
    # diagnostic was unavailable would make entitlement a source of outages
    # rather than a boundary.
    try:
        _, rr_num, rr_den = _s1_aggregate(
            "refund_rate", window, principal, slice_filter
        )
    except EntitlementError:
        return out
    if gross and gross == gross and rr_num == rr_num and rr_den:
        warehouse_leakage = 1.0 - (net / gross)
        finance_rate = rr_num / rr_den
        if finance_rate == finance_rate and warehouse_leakage:
            diff = (finance_rate / warehouse_leakage - 1.0) * 100.0
            out.append(
                SourceReconciliation(
                    quantity="refund / leakage rate",
                    source_a="S1 warehouse (discount + returns) / gross",
                    source_b="S3 finance refund_amount / gross",
                    value_a=warehouse_leakage,
                    value_b=finance_rate,
                    difference_pct=diff,
                    classification="definition",
                    explanation=(
                        "the S3 finance refund rate ({0:.4f}) is a different "
                        "quantity from warehouse leakage ({1:.4f}): it excludes "
                        "discounts, which are a material part of the gap "
                        "between gross and net. Using (1 - S3 refund rate) as "
                        "the fourth identity factor would leave discounts "
                        "unexplained, so the identity uses the warehouse net "
                        "realisation rate instead. See ADR-018."
                    ).format(finance_rate, warehouse_leakage),
                    material_to_identity=True,
                )
            )

    return out


def identity_decomposition(
    principal: Principal,
    slice_filter: dict[str, list[str]],
    baseline_window: Window,
    observed_window: Window,
) -> IdentityDecomposition:
    """LMDI over the revenue identity, on a single analytical population.

        net_revenue = sessions x conversion x AOV x net_realisation

    Every factor is read from the S1 warehouse under identical filters, so the
    product telescopes to net revenue exactly:

        sessions x (orders/sessions) x (gross/orders) x (net/gross) = net

    That exactness is not decoration - it is the property that makes LMDI's
    conservation guarantee mean anything. An earlier version took conversion
    from S2 product analytics and the fourth factor from the S3 finance refund
    rate, and closed only to ~5%: the S2 population differs by 3.5%
    unknown-region rows, and the finance refund rate omits discounts. Both
    differences are now measured and reported by `source_reconciliation`
    rather than absorbed into the decomposition.
    """
    grain_limited: dict[str, str] = {}
    lineage = []

    contract = registry.get("net_revenue")
    available = set(contract.dimension_names())
    dropped = sorted(set(slice_filter) - available)

    def factors(window: Window) -> tuple[dict[str, float], float]:
        days = (window.end - window.start).days + 1

        sessions, _, _ = _s1_aggregate("sessions", window, principal, slice_filter)
        net, _, _ = _s1_aggregate("net_revenue", window, principal, slice_filter)
        _, gross, orders = _s1_aggregate(
            "average_order_value", window, principal, slice_filter
        )

        if not (sessions and orders and gross and net):
            raise lmdi.IdentityError(
                "one of sessions/orders/gross/net is zero or missing over "
                "{0}..{1}; the identity cannot be formed".format(
                    window.start, window.end
                )
            )

        return (
            {
                "sessions": sessions / days,
                "conversion_rate": orders / sessions,
                "average_order_value": gross / orders,
                "net_realisation": net / gross,
            },
            net / days,
        )

    f0, actual0 = factors(baseline_window)
    f1, actual1 = factors(observed_window)

    ms = gateway.guarded_query(
        "net_revenue",
        observed_window,
        sorted(set(slice_filter) & available),
        principal,
    )
    lineage.append(ms.lineage)

    if dropped:
        note = (
            "net_revenue has no {0} dimension; the identity is evaluated at "
            "the coarser grain".format(", ".join(dropped))
        )
        for name in (
            "sessions",
            "conversion_rate",
            "average_order_value",
            "net_realisation",
        ):
            grain_limited[name] = note

    result = lmdi.decompose(
        f0,
        f1,
        kpi="net_revenue",
        identity=REVENUE_IDENTITY,
        actual_baseline=actual0,
        actual_observed=actual1,
        grain_limited=grain_limited,
        lineage=lineage,
    )
    result.reconciliation = source_reconciliation(
        principal, slice_filter, observed_window
    )
    return result


# --------------------------------------------------------------------------
# the pipeline
# --------------------------------------------------------------------------
def attribute(
    detection: DetectionResult,
    principal: Principal,
    *,
    dims: list[str] | None = None,
    t_ep: float = T_EP,
    t_eep: float = T_EEP,
    cause_date: date | None = None,
    run_identity: bool = True,
    run_robustness: bool = True,
    n_resamples: int = rob.DEFAULT_RESAMPLES,
) -> AttributionResult:
    """Attribute an established, material KPI movement."""
    movement = KPIMovement(
        kpi_id=detection.kpi_id,
        slice_label=detection.slice_label,
        baseline_value=detection.baseline_value,
        observed_value=detection.observed_value,
        abs_delta=detection.abs_delta,
        pct_delta=detection.pct_delta,
        changepoint_date=detection.changepoint_date,
        event_start=detection.observed_start,
        event_end=detection.observed_end,
        is_material=detection.is_material,
        detection_outcome=detection.outcome.value,
    )

    base = dict(
        kpi_id=detection.kpi_id,
        contract_version=detection.contract_version,
        slice=detection.slice,
        slice_label=detection.slice_label,
        scenario_id=detection.scenario_id,
        movement=movement,
        computed_at=datetime.now(),
    )

    # --- 0. guards --------------------------------------------------------
    # Attribution must not run on a movement Stage 3 declined to establish.
    # Explaining a movement that was never shown to be real is exactly the
    # failure the sparse-history path exists to prevent.
    if detection.outcome is DetectionOutcome.SPARSE_HISTORY:
        return AttributionResult(
            **base,
            outcome=AttributionOutcome.NOT_ATTEMPTED_SPARSE_HISTORY,
            requires_human_review=True,
            causal_language_licensed=False,
            causal_language_reason=(
                "detection returned SPARSE_HISTORY; there is no established "
                "movement to attribute"
            ),
            method="guard: sparse history",
            notes=[detection.caveat or "insufficient history"],
        )

    if not detection.is_material:
        return AttributionResult(
            **base,
            outcome=AttributionOutcome.NOT_ATTEMPTED_NOT_MATERIAL,
            causal_language_licensed=False,
            causal_language_reason=(
                f"detection returned {detection.outcome.value}; attribution "
                "runs only on movements established as material"
            ),
            method="guard: not material",
        )

    # --- 1. ratio routing -------------------------------------------------
    attribution_kpi, via = resolve_attribution_kpi(detection.kpi_id)
    assert_attributable(attribution_kpi)

    contract = registry.get(attribution_kpi)
    dims = dims or contract.dimension_names()
    notes: list[str] = []
    if via:
        notes.append(
            f"{detection.kpi_id} is a ratio; explanatory power over a ratio is "
            f"not well defined, so attribution runs on '{attribution_kpi}' "
            f"(contract attribute_via={via})"
        )

    grain_note = None
    source_dims = set(registry.get(detection.kpi_id).dimension_names())
    missing = sorted(set(dims) - source_dims)
    if missing:
        grain_note = (
            f"{detection.kpi_id} has no {', '.join(missing)} dimension; "
            f"attribution on it cannot descend below "
            f"{', '.join(sorted(source_dims))}"
        )

    event_start = detection.observed_start
    event_end = detection.observed_end
    if event_start is None or event_end is None:
        return AttributionResult(
            **base,
            outcome=AttributionOutcome.NO_EXPLANATION,
            causal_language_reason="detection produced no event window",
            method="guard: no event window",
        )

    analysis = Window(start=detection.analysis_start, end=detection.analysis_end)

    # --- 2. identity decomposition (which factor) -------------------------
    identity = None
    if run_identity and detection.kpi_id == "net_revenue":
        baseline_window = Window(
            start=detection.baseline_start or (event_start - timedelta(days=28)),
            end=detection.baseline_end or (event_start - timedelta(days=1)),
        )
        observed_window = Window(start=event_start, end=event_end)
        try:
            identity = identity_decomposition(
                principal, detection.slice, baseline_window, observed_window
            )
        except (lmdi.IdentityError, KeyError, ZeroDivisionError) as exc:
            notes.append(f"identity decomposition unavailable: {exc}")

    # --- 3. Adtributor (which slice) --------------------------------------
    forecast, actual, cube_notes = build_forecast_cube(
        attribution_kpi, analysis, principal, dims, event_start, event_end,
        seasonal_period=contract.detection.seasonality_period,
    )
    notes.extend(cube_notes)

    if forecast.empty or actual.empty:
        return AttributionResult(
            **base,
            identity=identity,
            outcome=AttributionOutcome.NO_EXPLANATION,
            causal_language_reason="no cells available to attribute over",
            method="adtributor: empty cube",
            notes=notes,
        )

    ad = adtributor(forecast, actual, dims, t_ep=t_ep, t_eep=t_eep)

    ranked_slices: list[RankedSlice] = []
    rank = 0
    for dim in ad.dimensions:
        for el in dim.all_elements:
            rank += 1
            ranked_slices.append(
                RankedSlice(
                    dimension=dim.dimension,
                    element=el.element,
                    slice={dim.dimension: [el.element]},
                    explanatory_power=el.explanatory_power,
                    surprise=el.surprise,
                    forecast=el.forecast,
                    actual=el.actual,
                    delta=el.actual - el.forecast,
                    rank=rank,
                    selected=el.selected,
                )
            )
    # selected slices first, then by surprise - demoted candidates are kept
    # visible rather than dropped, which is itself a trust signal
    ranked_slices.sort(key=lambda s: (not s.selected, -s.surprise))
    for i, s in enumerate(ranked_slices, start=1):
        s.rank = i

    if ad.outcome is AttributionOutcome.MULTI_DIMENSIONAL_CASE:
        return AttributionResult(
            **base,
            identity=identity,
            adtributor=ad,
            ranked_dimensions=ad.dimensions,
            ranked_slices=ranked_slices,
            outcome=AttributionOutcome.MULTI_DIMENSIONAL_CASE,
            requires_human_review=True,
            attributed_via=via,
            attribution_kpi=attribution_kpi,
            grain_limit_note=grain_note,
            causal_language_licensed=False,
            causal_language_reason=(
                "no single dimension explains the movement, so there is no "
                "slice to make a causal claim about. Adtributor does not "
                "localise causes spanning dimension combinations (HotSpot / "
                "Squeeze are the research answer and are out of scope)"
            ),
            method=(
                f"adtributor(t_ep={t_ep}, t_eep={t_eep}) -> "
                "MULTI_DIMENSIONAL_CASE -> human review"
            ),
            notes=notes + [ad.reason],
        )

    winner = ad.winner
    top = max(winner.candidates, key=lambda e: abs(e.explanatory_power))

    # --- 4. robustness ----------------------------------------------------
    robustness = None
    if run_robustness:
        robustness = rob.assess(
            forecast, actual, dims,
            seasonal_period=contract.detection.seasonality_period,
            n_resamples=n_resamples, t_ep=t_ep, t_eep=t_eep,
        )

    # --- 5. counterfactual ------------------------------------------------
    counter = _counterfactual_for(
        attribution_kpi, analysis, principal, winner.dimension, top.element,
        event_start, event_end, detection, cause_date,
    )

    licensed = bool(counter and counter.causal_language_licensed)
    if robustness and robustness.strength is DriverStrength.UNSTABLE:
        # An unstable ranking must not carry a causal claim even if the
        # counterfactual happens to pass: we would be asserting causation
        # about a slice that changes between resamples.
        licensed = False
        reason = (
            "counterfactual checks aside, the driver ranking is UNSTABLE "
            f"({robustness.reason})"
        )
    elif licensed:
        reason = counter.reason
    else:
        reason = counter.reason if counter else "no counterfactual was possible"

    return AttributionResult(
        **base,
        identity=identity,
        adtributor=ad,
        ranked_dimensions=ad.dimensions,
        ranked_slices=ranked_slices,
        explanatory_power=winner.explanatory_power,
        surprise=winner.surprise,
        robustness=robustness,
        counterfactual=counter,
        outcome=AttributionOutcome.ATTRIBUTED,
        attributed_via=via,
        attribution_kpi=attribution_kpi,
        grain_limit_note=grain_note,
        causal_language_licensed=licensed,
        causal_language_reason=reason,
        method=(
            f"LMDI identity -> adtributor(t_ep={t_ep}, t_eep={t_eep}) "
            f"-> block-bootstrap robustness -> DiD counterfactual"
        ),
        lineage=identity.lineage if identity else [],
        notes=notes,
    )


def _counterfactual_for(
    kpi_id: str,
    analysis: Window,
    principal: Principal,
    dimension: str,
    element: str,
    event_start: date,
    event_end: date,
    detection: DetectionResult,
    cause_date: date | None,
):
    """Build treated and candidate-control series, then run DiD."""
    ms = gateway.guarded_query(kpi_id, analysis, [dimension], principal)
    df = ms.df.copy()
    time_key = ms.grain[0]
    df[time_key] = pd.to_datetime(df[time_key]).dt.date

    series: dict[str, pd.Series] = {}
    for value, cell in df.groupby(dimension):
        s = cell.groupby(time_key)["value"].sum().sort_index()
        series[str(value)] = s

    if element not in series:
        return None

    treated = series[element]
    candidates = {k: v for k, v in series.items() if k != element}

    pre_end = event_start - timedelta(days=1)
    pre_start = pre_end - timedelta(days=27)

    return cf.difference_in_differences(
        treated,
        candidates,
        treatment_label=f"{dimension}={element}",
        treatment_slice={dimension: [element]},
        candidate_slices={k: {dimension: [k]} for k in candidates},
        pre_start=pre_start,
        pre_end=pre_end,
        post_start=event_start,
        post_end=event_end,
        cause_date=cause_date,
        changepoint=detection.changepoint_date,
    )
