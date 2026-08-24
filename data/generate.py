"""Deterministic synthetic dataset for the Round 2 prototype.

Run:  python -m data.generate

Produces `data/warehouse.duckdb` plus `ground_truth.json` and
`scenario_manifest.json`. Two runs from the same seed produce identical data
(content-identical; see ADR-013 on why not byte-identical).

Design notes
------------
The five KPIs are connected by one identity (Part 7.1):

    Net Revenue = Sessions x Conversion Rate x AOV x (1 - Refund Rate)

so the generator builds sessions and conversion first, derives orders from
them, then applies AOV and refunds. That ordering is what makes LMDI
decomposition meaningful later — the factors genuinely multiply out.

Three sources with deliberately different characteristics (Part 7.3):
  S1 warehouse         daily, full dimensionality
  S2 product_analytics hourly, no product dimension, 3.5% null region
  S3 ops_context       documents + weekly finance, T+3 lag

THIS IS THE ONLY MODULE OUTSIDE semantic/gateway.py PERMITTED TO OPEN DuckDB.
It is a build-time tool, not a runtime query path, and nothing in the runtime
packages imports it. `tests/test_chokepoint.py` enforces both halves of that.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from data import spec

HERE = Path(__file__).parent
DB_PATH = HERE / "warehouse.duckdb"
GROUND_TRUTH_PATH = HERE / "ground_truth.json"
MANIFEST_PATH = HERE / "scenario_manifest.json"
SUMMARY_PATH = HERE / "SCENARIOS.md"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _weekday_factor(d: date) -> float:
    """Retail weekly shape. Weekend lift, Monday dip."""
    return {0: 0.92, 1: 0.97, 2: 1.00, 3: 1.03, 4: 1.12, 5: 1.18, 6: 1.05}[d.weekday()]


def _annual_seasonality(d: date) -> float:
    doy = d.timetuple().tm_yday
    festive = 1.0
    if d.month == 10 or (d.month == 11 and d.day <= 15):  # festive season
        festive = 1.22
    return festive * (1.0 + 0.06 * np.sin(2 * np.pi * (doy - 80) / 365.0))


def _trend(d: date) -> float:
    """Gentle organic growth across the 18 months."""
    return 1.0 + 0.00035 * (d - spec.START).days


def _in_slice(row_region, row_segment, row_cat, row_channel, slc: dict) -> bool:
    for key, values in slc.items():
        actual = {
            "region": row_region,
            "segment": row_segment,
            "product_category": row_cat,
            "channel": row_channel,
        }[key]
        if actual not in values:
            return False
    return True


# --------------------------------------------------------------------------
# S1 — warehouse: fact_orders (daily x full dimensionality)
# --------------------------------------------------------------------------
def build_fact_orders(rng: np.random.Generator) -> pd.DataFrame:
    days = _date_range(spec.START, spec.END)

    cells = [
        (r, s, c, ch)
        for r in spec.REGIONS
        for s in spec.SEGMENTS
        for c in spec.PRODUCT_CATEGORIES
        for ch in spec.CHANNELS
    ]

    records = []
    for d in days:
        day_factor = _weekday_factor(d) * _annual_seasonality(d) * _trend(d)
        for (region, segment, cat, channel) in cells:
            # NewLaunch simply does not exist before its launch date.
            if cat == "NewLaunch" and d < spec.NEW_LAUNCH_START:
                continue

            share = (
                spec.REGION_WEIGHT[region]
                * spec.SEGMENT_WEIGHT[segment]
                * spec.CATEGORY_WEIGHT[cat]
                * spec.CHANNEL_WEIGHT[channel]
            )
            base_sessions = spec.BASE_DAILY_ORDERS / spec.BASE_CONVERSION * share * day_factor
            conversion = spec.BASE_CONVERSION
            aov = spec.BASE_AOV_INR[cat]
            refund_rate = spec.BASE_REFUND_RATE
            orders_mult = 1.0

            # --- apply injected events -----------------------------------
            active_events: list[str] = []
            for ev in spec.EVENTS:
                if ev["event_id"] == "E6":
                    continue  # E6 shares E1's movement; evidence differs, not data
                if not (ev["start"] <= d <= ev["end"]):
                    continue
                if not _in_slice(region, segment, cat, channel, ev["slice"]):
                    continue
                eff = ev["effect"]
                if "conversion_multiplier" in eff:
                    conversion *= eff["conversion_multiplier"]
                if "orders_multiplier" in eff:
                    orders_mult *= eff["orders_multiplier"]
                active_events.append(ev["event_id"])

            # NewLaunch ramps from a low base regardless of E4
            if cat == "NewLaunch":
                age = (d - spec.NEW_LAUNCH_START).days
                base_sessions *= min(1.0, 0.25 + 0.03 * age)

            noise = rng.normal(1.0, spec.NOISE_CV)
            noise = float(np.clip(noise, 0.55, 1.45))

            sessions = base_sessions * noise
            orders = sessions * conversion * orders_mult
            orders = max(0.0, orders)

            aov_actual = aov * float(np.clip(rng.normal(1.0, 0.035), 0.85, 1.15))
            gross = orders * aov_actual
            discount = gross * spec.BASE_DISCOUNT_RATE * float(
                np.clip(rng.normal(1.0, 0.10), 0.6, 1.4)
            )
            refund_actual = refund_rate * float(np.clip(rng.normal(1.0, 0.12), 0.5, 1.6))
            returns = gross * refund_actual

            # The schema change (E5): the stored channel value changes spelling.
            stored_channel = channel
            if channel == "Marketplace" and d < spec.SCHEMA_CHANGE_DATE:
                stored_channel = spec.SCHEMA_CHANGE_OLD_VALUE

            records.append(
                {
                    "order_date": d,
                    "region": region,
                    "segment": segment,
                    "product_category": cat,
                    "channel": stored_channel,
                    # Stored as a float, not rounded to an integer count.
                    # At this scale a cell averages ~1.2 orders/day, so
                    # rounding would destroy the Net Revenue = Sessions x
                    # Conversion x AOV x (1 - Refund) identity that LMDI
                    # decomposition depends on in Stage 4. Detection always
                    # runs on aggregated series, never a raw cell.
                    "orders": float(orders),
                    "sessions": float(sessions),
                    "gross_amount": float(gross),
                    "discount_amount": float(discount),
                    "return_amount": float(returns),
                    # restricted / sensitive columns (Part 21.2)
                    "margin": float(gross * 0.31 * float(np.clip(rng.normal(1.0, 0.05), 0.7, 1.3))),
                    "refund_reason_detail": "quality_complaint" if refund_actual > 0.075 else "size_exchange",
                    "customer_email": f"cust_{region[:2].lower()}{rng.integers(10000, 99999)}@example.com",
                    "order_status": "delivered",
                    "is_test_account": False,
                    "_injected_events": ",".join(active_events),
                }
            )

    return pd.DataFrame.from_records(records)


# --------------------------------------------------------------------------
# S2 — product analytics: hourly sessions + funnel, no product dimension
# --------------------------------------------------------------------------
def build_product_analytics(
    rng: np.random.Generator, orders: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hourly sessions and funnel steps at region x channel.

    Deliberately has NO product_category — this is the grain mismatch that
    forces attribution on conversion_rate to stop at region x channel (Part 7.1).
    """
    daily = (
        orders.assign(
            channel_canonical=lambda df: df["channel"].replace(
                {spec.SCHEMA_CHANGE_OLD_VALUE: spec.SCHEMA_CHANGE_NEW_VALUE}
            )
        )
        .groupby(["order_date", "region", "channel_canonical"], as_index=False)
        .agg(sessions=("sessions", "sum"), orders=("orders", "sum"))
    )

    hour_shape = np.array(
        [0.2, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 0.9, 1.3, 1.5, 1.6, 1.6,
         1.5, 1.4, 1.3, 1.3, 1.4, 1.6, 1.9, 2.1, 2.0, 1.6, 1.0, 0.5]
    )
    hour_shape = hour_shape / hour_shape.sum()

    sess_rows = []
    funnel_rows = []
    for row in daily.itertuples(index=False):
        day_sessions = row.sessions
        day_orders = row.orders
        hourly_sessions = day_sessions * hour_shape
        hourly_sessions = hourly_sessions * rng.normal(1.0, 0.06, size=24).clip(0.7, 1.3)
        conv = (day_orders / day_sessions) if day_sessions > 0 else 0.0

        for h in range(24):
            s = float(hourly_sessions[h])
            # 3.5% of hourly rows have unknown geo (VPN) -> deliberate null region
            region_val = row.region
            if rng.random() < 0.035:
                region_val = None

            ts = datetime.combine(row.order_date, time(hour=h))
            sess_rows.append(
                {
                    "session_hour": ts,
                    "region": region_val,
                    "channel": row.channel_canonical,
                    "sessions": s,
                    "orders": s * conv,
                }
            )

            # funnel: monotone decreasing counts down to order_placed
            v_cart = s * 0.42 * float(np.clip(rng.normal(1.0, 0.05), 0.8, 1.2))
            v_checkout = v_cart * 0.55 * float(np.clip(rng.normal(1.0, 0.05), 0.8, 1.2))
            v_payment = v_checkout * 0.78 * float(np.clip(rng.normal(1.0, 0.05), 0.8, 1.2))
            v_placed = s * conv
            for step, val in zip(
                spec.FUNNEL_STEPS, [v_cart, v_checkout, v_payment, v_placed]
            ):
                funnel_rows.append(
                    {
                        "session_hour": ts,
                        "region": region_val,
                        "channel": row.channel_canonical,
                        "funnel_step": step,
                        "step_count": float(max(0.0, val)),
                    }
                )

    return pd.DataFrame.from_records(sess_rows), pd.DataFrame.from_records(funnel_rows)


