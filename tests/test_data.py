"""Stage 1 validations — the seven checks the dataset must satisfy."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from data import spec

ROOT = Path(__file__).resolve().parent.parent
GT = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "data" / "scenario_manifest.json").read_text(encoding="utf-8"))


# --- 1. reproducibility ---------------------------------------------------
def _content_digest(db_path: Path) -> str:
    """Hash the *contents* of every table.

    Deliberately not a hash of the file. A DuckDB file embeds internal
    metadata that varies between writes, so two byte-different files can hold
    identical data — verified: same size, different bytes, identical rows.
    Reproducibility of the data is the property that matters, so that is what
    this asserts. Recorded as ADR-013.
    """
    import duckdb

    con = duckdb.connect(str(db_path))
    try:
        tables = sorted(
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        )
        h = hashlib.sha256()
        for t in tables:
            if t == "audit_log":
                continue  # written at query time, not by the generator
            df = con.execute(f"SELECT * FROM {t}").df()
            h.update(t.encode())
            h.update(
                pd.util.hash_pandas_object(df, index=False).values.tobytes()
            )
        return h.hexdigest()
    finally:
        con.close()


@pytest.mark.slow
def test_same_seed_produces_identical_output(tmp_path):
    """Two runs from one seed must produce identical data."""
    from data import generate

    a, b = tmp_path / "a.duckdb", tmp_path / "b.duckdb"
    generate.generate(a)
    gt_a = (ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8")

    generate.generate(b)
    gt_b = (ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8")

    assert _content_digest(a) == _content_digest(b), (
        "same seed produced different data"
    )
    assert gt_a == gt_b, "same seed produced a different ground truth"


def test_ground_truth_records_the_seed():
    assert GT["seed"] == spec.SEED


# --- 2. expected row counts ----------------------------------------------
def test_fact_tables_have_expected_scale(con):
    orders = con.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    sessions = con.execute("SELECT COUNT(*) FROM fact_sessions").fetchone()[0]
    assert 100_000 <= orders <= 140_000, orders
    assert sessions > 200_000


def test_document_corpora_are_within_spec_ranges(con):
    for table, (lo, hi) in spec.EXPECTED_COUNTS.items():
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert lo <= n <= hi, f"{table}={n}, expected {lo}-{hi}"


def test_embedded_corpus_is_about_1370_documents(con):
    total = sum(
        con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("support_tickets", "crm_notes", "market_events")
    )
    assert 1_200 <= total <= 1_500, total


# --- 3. injected events exist --------------------------------------------
def test_all_six_events_are_recorded():
    ids = [e["event_id"] for e in GT["events"]]
    assert ids == ["E1", "E2", "E3", "E4", "E5", "E6"]


def test_planted_evidence_exists_for_each_event(con):
    tickets = con.execute(
        "SELECT planted_for, COUNT(*) FROM support_tickets "
        "WHERE planted_for IS NOT NULL GROUP BY 1"
    ).df().set_index("planted_for")["count_star()"].to_dict()
    assert tickets.get("E1") == 34
    assert tickets.get("E3") == 2
    assert tickets.get("E5") == 12  # decoys

    notes = con.execute(
        "SELECT planted_for, COUNT(*) FROM crm_notes "
        "WHERE planted_for IS NOT NULL GROUP BY 1"
    ).df().set_index("planted_for")["count_star()"].to_dict()
    assert notes.get("E2") == 11
    assert notes.get("E4") == 4
    assert notes.get("E6") == 5

    deploy = con.execute(
        "SELECT COUNT(*) FROM deploy_changelog WHERE planted_for = 'E1'"
    ).fetchone()[0]
    assert deploy == 1


# --- 4. West revenue has the intended material movement -------------------
def test_west_region_has_the_intended_material_movement(con):
    df = con.execute(
        """
        SELECT order_date, SUM(gross_amount - discount_amount - return_amount) AS net
        FROM fact_orders
        WHERE region = 'West' AND channel IN ('Web','Mobile App')
        GROUP BY 1 ORDER BY 1
        """
    ).df()
    df["order_date"] = pd.to_datetime(df["order_date"])
    pre = df[(df.order_date >= "2026-06-14") & (df.order_date < "2026-07-12")]["net"].mean()
    during = df[(df.order_date >= "2026-07-12") & (df.order_date <= "2026-07-26")]["net"].mean()
    change = (during - pre) / pre * 100
    assert change < -15, f"expected a clear drop, got {change:.1f}%"

    contract_threshold = 2.0  # net_revenue min_rel_effect_pct
    assert abs(change) > contract_threshold


def test_baseline_noise_makes_detection_non_trivial(con):
    """Too clean and there is nothing to detect; too noisy and nothing is
    detectable. Part 23 Stage 1 targets a baseline CV of roughly 8-12%."""
    df = con.execute(
        """
        SELECT order_date, SUM(gross_amount - discount_amount - return_amount) AS net
        FROM fact_orders
        WHERE order_date BETWEEN DATE '2026-02-01' AND DATE '2026-05-31'
        GROUP BY 1
        """
    ).df()
    cv = df["net"].std() / df["net"].mean()
    assert 0.06 <= cv <= 0.14, f"baseline CV {cv:.1%} outside the workable band"


# --- 5. sparse history ----------------------------------------------------
def test_newlaunch_has_sparse_history(con):
    first = con.execute(
        "SELECT MIN(order_date) FROM fact_orders WHERE product_category = 'NewLaunch'"
    ).fetchone()[0]
    assert first == spec.NEW_LAUNCH_START

    e4 = next(e for e in GT["events"] if e["event_id"] == "E4")
    history_days = (date.fromisoformat(e4["start"]) - spec.NEW_LAUNCH_START).days
    assert history_days == 23
    # below net_revenue's min_history_days of 56 -> must take the sparse path
    assert history_days < 56
    assert e4["detectable_by_standard_path"] is False


# --- 6. conflicting evidence ---------------------------------------------
def test_conflicting_evidence_scenario_is_balanced(con):
    """E2's evidence must not favour either hypothesis."""
    df = con.execute(
        "SELECT kind, COUNT(*) AS n FROM crm_notes WHERE planted_for='E2' GROUP BY 1"
    ).df().set_index("kind")["n"].to_dict()
    competitor = df.get("competitor", 0)
    stockout = df.get("stockout", 0)
    assert competitor > 0 and stockout > 0
    assert abs(competitor - stockout) <= 1, f"unbalanced: {df}"

    market = con.execute(
        "SELECT COUNT(*) FROM market_events WHERE planted_for='E2'"
    ).fetchone()[0]
    assert market == 6


