"""Dataset constants and the injected-event catalogue.

Kept separate from generate.py so tests and the scenario summary can import the
ground-truth definitions without triggering a regeneration.

Architecture reference: Part 7.1-7.6.
"""

from __future__ import annotations

from datetime import date, datetime

SEED = 20260821

# --- calendar -------------------------------------------------------------
START = date(2025, 3, 1)
END = date(2026, 8, 17)  # 535 days ~ 18 months

# The demo runs against a fixed notional clock rather than wall time, so
# freshness lags are deterministic and reproducible on any day. Without this a
# stored watermark drifts into "stale" simply because time passed, which would
# make the freshness panel meaningless in a recorded demo. See ADR-014.
DEMO_NOW = datetime(2026, 8, 17, 12, 0)

# --- dimensions (Part 7.2) ------------------------------------------------
REGIONS = ["North", "South", "East", "West"]
SEGMENTS = ["Enterprise", "SMB", "Consumer"]
PRODUCT_CATEGORIES = ["Apparel", "Electronics", "Home", "Beauty", "NewLaunch"]
CHANNELS = ["Web", "Mobile App", "Marketplace", "Retail Partner"]
FUNNEL_STEPS = ["view_cart", "checkout_start", "payment_attempt", "order_placed"]

# NewLaunch does not exist before this date -> sparse-history scenario (E4).
NEW_LAUNCH_START = date(2026, 6, 27)

# --- the deliberate schema change (E5) ------------------------------------
# 'marketplace' is renamed 'Marketplace' on this date, splitting the series.
SCHEMA_CHANGE_DATE = date(2026, 6, 14)
SCHEMA_CHANGE_OLD_VALUE = "marketplace"
SCHEMA_CHANGE_NEW_VALUE = "Marketplace"

# --- baseline economics ---------------------------------------------------
BASE_AOV_INR = {
    "Apparel": 2200.0,
    "Electronics": 8500.0,
    "Home": 3400.0,
    "Beauty": 1450.0,
    "NewLaunch": 3900.0,
}

REGION_WEIGHT = {"North": 0.30, "South": 0.28, "East": 0.17, "West": 0.25}
SEGMENT_WEIGHT = {"Enterprise": 0.22, "SMB": 0.33, "Consumer": 0.45}
CATEGORY_WEIGHT = {
    "Apparel": 0.30,
    "Electronics": 0.24,
    "Home": 0.21,
    "Beauty": 0.20,
    "NewLaunch": 0.05,
}
CHANNEL_WEIGHT = {
    "Web": 0.34,
    "Mobile App": 0.38,
    "Marketplace": 0.19,
    "Retail Partner": 0.09,
}

# 281 orders/day x weighted AOV Rs 3,899 x 365 = ~Rs 40 Cr/yr, the mid-market
# D2C scale the architecture specifies (Part 7).
BASE_DAILY_ORDERS = 281.0
BASE_CONVERSION = 0.0295            # 2.95% checkout conversion
BASE_REFUND_RATE = 0.052
BASE_DISCOUNT_RATE = 0.083
NOISE_CV = 0.10                     # target baseline CV ~8-12% (Part 23 Stage 1)