# --------------------------------------------------------------------------
# S3 — ops context: documents and weekly finance
# --------------------------------------------------------------------------
TICKET_TEMPLATES = {
    "payment": [
        ("Payment failed at checkout", "Card was declined repeatedly at the payment step. Tried twice, same error."),
        ("Gateway timeout on order", "Payment page hung and then timed out. No confirmation received."),
        ("Card declined but amount debited", "Amount was debited but the order did not go through."),
        ("Cannot complete payment", "Checkout keeps failing when I click pay. Using UPI."),
        ("Transaction error at final step", "Getting an error right at the payment attempt stage."),
    ],
    "delivery": [
        ("Order delayed", "Shipment has not moved for four days."),
        ("Wrong item delivered", "Received a different SKU than ordered."),
        ("Package damaged", "Outer box crushed, item unusable."),
    ],
    "product": [
        ("Item quality below expectation", "Fabric feels thinner than described."),
        ("Sizing inconsistent", "Ordered the usual size, fits differently."),
    ],
    "account": [
        ("Cannot log in", "Password reset email never arrives."),
        ("Address not saving", "New address disappears after save."),
    ],
    "vague": [
        ("Issue with recent order", "Something went wrong, not sure what."),
        ("General complaint", "Experience was not good this time."),
    ],
}