# --- 7. entitlement scenario ---------------------------------------------
def test_entitlement_scenario_has_restricted_evidence(con):
    """E6 plants CRM notes in West — visible to finance, denied to ops."""
    n = con.execute(
        "SELECT COUNT(*) FROM crm_notes WHERE planted_for='E6' AND region='West'"
    ).fetchone()[0]
    assert n == 5


# --- deliberate data quirks ----------------------------------------------
def test_schema_change_split_the_channel_series(con):
    """Both spellings must exist, split exactly at the change date."""
    vals = {
        r[0] for r in con.execute("SELECT DISTINCT channel FROM fact_orders").fetchall()
    }
    assert {"marketplace", "Marketplace"} <= vals

    last_old = con.execute(
        "SELECT MAX(order_date) FROM fact_orders WHERE channel = 'marketplace'"
    ).fetchone()[0]
    first_new = con.execute(
        "SELECT MIN(order_date) FROM fact_orders WHERE channel = 'Marketplace'"
    ).fetchone()[0]
    assert first_new == spec.SCHEMA_CHANGE_DATE
    assert last_old < spec.SCHEMA_CHANGE_DATE

    logged = con.execute(
        "SELECT COUNT(*) FROM schema_change_log WHERE change_type='value_rename'"
    ).fetchone()[0]
    assert logged == 1


def test_sessions_have_the_declared_null_region_rate(con):
    rate = con.execute(
        "SELECT AVG(CASE WHEN region IS NULL THEN 1.0 ELSE 0.0 END) FROM fact_sessions"
    ).fetchone()[0]
    assert 0.025 <= rate <= 0.045, rate