# --- injected ground-truth events (Part 7.5) ------------------------------
# Each event carries the true driver so detection precision/recall and
# attribution Top-1/Top-2 accuracy can be measured, not asserted.
EVENTS: list[dict] = [
    {
        "event_id": "E1",
        "name": "Payment gateway degradation",
        "start": date(2026, 7, 12),
        "end": date(2026, 7, 26),
        "slice": {"region": ["West"], "channel": ["Web", "Mobile App"]},
        "true_driver": "conversion_rate",
        "true_dimension": "region",
        "true_slice_label": "West",
        "mechanism": "payment_gateway_degradation",
        "effect": {"conversion_multiplier": 0.72},
        "scenario": "S1_high_confidence_multifactor",
        "evidence": {"support_tickets": 34, "deploy_changelog": 1},
        "decoys": {"market_events": 1},
        "detectable": True,
    },
    {
        "event_id": "E2",
        "name": "Ambiguous: competitor promo vs stockout",
        "start": date(2026, 6, 2),
        "end": date(2026, 6, 16),
        "slice": {"region": ["South"], "product_category": ["Apparel"]},
        "true_driver": "orders",
        "true_dimension": "product_category",
        "true_slice_label": "Apparel",
        "mechanism": "ambiguous_competitor_promo_or_stockout",
        "effect": {"orders_multiplier": 0.78},
        "scenario": "S2_conflicting_evidence",
        "evidence": {"market_events": 6, "crm_notes": 11},
        "decoys": {},
        "detectable": True,
        "note": "Evidence deliberately balanced so no single hypothesis dominates.",
    },
    {
        "event_id": "E3",
        "name": "Unexplained softness, thin evidence",
        "start": date(2026, 8, 5),
        "end": date(2026, 8, 15),
        "slice": {"region": ["East"], "segment": ["SMB"]},
        "true_driver": "orders",
        "true_dimension": "region",
        "true_slice_label": "East",
        "mechanism": "unknown",
        "effect": {"orders_multiplier": 0.84},
        "scenario": "S3_low_confidence_abstention",
        "evidence": {"support_tickets": 2},
        "decoys": {},
        "detectable": True,
        "note": "Only two vague tickets exist -> engine should abstain, not guess.",
    },
    {
        "event_id": "E4",
        "name": "NewLaunch category, sparse history",
        "start": date(2026, 7, 20),
        "end": date(2026, 7, 31),
        "slice": {"product_category": ["NewLaunch"]},
        "true_driver": "orders",
        "true_dimension": "product_category",
        "true_slice_label": "NewLaunch",
        "mechanism": "new_product_ramp",
        "effect": {"orders_multiplier": 1.55},
        "scenario": "S4_sparse_history",
        "evidence": {"crm_notes": 4},
        "decoys": {},
        "detectable": False,
        "note": (
            "23 days of history at event start (launched 2026-06-27) is below "
            "min_history_days=56 -> sparse path, not the standard detector."
        ),
    },
    {
        "event_id": "E5",
        "name": "Schema change masquerading as a business event",
        "start": SCHEMA_CHANGE_DATE,
        "end": date(2026, 6, 28),
        "slice": {"channel": ["Marketplace"]},
        "true_driver": "schema_change",
        "true_dimension": "channel",
        "true_slice_label": "Marketplace",
        "mechanism": "channel_value_renamed",
        "effect": {"series_split": True},
        "scenario": "S7_schema_change",
        "evidence": {"schema_change_log": 1},
        "decoys": {"support_tickets": 12},
        "detectable": True,
        "note": "No real business movement. Correct answer is 'this is a data artifact'.",
    },
    {
        "event_id": "E6",
        "name": "One event, two personas",
        "start": date(2026, 7, 12),
        "end": date(2026, 7, 26),
        "slice": {"region": ["West"], "channel": ["Web", "Mobile App"]},
        "true_driver": "conversion_rate",
        "true_dimension": "region",
        "true_slice_label": "West",
        "mechanism": "payment_gateway_degradation",
        "effect": {"shares_movement_with": "E1"},
        "scenario": "S5_two_personas_and_S6_entitlement",
        "evidence": {"crm_notes": 5},
        "decoys": {},
        "detectable": True,
        "note": (
            "Same underlying movement as E1. The CRM notes here are visible to "
            "finance_director but denied to ops_lead, so the two personas "
            "genuinely see different evidence."
        ),
    },
]

EVENTS_BY_ID = {e["event_id"]: e for e in EVENTS}

# --- expected row counts, asserted by tests -------------------------------
EXPECTED_COUNTS = {
    "support_tickets": (850, 1000),
    "crm_notes": (300, 420),
    "market_events": (100, 150),
    "deploy_changelog": (160, 210),
    "schema_change_log": (20, 30),
    "finance_adjustments": (60, 100),
}