CRM_TEMPLATES = {
    "competitor": "Buyer flagged a competitor running an aggressive promotion in this category this fortnight.",
    "stockout": "Account reported repeated out-of-stock messages on core SKUs during the period.",
    "gateway": "Client escalated repeated payment failures affecting their regional buyers.",
    "launch": "Early feedback on the new category is positive but availability is limited.",
    "routine": "Routine quarterly check-in. No issues raised.",
}

MARKET_TEMPLATES = [
    ("Rival launches festive discounting early", "A regional competitor began discounting ahead of the usual festive window."),
    ("Category price war reported", "Trade press notes sustained discounting across the apparel category."),
    ("Logistics strike affects deliveries", "Regional transport disruption reported for several days."),
    ("New entrant expands to region", "A direct-to-consumer entrant announced regional expansion."),
    ("Consumer sentiment index dips", "Monthly sentiment reading fell in the region."),
]


def build_ops_context(rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    days = _date_range(spec.START, spec.END)

    # ---------------- support tickets ----------------
    tickets = []
    tid = 0

    def add_ticket(d: date, region, segment, channel, category, planted_for=None, is_decoy=False):
        nonlocal tid
        tid += 1
        subject, body = TICKET_TEMPLATES[category][rng.integers(len(TICKET_TEMPLATES[category]))]
        created = datetime.combine(d, time(hour=int(rng.integers(6, 23))))
        tickets.append(
            {
                "ticket_id": f"T{tid:05d}",
                "created_at": created,
                "account_id": f"A{rng.integers(1000, 9999)}",
                "region": region,
                "segment": segment,
                "channel": channel,
                "category": category,
                "subject": subject,
                "body": body,
                "severity": str(rng.choice(["low", "medium", "high"], p=[0.5, 0.35, 0.15])),
                "resolved_at": created + timedelta(hours=float(rng.integers(2, 96))),
                "planted_for": planted_for,
                "is_decoy": is_decoy,
            }
        )

    # background volume, with a Monday spike (the deliberate quirk in Part 7.3)
    for d in days:
        lam = 1.48 * (1.45 if d.weekday() == 0 else 1.0)
        for _ in range(int(rng.poisson(lam))):
            add_ticket(
                d,
                str(rng.choice(spec.REGIONS)),
                str(rng.choice(spec.SEGMENTS)),
                str(rng.choice(spec.CHANNELS)),
                str(rng.choice(["delivery", "product", "account", "payment"], p=[0.35, 0.3, 0.25, 0.10])),
            )

    # E1 planted evidence: 34 payment tickets in West on Web/Mobile App
    e1 = spec.EVENTS_BY_ID["E1"]
    e1_days = _date_range(e1["start"], e1["end"])
    for i in range(e1["evidence"]["support_tickets"]):
        add_ticket(
            e1_days[i % len(e1_days)],
            "West",
            str(rng.choice(spec.SEGMENTS)),
            str(rng.choice(["Web", "Mobile App"])),
            "payment",
            planted_for="E1",
        )

    # E3 planted evidence: exactly 2 vague tickets -> not enough to conclude
    e3 = spec.EVENTS_BY_ID["E3"]
    e3_days = _date_range(e3["start"], e3["end"])
    for i in range(e3["evidence"]["support_tickets"]):
        add_ticket(e3_days[i * 3 % len(e3_days)], "East", "SMB",
                   str(rng.choice(spec.CHANNELS)), "vague", planted_for="E3")

    # E5 decoys: 12 coincidental tickets around the schema change
    e5 = spec.EVENTS_BY_ID["E5"]
    e5_days = _date_range(e5["start"], e5["end"])
    for i in range(e5["decoys"]["support_tickets"]):
        add_ticket(e5_days[i % len(e5_days)], str(rng.choice(spec.REGIONS)),
                   str(rng.choice(spec.SEGMENTS)), "Marketplace",
                   str(rng.choice(["delivery", "account"])), planted_for="E5", is_decoy=True)

    tickets_df = pd.DataFrame.from_records(tickets)

    # ---------------- CRM notes (restricted source) ----------------
    notes = []
    nid = 0

    def add_note(d: date, region, segment, kind, planted_for=None):
        nonlocal nid
        nid += 1
        notes.append(
            {
                "note_id": f"C{nid:05d}",
                "note_date": d,
                "account_id": f"A{rng.integers(1000, 9999)}",
                "region": region,
                "segment": segment,
                "author_role": str(rng.choice(["AE", "CSM", "RSM"])),
                "body": CRM_TEMPLATES[kind],
                "kind": kind,
                "planted_for": planted_for,
            }
        )

    for d in days:
        if rng.random() < 0.58:
            add_note(d, str(rng.choice(spec.REGIONS)), str(rng.choice(spec.SEGMENTS)), "routine")

    e2 = spec.EVENTS_BY_ID["E2"]
    e2_days = _date_range(e2["start"], e2["end"])
    # deliberately balanced: roughly half competitor, half stockout
    for i in range(e2["evidence"]["crm_notes"]):
        add_note(e2_days[i % len(e2_days)], "South", str(rng.choice(spec.SEGMENTS)),
                 "competitor" if i % 2 == 0 else "stockout", planted_for="E2")

    e4 = spec.EVENTS_BY_ID["E4"]
    e4_days = _date_range(e4["start"], e4["end"])
    for i in range(e4["evidence"]["crm_notes"]):
        add_note(e4_days[i % len(e4_days)], str(rng.choice(spec.REGIONS)),
                 str(rng.choice(spec.SEGMENTS)), "launch", planted_for="E4")

    # E6: CRM notes only finance may see -> the entitlement demonstration
    e6 = spec.EVENTS_BY_ID["E6"]
    e6_days = _date_range(e6["start"], e6["end"])
    for i in range(e6["evidence"]["crm_notes"]):
        add_note(e6_days[i % len(e6_days)], "West", str(rng.choice(spec.SEGMENTS)),
                 "gateway", planted_for="E6")

    notes_df = pd.DataFrame.from_records(notes)

    # ---------------- market events ----------------
    market = []
    mid = 0

    def add_market(d: date, region, category, idx, planted_for=None, is_decoy=False):
        nonlocal mid
        mid += 1
        headline, body = MARKET_TEMPLATES[idx % len(MARKET_TEMPLATES)]
        market.append(
            {
                "event_id_doc": f"M{mid:05d}",
                "event_date": d,
                "region": region,
                "category": category,
                "headline": headline,
                "body": body,
                "source_name": str(rng.choice(["TradePress", "RegionalDaily", "IndustryWire"])),
                "planted_for": planted_for,
                "is_decoy": is_decoy,
            }
        )

    for i, d in enumerate(days[::5]):
        if rng.random() < 0.95:
            add_market(d, str(rng.choice(spec.REGIONS)),
                       str(rng.choice(spec.PRODUCT_CATEGORIES[:4])), int(rng.integers(0, 5)))

    for i in range(e2["evidence"]["market_events"]):
        add_market(e2_days[i % len(e2_days)], "South", "Apparel", i % 2, planted_for="E2")

    for i in range(e1["decoys"]["market_events"]):
        add_market(e1_days[len(e1_days) // 2], "West", "Electronics", 4,
                   planted_for="E1", is_decoy=True)

    market_df = pd.DataFrame.from_records(market)

    # ---------------- deploy changelog ----------------
    deploys = []
    did = 0
    services = ["checkout", "catalog", "search", "payments", "shipping", "auth"]
    for d in days[::3]:
        if rng.random() < 0.98:
            did += 1
            deploys.append(
                {
                    "deploy_id": f"D{did:05d}",
                    "deployed_at": datetime.combine(d, time(hour=int(rng.integers(1, 6)))),
                    "service": str(rng.choice(services)),
                    "component": str(rng.choice(["api", "worker", "ui", "config"])),
                    "summary": "Routine release",
                    "risk_level": str(rng.choice(["low", "medium", "high"], p=[0.7, 0.25, 0.05])),
                    "rollback_at": None,
                    "planted_for": None,
                }
            )
    # E1's real cause: a payments config change on the event start date
    did += 1
    deploys.append(
        {
            "deploy_id": f"D{did:05d}",
            "deployed_at": datetime.combine(e1["start"], time(hour=2)),
            "service": "payments",
            "component": "gateway-config",
            "summary": "Switch primary payment gateway routing to new provider",
            "risk_level": "high",
            "rollback_at": datetime.combine(e1["end"], time(hour=4)),
            "planted_for": "E1",
        }
    )
    deploys_df = pd.DataFrame.from_records(deploys)

    # ---------------- schema change log ----------------
    schema_rows = []
    sid = 0
    for d in days[::24]:
        sid += 1
        schema_rows.append(
            {
                "change_id": f"S{sid:05d}",
                "changed_at": datetime.combine(d, time(hour=3)),
                "table_name": str(rng.choice(["fact_orders", "dim_product", "fact_sessions"])),
                "column_name": str(rng.choice(["notes", "tags", "attr_json"])),
                "change_type": "add_column",
                "actor": "data-platform",
                "note": "Additive change, no downstream impact expected.",
                "planted_for": None,
            }
        )
    sid += 1
    schema_rows.append(
        {
            "change_id": f"S{sid:05d}",
            "changed_at": datetime.combine(spec.SCHEMA_CHANGE_DATE, time(hour=3)),
            "table_name": "fact_orders",
            "column_name": "channel",
            "change_type": "value_rename",
            "actor": "sales-ops",
            "note": (
                "Renamed channel value 'marketplace' to 'Marketplace' for "
                "consistency with the partner portal. No backfill applied."
            ),
            "planted_for": "E5",
        }
    )
    schema_df = pd.DataFrame.from_records(schema_rows)

    # ---------------- finance adjustments (weekly, T+3) ----------------
    fin = []
    week_starts = [d for d in days if d.weekday() == 0]
    for wk in week_starts[-20:]:
        for region in spec.REGIONS:
            cat = str(rng.choice(spec.PRODUCT_CATEGORIES[:4]))
            fin.append(
                {
                    "week_start": wk,
                    "region": region,
                    "product_category": cat,
                    "refund_amount": float(abs(rng.normal(180000, 55000))),
                    "reason_code": str(rng.choice(["QUALITY", "SIZE", "LATE", "DAMAGE"])),
                }
            )
    fin_df = pd.DataFrame.from_records(fin)

    return {
        "support_tickets": tickets_df,
        "crm_notes": notes_df,
        "market_events": market_df,
        "deploy_changelog": deploys_df,
        "schema_change_log": schema_df,
        "finance_adjustments": fin_df,
    }


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------
def _watermarks() -> pd.DataFrame:
    """Source watermarks drive freshness, measured against spec.DEMO_NOW.

    S1 is a daily T-1 batch, S2 refreshes hourly, and S3 finance is
    deliberately T+3 — so the most recent week genuinely does not exist yet.
    """
    end = spec.END
    return pd.DataFrame(
        [
            {"source_id": "S1", "source_name": "warehouse",
             "as_of": datetime.combine(end - timedelta(days=1), time(6, 0)),
             "cadence": "daily"},
            {"source_id": "S2", "source_name": "product_analytics",
             "as_of": spec.DEMO_NOW - timedelta(hours=2),
             "cadence": "hourly"},
            {"source_id": "S3", "source_name": "ops_context",
             "as_of": datetime.combine(end - timedelta(days=3), time(6, 0)),
             "cadence": "weekly"},
        ]
    )


def generate(db_path: Path = DB_PATH) -> dict:
    rng = np.random.default_rng(spec.SEED)

    orders = build_fact_orders(rng)
    sessions, funnel = build_product_analytics(rng, orders)
    ops = build_ops_context(rng)
    watermarks = _watermarks()

    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        con.register("_orders", orders)
        con.execute("CREATE TABLE fact_orders AS SELECT * FROM _orders")
        con.register("_sessions", sessions)
        con.execute("CREATE TABLE fact_sessions AS SELECT * FROM _sessions")
        con.register("_funnel", funnel)
        con.execute("CREATE TABLE fact_funnel_steps AS SELECT * FROM _funnel")
        for name, df in ops.items():
            con.register(f"_{name}", df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM _{name}")
        con.register("_wm", watermarks)
        con.execute("CREATE TABLE source_watermarks AS SELECT * FROM _wm")

        # Dimension tables, derived so they can never drift from the facts.
        # ORDER BY is not cosmetic: SELECT DISTINCT alone returns rows in
        # whatever order the parallel hash aggregate produces, which made the
        # generator non-reproducible across runs.
        for dim in ("region", "segment", "product_category", "channel"):
            con.execute(
                f"CREATE TABLE dim_{dim} AS "
                f"SELECT DISTINCT {dim} FROM fact_orders ORDER BY {dim}"
            )

        # append-only audit log (Part 21.4), created here, written by gateway
        con.execute(
            """
            CREATE TABLE audit_log (
                ts TIMESTAMP, run_id VARCHAR, actor VARCHAR, role VARCHAR,
                action VARCHAR, resource VARCHAR, decision VARCHAR,
                policy_applied VARCHAR, rows_returned INTEGER, items_withheld INTEGER,
                columns_masked VARCHAR, detail VARCHAR
            )
            """
        )

        stats = {
            "fact_orders": len(orders),
            "fact_sessions": len(sessions),
            "fact_funnel_steps": len(funnel),
            **{k: len(v) for k, v in ops.items()},
            "source_watermarks": len(watermarks),
        }
    finally:
        con.close()

    _write_ground_truth(orders)
    _write_manifest()
    _write_summary(stats)
    return stats


def _write_ground_truth(orders: pd.DataFrame) -> None:
    """Record every injected event with its measured effect, so detection and
    attribution accuracy can be reported rather than asserted (Part 7.5)."""
    payload = {
        "seed": spec.SEED,
        "generated_for_window": {"start": spec.START.isoformat(), "end": spec.END.isoformat()},
        "events": [],
    }

    for ev in spec.EVENTS:
        rec = {
            "event_id": ev["event_id"],
            "name": ev["name"],
            "start": ev["start"].isoformat(),
            "end": ev["end"].isoformat(),
            "slice": ev["slice"],
            "true_driver": ev["true_driver"],
            "true_dimension": ev["true_dimension"],
            "true_slice_label": ev["true_slice_label"],
            "mechanism": ev["mechanism"],
            "scenario": ev["scenario"],
            "detectable_by_standard_path": ev["detectable"],
            "evidence_planted": ev["evidence"],
            "decoys_planted": ev["decoys"],
            "note": ev.get("note", ""),
        }

        # measured effect on net revenue for the affected slice
        if ev["event_id"] != "E5":
            mask = np.ones(len(orders), dtype=bool)
            for key, values in ev["slice"].items():
                col = orders[key] if key != "channel" else orders["channel"].replace(
                    {spec.SCHEMA_CHANGE_OLD_VALUE: spec.SCHEMA_CHANGE_NEW_VALUE}
                )
                mask &= col.isin(values).to_numpy()

            net = orders["gross_amount"] - orders["discount_amount"] - orders["return_amount"]
            during = mask & orders["order_date"].between(ev["start"], ev["end"]).to_numpy()
            before_start = ev["start"] - timedelta(days=28)
            before = mask & orders["order_date"].between(
                before_start, ev["start"] - timedelta(days=1)
            ).to_numpy()

            during_daily = net[during].sum() / max(1, (ev["end"] - ev["start"]).days + 1)
            before_daily = net[before].sum() / 28.0
            rec["measured"] = {
                "baseline_daily_net_revenue_inr": round(float(before_daily), 2),
                "event_daily_net_revenue_inr": round(float(during_daily), 2),
                "relative_change_pct": round(
                    float((during_daily - before_daily) / before_daily * 100.0), 2
                )
                if before_daily
                else None,
            }
        payload["events"].append(rec)

    GROUND_TRUTH_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_manifest() -> None:
    """The executable scenario definition (ADR-028).

    `persona` is what `eval/run_recommendation_eval.py` actually runs. Where
    that differs from the Round-1 specification, the original is preserved on
    the entry as `original_spec_persona` with the reason, rather than being
    overwritten and forgotten.

    The divergence is deliberate and it is a design fix. The Round-1 assignment
    gave S1 to priya and S2 to arjun, which confounds two variables: a
    difference between those runs could come from the event or from the role,
    and nothing in the output distinguishes them. The harness varies one factor
    at a time - S1..S4 hold the persona fixed and vary the event, S1/S5a/S5b
    hold the event fixed and vary the persona.

    `expected_outcome` states design INTENT. It is not a record of what the
    system decides; that is `eval/recommendation_report.md` (ADR-027).
    """
    scenarios = [
        {
            "scenario_id": "S1",
            "title": "High-confidence multi-factor movement",
            "event_ids": ["E1"],
            "persona": "meera",
            "original_spec_persona": "priya",
            "divergence_reason": (
                "fixed persona across S1..S4 so the event is the only variable; "
                "the persona contrast moved to S1/S5a/S5b on one event"
            ),
            "expected_outcome": "Ranked hypothesis with gateway deploy + payment tickets as corroboration",
            "requirement_ids": ["R2-MPE-4", "R2-MPE-8"],
        },
        {
            "scenario_id": "S2",
            "title": "Conflicting evidence",
            "event_ids": ["E2"],
            "persona": "meera",
            "original_spec_persona": "arjun",
            "divergence_reason": (
                "fixed persona across S1..S4 so the event is the only variable"
            ),
            "expected_outcome": "Two hypotheses within the ambiguity margin, both shown",
            "requirement_ids": ["R2-MPE-4", "R2-CX-6"],
        },
        {
            "scenario_id": "S3",
            "title": "Low confidence / thin evidence",
            "event_ids": ["E3"],
            "persona": "meera",
            "original_spec_persona": "priya",
            "divergence_reason": (
                "fixed persona across S1..S4 so the event is the only variable"
            ),
            "expected_outcome": (
                "System declines to assert a cause and names what would settle it"
            ),
            "requirement_ids": ["R2-MPE-5"],
        },
        {
            "scenario_id": "S4",
            "title": "Sparse history",
            "event_ids": ["E4"],
            "persona": "meera",
            "original_spec_persona": "arjun",
            "divergence_reason": (
                "fixed persona across S1..S4 so the event is the only variable"
            ),
            "expected_outcome": "Sparse path used; standard detector suppressed; levers restricted",
            "requirement_ids": ["R2-MPE-6"],
        },
        {
            "scenario_id": "S5a",
            "title": "Two personas, one event - operations lead",
            "event_ids": ["E1", "E6"],
            "persona": "priya",
            "original_spec_id": "S5",
            "divergence_reason": (
                "S5 named two personas in one row, so the two runs it implies "
                "had no separate identity in any result table; split so each "
                "can be cited"
            ),
            "expected_outcome": "Same movement, different narrative, actions and owners",
            "requirement_ids": ["R2-MPE-3"],
        },
        {
            "scenario_id": "S5b",
            "title": "Two personas, one event - finance director",
            "event_ids": ["E1", "E6"],
            "persona": "arjun",
            "original_spec_id": "S5",
            "divergence_reason": (
                "the finance director half of the original S5 row; a larger "
                "decision value, so the deferral arithmetic differs on "
                "identical evidence"
            ),
            "expected_outcome": "Same movement, different narrative, actions and owners",
            "requirement_ids": ["R2-MPE-3"],
        },
        {
            "scenario_id": "S6",
            "title": "Entitlement restriction",
            "event_ids": ["E6"],
            "persona": "priya",
            "expected_outcome": "CRM evidence withheld with an explicit count and reason",
            "requirement_ids": ["R2-MPE-7", "R2-CX-8"],
        },
        {
            "scenario_id": "S7",
            "title": "Schema change masquerading as a business event",
            "event_ids": ["E5"],
            "persona": "meera",
            "expected_outcome": "Identified as a data artifact, not a business movement",
            "requirement_ids": ["R2-CX-3"],
        },
    ]
    MANIFEST_PATH.write_text(
        json.dumps({"seed": spec.SEED, "scenarios": scenarios}, indent=2), encoding="utf-8"
    )


def _write_summary(stats: dict) -> None:
    gt = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    lines = [
        "# Generated dataset — scenario summary",
        "",
        f"Seed `{spec.SEED}`. Window {spec.START} to {spec.END} "
        f"({(spec.END - spec.START).days + 1} days). Regenerate with `python -m data.generate`.",
        "",
        "## Table row counts",
        "",
        "| Table | Rows |",
        "|---|---|",
    ]
    for k, v in stats.items():
        lines.append(f"| `{k}` | {v:,} |")

    lines += ["", "## Injected events", "",
              "| ID | Event | Window | Slice | True driver | Detectable | Net revenue change |",
              "|---|---|---|---|---|---|---|"]
    for ev in gt["events"]:
        slice_str = ", ".join(f"{k}={'/'.join(v)}" for k, v in ev["slice"].items())
        measured = ev.get("measured", {})
        chg = measured.get("relative_change_pct")
        chg_str = f"{chg:+.1f}%" if chg is not None else "n/a (data artifact)"
        lines.append(
            f"| {ev['event_id']} | {ev['name']} | {ev['start']} to {ev['end']} | "
            f"{slice_str} | `{ev['true_driver']}` | "
            f"{'yes' if ev['detectable_by_standard_path'] else 'no (sparse path)'} | {chg_str} |"
        )

    lines += [
        "",
        "## Demo scenarios",
        "",
        "These are the scenarios as the evaluation harness actually runs them "
        "(ADR-028). `eval/run_recommendation_eval.py` is the executable "
        "definition; this table is generated from the same manifest it reads, "
        "so the two cannot drift apart.",
        "",
        "The **Expected outcome** column states design *intent*. It is not a "
        "record of what the system decides. That is the scenario table in "
        "`eval/recommendation_report.md`, which is authoritative for every "
        "terminal decision (ADR-027).",
        "",
        "| ID | Title | Events | Persona | Expected outcome (intent) | Case requirement |",
        "|---|---|---|---|---|---|",
    ]
    for sc in manifest["scenarios"]:
        persona = sc["persona"]
        persona_str = "/".join(persona) if isinstance(persona, list) else persona
        lines.append(
            f"| {sc['scenario_id']} | {sc['title']} | {', '.join(sc['event_ids'])} | "
            f"{persona_str} | {sc['expected_outcome']} | {', '.join(sc['requirement_ids'])} |"
        )

    # --- the superseded Round-1 assignment, kept rather than overwritten ---
    diverged = [sc for sc in manifest["scenarios"]
                if sc.get("original_spec_persona") or sc.get("original_spec_id")]
    if diverged:
        lines += [
            "",
            "### Divergence from the Round-1 specification (historical)",
            "",
            "The original assignment is preserved here because it is the record "
            "of what was first intended, and because a reader who finds it "
            "quoted elsewhere needs to know it was superseded rather than "
            "mistaken for current.",
            "",
            "The Round-1 table gave S1 to `priya` and S2 to `arjun`. That "
            "confounds two variables: a difference between those two runs could "
            "come from the event or from the persona, and nothing in the output "
            "separates them. The harness varies one factor at a time instead - "
            "S1..S4 hold the persona fixed and vary the event, S1/S5a/S5b hold "
            "the event fixed and vary the persona. S5 was one row naming two "
            "personas, so the two runs it implied had no separate identity and "
            "could not be cited individually; it is now S5a and S5b.",
            "",
            "| ID | Round-1 spec | Now | Why |",
            "|---|---|---|---|",
        ]
        for sc in diverged:
            was = sc.get("original_spec_persona") or f"part of {sc['original_spec_id']}"
            lines.append(
                f"| {sc['scenario_id']} | {was} | {sc['persona']} | "
                f"{sc.get('divergence_reason', '')} |"
            )
        lines.append("")
        lines.append(
            "S6 and S7 were never reassigned. No injected event, slice, window "
            "or seed changed: the divergence is in who reads each scenario, not "
            "in what the data contains."
        )

    lines += [
        "",
        "## Deliberate data quirks",
        "",
        "- `channel` value `marketplace` was renamed `Marketplace` on "
        f"{spec.SCHEMA_CHANGE_DATE}, splitting that series. Both spellings exist in "
        "`fact_orders`. This is event E5.",
        "- `fact_sessions` has ~3.5% null `region` (unknown geo), forcing an explicit "
        "completeness check.",
        "- Support-ticket volume carries a Monday spike, so a naive day-over-day count "
        "comparison mis-reads Mondays as signal.",
        "- `NewLaunch` does not exist before "
        f"{spec.NEW_LAUNCH_START}, giving it sparse history.",
        "- Source `S3` finance is stamped T+3, so the most recent week is genuinely "
        "unavailable rather than zero.",
        "",
    ]
    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    stats = generate()
    print(f"Wrote {DB_PATH}")
    for k, v in stats.items():
        print(f"  {k:24s} {v:>8,}")
    print(f"Wrote {GROUND_TRUTH_PATH.name}, {MANIFEST_PATH.name}, {SUMMARY_PATH.name}")
