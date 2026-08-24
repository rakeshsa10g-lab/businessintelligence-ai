"""Semantic layer: contracts, compilation, lineage, freshness."""

from __future__ import annotations

from datetime import date

import pytest

from semantic import gateway, registry
from semantic.types import ContractError, Window


def test_all_kpis_load_and_validate():
    """The five case KPIs, plus `sessions`.

    `sessions` was added in Stage 4 (ADR-018) so the revenue identity can be
    evaluated on a single analytical population. The architecture's identity
    names Sessions as a factor but Part 7.1 lists only K1-K5, so there was no
    contract for it; mixing the S2 product-analytics session count into the
    identity broke LMDI conservation by ~4.5%.
    """
    ids = registry.all_ids()
    assert ids == [
        "average_order_value",
        "conversion_rate",
        "net_revenue",
        "orders",
        "refund_rate",
        "sessions",
    ]


def test_unknown_kpi_raises(july_window, arjun):
    with pytest.raises(ContractError):
        registry.get("gross_margin_pct")
    with pytest.raises(ContractError):
        gateway.guarded_query("gross_margin_pct", july_window, ["region"], arjun)


def test_ratio_kpis_declare_attribute_via():
    """A non-additive KPI must route attribution to the fundamentals — the
    CMMD / Adtributor s4 rule, enforced by the contract validator."""
    for kpi_id in ("average_order_value", "conversion_rate", "refund_rate"):
        c = registry.get(kpi_id)
        assert c.additive is False
        assert c.attribute_via, f"{kpi_id} must declare attribute_via"


def test_additive_kpis_are_marked_additive():
    for kpi_id in ("net_revenue", "orders"):
        assert registry.get(kpi_id).additive is True


def test_conversion_rate_has_a_narrower_grain_than_net_revenue():
    """The grain mismatch is deliberate: conversion_rate has no
    product_category, so attribution on it cannot descend that far."""
    cr = registry.get("conversion_rate")
    nr = registry.get("net_revenue")
    assert "product_category" not in cr.dimension_names()
    assert "product_category" in nr.dimension_names()
    assert cr.grain_note


def test_requesting_a_dimension_outside_the_contract_grain_fails(arjun, july_window):
    with pytest.raises(ValueError, match="not in this contract's"):
        gateway.guarded_query(
            "conversion_rate", july_window, ["product_category"], arjun
        )


def test_valid_metric_query_returns_data(arjun, july_window):
    s = gateway.guarded_query("net_revenue", july_window, ["region"], arjun)
    assert s.rows > 0
    assert {"date", "region", "value"} <= set(s.df.columns)
    assert s.unit == "INR"
    assert s.df["value"].sum() > 0


def test_lineage_is_attached_to_returned_data(arjun, july_window):
    s = gateway.guarded_query("net_revenue", july_window, ["region"], arjun)
    ln = s.lineage
    assert ln.metric_id == "net_revenue"
    assert ln.contract_version == "1.2.0"
    assert ln.source_id == "S1"
    assert ln.source_table == "fact_orders"
    assert "SELECT" in ln.compiled_sql
    assert ln.row_count == s.rows
    assert ln.grain == ["date", "region"]
    assert any("order_date" in f for f in ln.filters_applied)
    assert ln.freshness_lag_hours >= 0


def test_lineage_records_the_entitlement_predicate(priya, july_window):
    """The row filter must be visible in lineage — governance you can read."""
    s = gateway.guarded_query("net_revenue", july_window, ["region"], priya)
    assert any("region = 'West'" in f for f in s.lineage.filters_applied)


def test_freshness_metadata_is_available(arjun, july_window):
    s = gateway.guarded_query("net_revenue", july_window, ["region"], arjun)
    assert s.freshness.cadence == "daily"
    assert s.freshness.lag_hours >= 0
    assert s.freshness.note


def test_finance_source_is_lagging_by_design(arjun):
    """S3 is stamped T+3. That must show up as a real lag, not a zero."""
    w = Window(start=date(2026, 6, 1), end=date(2026, 8, 31))
    s = gateway.guarded_query("refund_rate", w, ["region"], arjun)
    s1 = gateway.guarded_query("net_revenue", w, ["region"], arjun)
    assert s.freshness.lag_hours > s1.freshness.lag_hours
    assert s.freshness.expected_lag_hours == 72


def test_cross_source_ratio_reconciles_two_systems(arjun):
    """refund_rate takes its numerator from S3 finance and its denominator
    from S1 warehouse — a genuine cross-source join (R2-OBJ-2)."""
    w = Window(start=date(2026, 6, 1), end=date(2026, 8, 31))
    s = gateway.guarded_query("refund_rate", w, ["region"], arjun)
    assert s.rows > 0
    assert {"numerator", "denominator", "value"} <= set(s.df.columns)
    assert "JOIN" in s.lineage.compiled_sql.upper()
    finite = s.df["value"].dropna()
    assert (finite >= 0).all() and (finite < 1).all()


def test_same_source_ratio_exposes_numerator_and_denominator(arjun, july_window):
    s = gateway.guarded_query("conversion_rate", july_window, ["region"], arjun)
    assert {"numerator", "denominator", "value"} <= set(s.df.columns)
    row = s.df.dropna(subset=["value"]).iloc[0]
    assert abs(row["value"] - row["numerator"] / row["denominator"]) < 1e-9


def test_window_validation_rejects_reversed_dates():
    with pytest.raises(ValueError, match="precedes start"):
        Window(start=date(2026, 8, 1), end=date(2026, 7, 1))


def test_materiality_rule_is_inspectable():
    """'Why did you alert me?' must have a literal answer."""
    m = registry.get("net_revenue").materiality
    assert m.min_abs_effect == 250000.0
    # 9.0, not the 2.0 this contract shipped with in Stage 2. The original
    # value was authored by intuition and turned out to sit below the *median*
    # of the noise floor measured over an event-free period, so the gate
    # admitted nearly every slice it saw. See eval/detection_report.md.
    assert m.min_rel_effect_pct == 9.0
    assert m.min_duration_days == 3
    assert "abs_effect" in m.rule
