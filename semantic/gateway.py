"""THE ONLY MODULE THAT TOUCHES DuckDB.

Every metric read in the system passes through `guarded_query()`. That is not a
convention — `tests/test_chokepoint.py` asserts it mechanically by scanning the
runtime packages for any other database access.

Why one path: row-, column- and domain-level security (R2-CX-8, R2-MPE-7) is
only credible if it cannot be bypassed. One path is auditable; several are not.
Entitlement resolution, SQL compilation, execution, lineage and the audit write
all happen here, in that order, with no way to skip a step.

Architecture reference: Part 8.2, Part 21.3, ADR-011.
"""

from __future__ import annotations

import re
import threading
from datetime import datetime
from pathlib import Path

import duckdb

from data import spec
from security import audit, entitlements
from security.entitlements import AccessDecision, Principal
from semantic import freshness, registry
from semantic.types import EntitlementError, MetricSeries, Window

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse.duckdb"

_conn: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()


def connect(db_path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open (or reuse) the single connection. Read-write: the audit log is
    append-only but it is still a write."""
    global _conn
    with _lock:
        if _conn is None:
            path = db_path or DB_PATH
            if not path.exists():
                raise FileNotFoundError(
                    f"warehouse not found at {path}. "
                    "Run `python -m data.generate` first."
                )
            _conn = duckdb.connect(str(path))
        return _conn


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def _watermark(con: duckdb.DuckDBPyConnection, source_id: str) -> datetime:
    """Read a source watermark. Private, and inside the gateway on purpose."""
    row = con.execute(
        "SELECT as_of FROM source_watermarks WHERE source_id = ?", [source_id]
    ).fetchone()
    if row is None:
        raise ValueError(f"no watermark recorded for source '{source_id}'")
    return row[0]


def guarded_query(
    kpi_id: str,
    window: Window,
    dims: list[str],
    principal: Principal,
    include_columns: list[str] | None = None,
    db_path: Path | None = None,
) -> MetricSeries:
    """Read one KPI for one principal.

    Raises ContractError for an unknown KPI and EntitlementError when the
    principal may not read it. Both are audited before the exception leaves.
    """
    con = connect(db_path)

    # 1. contract — unknown KPI fails before any policy work
    try:
        contract = registry.get(kpi_id)
    except Exception:
        audit.write(
            con,
            actor=principal.user_id,
            role=principal.role,
            action="metric_query",
            resource=kpi_id,
            decision="DENIED",
            detail="unknown KPI",
        )
        raise

    # 2. entitlement decision
    access: AccessDecision = entitlements.decide(principal, contract)
    if not access.allowed:
        audit.write(
            con,
            actor=principal.user_id,
            role=principal.role,
            action="metric_query",
            resource=kpi_id,
            decision="DENIED",
            policy_applied=access.policy_version,
            detail=access.reason,
        )
        raise EntitlementError(
            f"{principal.display_name} ({principal.role}) may not read "
            f"'{kpi_id}': {access.reason}"
        )

    # 3. compile — row filters and column projections injected here, so denied
    #    columns never enter the result set
    sql, meta = contract.compile_sql(
        window, dims, access, include_columns=include_columns
    )

    # 4. execute
    df = con.execute(sql).df()

    # 5. lineage, built at read time
    as_of = _watermark(con, contract.lineage.source_id)
    computed_at = datetime.now()          # audit: when this query really ran
    evaluated_at = spec.DEMO_NOW          # freshness: the demo's notional clock
    null_rate = float(df["value"].isna().mean()) if "value" in df and len(df) else 0.0
    lineage = contract.build_lineage(
        sql=sql,
        meta=meta,
        as_of=as_of,
        computed_at=computed_at,
        evaluated_at=evaluated_at,
        row_count=len(df),
        null_rate=null_rate,
    )
    fresh = freshness.assess(contract, as_of, now=evaluated_at)

    # 6. audit — always, success included
    audit.write(
        con,
        actor=principal.user_id,
        role=principal.role,
        action="metric_query",
        resource=kpi_id,
        decision=access.decision_label,
        policy_applied=access.policy_version,
        rows_returned=len(df),
        items_withheld=0,
        columns_masked=meta["columns_masked"],
        detail=f"grain={'/'.join(meta['grain'])}; filters={len(meta['filters_applied'])}",
    )

    return MetricSeries(
        kpi_id=contract.id,
        df=df,
        lineage=lineage,
        freshness=fresh,
        grain=meta["grain"],
        unit=contract.unit,
        additive=contract.additive,
        attribute_via=contract.attribute_via,
        columns_masked=meta["columns_masked"],
        row_filters_applied=[access.row_filter_sql] if access.row_filter_sql else [],
    )


def schema_changes(db_path: Path | None = None) -> list[dict]:
    """Recorded value renames, for the preprocess stitching step.

    This is semantic-layer metadata, not a metric, but it still reads the
    database — so it lives here rather than giving detection/ a second path.
    Value renames are parsed out of the change note; the log records the
    change in prose because that is how a real change log is written.

    Architecture reference: Part 9.2 step 1.
    """
    rows = connect(db_path).execute(
        """
        SELECT change_id, changed_at, table_name, column_name, change_type, note
        FROM schema_change_log
        WHERE change_type = 'value_rename'
        ORDER BY changed_at
        """
    ).fetchall()

    out: list[dict] = []
    for change_id, changed_at, table_name, column_name, change_type, note in rows:
        quoted = re.findall(r"'([^']+)'", note or "")
        out.append(
            {
                "change_id": change_id,
                "changed_at": changed_at,
                "table_name": table_name,
                "column_name": column_name,
                "change_type": change_type,
                "note": note,
                "old_value": quoted[0] if len(quoted) > 0 else None,
                "new_value": quoted[1] if len(quoted) > 1 else None,
            }
        )
    return out


# --------------------------------------------------------------------------
# Stage 5 — document access
# --------------------------------------------------------------------------
# The evidence corpus lives in the same database, so it comes through the same
# chokepoint. These are read-only and return raw rows: the retrieval layer
# owns the shaping, this owns the access.
#
# Source access is enforced HERE rather than in the retrieval layer, so an
# unauthorised document cannot reach a ranking function even by mistake. That
# ordering is the whole point of the entitlement test in Stage 5.

CORPUS_TABLES: dict[str, dict] = {
    "support_ticket": {
        "table": "support_tickets",
        "source_id": "S3",
        "policy_source": "support_tickets",
        "id": "ticket_id",
        "timestamp": "created_at",
    },
    "crm_note": {
        "table": "crm_notes",
        "source_id": "S3",
        "policy_source": "crm_notes",
        "id": "note_id",
        "timestamp": "note_date",
    },
    "market_event": {
        "table": "market_events",
        "source_id": "S3",
        "policy_source": "market_events",
        "id": "event_id_doc",
        "timestamp": "event_date",
    },
    "deploy_changelog": {
        "table": "deploy_changelog",
        "source_id": "S3",
        "policy_source": "deploy_changelog",
        "id": "deploy_id",
        "timestamp": "deployed_at",
    },
    "schema_change": {
        "table": "schema_change_log",
        "source_id": "S1",
        "policy_source": "schema_change_log",
        "id": "change_id",
        "timestamp": "changed_at",
    },
    "finance_adjustment": {
        "table": "finance_adjustments",
        "source_id": "S3",
        "policy_source": "finance_adjustments",
        "id": "week_start",
        "timestamp": "week_start",
    },
}


def documents(
    source_type: str,
    principal: Principal | None = None,
    db_path: Path | None = None,
) -> tuple[list[dict], str | None]:
    """Read one corpus table.

    Returns (rows, withheld_reason). When a principal is supplied and the role
    may not read that source, the rows list is EMPTY and the reason is
    populated - the caller never receives the content it is not entitled to,
    so there is nothing to filter out downstream.

    `planted_for` and `is_decoy` are ground-truth labels written by the
    generator. They are returned because tests and the retrieval benchmark
    need them, and it is the retrieval layer's job never to read them at query
    time. `tests/test_retrieval.py` asserts that separation.
    """
    if source_type not in CORPUS_TABLES:
        raise ValueError(f"unknown corpus source_type '{source_type}'")

    meta = CORPUS_TABLES[source_type]
    con = connect(db_path)

    if principal is not None:
        access = entitlements.source_access(principal)
        if not access.permits(meta["policy_source"], meta["source_id"]):
            audit.write(
                con,
                actor=principal.user_id,
                role=principal.role,
                action="corpus_read",
                resource=meta["table"],
                decision="DENIED",
                policy_applied=access.policy_version,
                items_withheld=_corpus_count(con, meta["table"]),
                detail=f"source '{meta['policy_source']}' not permitted",
            )
            return [], (
                f"source '{meta['policy_source']}' not permitted for role "
                f"'{principal.role}'"
            )

    rows = con.execute(f"SELECT * FROM {meta['table']}").fetchdf().to_dict("records")

    if principal is not None:
        audit.write(
            con,
            actor=principal.user_id,
            role=principal.role,
            action="corpus_read",
            resource=meta["table"],
            decision="ALLOWED",
            rows_returned=len(rows),
            detail=f"source_type={source_type}",
        )
    return rows, None


def _corpus_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def audit_trail(db_path: Path | None = None):
    """Read the append-only audit log."""
    return audit.read_all(connect(db_path))
