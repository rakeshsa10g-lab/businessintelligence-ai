"""Entitlement enforcement (R2-MPE-7, R2-CX-8, Architecture Part 21).

The property under test is not "the UI hides it" but "the system did not use
it". These assertions are about what reaches downstream analysis.
"""

from __future__ import annotations

import pytest

from security import entitlements
from security.entitlements import Principal
from semantic import gateway, registry
from semantic.types import EntitlementError


# --- decision-level -------------------------------------------------------
def test_ops_lead_gets_a_region_row_filter(priya):
    access = entitlements.decide(priya, registry.get("net_revenue"))
    assert access.allowed
    assert access.row_filter_sql == "region = 'West'"
    assert access.decision_label == "PARTIAL"


def test_finance_director_has_no_row_filter(arjun):
    access = entitlements.decide(arjun, registry.get("net_revenue"))
    assert access.allowed
    assert access.row_filter_sql is None


def test_margin_is_denied_to_ops_lead_and_allowed_to_finance(priya, arjun):
    contract = registry.get("net_revenue")
    assert "margin" in entitlements.decide(priya, contract).denied_columns
    assert "margin" not in entitlements.decide(arjun, contract).denied_columns


def test_ops_lead_is_denied_the_finance_source(priya):
    """refund_rate lives on S3, which ops_lead may not read at all."""
    access = entitlements.decide(priya, registry.get("refund_rate"))
    assert not access.allowed
    assert "S3" in access.reason


def test_unknown_role_is_denied(arjun):
    stranger = Principal(user_id="x", display_name="X", role="intern")
    access = entitlements.decide(stranger, registry.get("net_revenue"))
    assert not access.allowed
    assert "unknown role" in access.reason


def test_region_scoped_role_without_a_region_is_denied():
    broken = Principal(user_id="p2", display_name="No Region", role="ops_lead")
    access = entitlements.decide(broken, registry.get("net_revenue"))
    assert not access.allowed
    assert "user_region" in access.reason


def test_source_permitted_helper(priya, meera):
    a_priya = entitlements.decide(priya, registry.get("net_revenue"))
    assert a_priya.source_permitted("support_tickets")
    assert not a_priya.source_permitted("crm_notes")

    a_meera = entitlements.decide(meera, registry.get("net_revenue"))
    assert a_meera.source_permitted("crm_notes")  # wildcard


# --- end-to-end through the gateway ---------------------------------------
def test_unauthorised_rows_never_reach_downstream_analysis(priya, july_window):
    """Priya's result set must contain West and nothing else."""
    series = gateway.guarded_query("net_revenue", july_window, ["region"], priya)
    assert set(series.df["region"].unique()) == {"West"}
    assert series.row_filters_applied == ["region = 'West'"]


def test_finance_sees_every_region(arjun, july_window):
    series = gateway.guarded_query("net_revenue", july_window, ["region"], arjun)
    assert set(series.df["region"].unique()) == {"North", "South", "East", "West"}


def test_restricted_columns_are_removed_before_analysis(priya, arjun, july_window):
    """margin must not be in the dataframe at all for ops_lead — not blanked,
    not null, absent. It never enters the result set."""
    p = gateway.guarded_query(
        "net_revenue", july_window, ["region"], priya, include_columns=["margin"]
    )
    assert "margin" not in p.df.columns
    assert p.columns_masked == ["margin"]
    assert "margin" not in p.lineage.compiled_sql

    a = gateway.guarded_query(
        "net_revenue", july_window, ["region"], arjun, include_columns=["margin"]
    )
    assert "margin" in a.df.columns
    assert a.columns_masked == []


def test_source_allowlist_is_enforced_end_to_end(priya, july_window):
    with pytest.raises(EntitlementError) as exc:
        gateway.guarded_query("refund_rate", july_window, ["region"], priya)
    assert "S3" in str(exc.value)


def test_denial_is_audited(priya, july_window):
    before = len(gateway.audit_trail())
    with pytest.raises(EntitlementError):
        gateway.guarded_query("refund_rate", july_window, ["region"], priya)
    after = gateway.audit_trail()
    assert len(after) == before + 1
    last = after.iloc[-1]
    assert last["decision"] == "DENIED"
    assert last["actor"] == "priya"


def test_successful_read_is_audited_with_masked_columns(priya, july_window):
    gateway.guarded_query(
        "net_revenue", july_window, ["region"], priya, include_columns=["margin"]
    )
    last = gateway.audit_trail().iloc[-1]
    assert last["decision"] == "PARTIAL"
    assert last["columns_masked"] == "margin"
    assert last["rows_returned"] > 0