def test_ticket_volume_has_a_monday_spike(con):
    df = con.execute(
        """
        SELECT DAYOFWEEK(created_at) AS dow, COUNT(*) AS n
        FROM support_tickets WHERE planted_for IS NULL GROUP BY 1 ORDER BY 1
        """
    ).df()
    monday = df[df.dow == 1]["n"].iloc[0]
    others = df[df.dow != 1]["n"].mean()
    assert monday > others * 1.15, f"Monday={monday}, other avg={others:.0f}"


def test_finance_source_is_stamped_t_plus_3(con):
    """S3's lag is measured against the demo clock, not against S1.

    S1 is a T-1 daily batch and S3 is T+3 weekly, so the gap *between the two
    watermarks* is only two days. The property that matters is S3's own lag.
    """
    s3 = con.execute(
        "SELECT as_of FROM source_watermarks WHERE source_id = 'S3'"
    ).fetchone()[0]
    lag_hours = (spec.DEMO_NOW - s3).total_seconds() / 3600.0
    assert lag_hours >= 72, f"S3 lag {lag_hours:.0f}h is not T+3"

    s1 = con.execute(
        "SELECT as_of FROM source_watermarks WHERE source_id = 'S1'"
    ).fetchone()[0]
    s1_lag = (spec.DEMO_NOW - s1).total_seconds() / 3600.0
    assert s1_lag < lag_hours, "the warehouse must be fresher than finance"


# --- manifest -------------------------------------------------------------
def test_scenario_manifest_covers_every_scenario():
    """S5 is split into S5a/S5b: one row naming two personas gave the two runs
    it implied no separate identity, so neither could be cited."""
    ids = [s["scenario_id"] for s in MANIFEST["scenarios"]]
    assert ids == ["S1", "S2", "S3", "S4", "S5a", "S5b", "S6", "S7"]
    for s in MANIFEST["scenarios"]:
        assert s["requirement_ids"], f"{s['scenario_id']} cites no requirement"


def test_the_manifest_matches_the_harness_that_actually_runs(monkeypatch):
    """ADR-028: the harness is the executable scenario definition.

    The manifest is documentation generated alongside it. If they disagree, the
    documentation is wrong by construction - which is exactly the drift that a
    hand-edited generated file produced before.
    """
    from eval.run_recommendation_eval import SCENARIOS, PERSONAS

    harness = {sid: persona for sid, _label, _sf, _cd, persona in SCENARIOS}
    manifest = {s["scenario_id"]: s["persona"] for s in MANIFEST["scenarios"]}

    assert set(harness) == set(manifest), (
        f"scenario ids differ: harness-only {set(harness) - set(manifest)}, "
        f"manifest-only {set(manifest) - set(harness)}"
    )
    for sid, persona in harness.items():
        assert manifest[sid] == persona, (
            f"{sid}: harness runs {persona}, manifest documents "
            f"{manifest[sid]}"
        )
        assert persona in PERSONAS, f"{sid}: unknown persona {persona}"


def test_the_superseded_round1_assignment_is_preserved_not_overwritten():
    """The original spec is history, and history is kept.

    Preserving it is what makes the divergence auditable: a reader who finds
    the Round-1 personas quoted in an older document can tell they were
    superseded deliberately rather than lost.
    """
    by_id = {s["scenario_id"]: s for s in MANIFEST["scenarios"]}

    assert by_id["S1"]["original_spec_persona"] == "priya"
    assert by_id["S2"]["original_spec_persona"] == "arjun"
    assert by_id["S3"]["original_spec_persona"] == "priya"
    assert by_id["S4"]["original_spec_persona"] == "arjun"
    assert by_id["S5a"]["original_spec_id"] == "S5"
    assert by_id["S5b"]["original_spec_id"] == "S5"
    # never reassigned, so nothing to preserve
    assert "original_spec_persona" not in by_id["S6"]
    assert "original_spec_persona" not in by_id["S7"]

    for sid in ("S1", "S2", "S3", "S4", "S5a", "S5b"):
        assert by_id[sid].get("divergence_reason"), (
            f"{sid} diverges from the spec without recording why"
        )


def test_human_readable_summary_exists():
    p = ROOT / "data" / "SCENARIOS.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Injected events" in text and "Demo scenarios" in text
    for eid in ("E1", "E2", "E3", "E4", "E5", "E6"):
        assert eid in text
