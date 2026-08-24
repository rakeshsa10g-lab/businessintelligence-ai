"""Append-only audit log (Architecture Part 21.4).

Written by the gateway on every read — never optional, never conditional, and
written for denials as well as successes. A log that only records what
succeeded proves nothing.

This module does not open its own database connection. The gateway owns the
single connection and passes it in, which keeps the chokepoint property intact.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any

#: The logical run every audit row is attributed to.
#:
#: A `ContextVar` rather than a module global, for two reasons found by
#: auditing the log rather than the code:
#:
#: 1. **Correlation.** The previous global was set lazily on first use and
#:    never reset, so one id covered every read for the lifetime of the
#:    process. Measured: two graph runs produced 21 audit rows under a single
#:    id, and that id matched neither run. The column existed but answered
#:    nothing.
#: 2. **Concurrency.** Streamlit serves each session on its own thread. A
#:    module global is shared across them, so two analysts running at once
#:    would interleave under whichever id was written last. A ContextVar is
#:    per-thread and per-task, so they cannot collide.
#:
#: Note what this does NOT affect: `actor`, `role` and `decision` are passed
#: per query from the live principal and were always correct. This is an
#: audit-correlation defect, not an access-control one.
_RUN_ID: ContextVar[str | None] = ContextVar("audit_run_id", default=None)


def set_run_id(run_id: str) -> str:
    """Bind subsequent reads to a caller-supplied run id.

    Called by the graph so the audit trail joins to the run the user sees.
    """
    _RUN_ID.set(run_id)
    return run_id


def new_run_id() -> str:
    """Start a new logical run with a generated id."""
    return set_run_id(uuid.uuid4().hex[:12])


def current_run_id() -> str:
    """The active run id, generating one if nothing bound it.

    The lazy fallback is kept so a direct gateway call outside a graph run
    still produces an attributable row rather than a null.
    """
    rid = _RUN_ID.get()
    if rid is None:
        rid = new_run_id()
    return rid


def write(
    con: Any,
    *,
    actor: str,
    role: str,
    action: str,
    resource: str,
    decision: str,
    policy_applied: str = "",
    rows_returned: int = 0,
    items_withheld: int = 0,
    columns_masked: list[str] | None = None,
    detail: str = "",
) -> None:
    """Append one row. `con` is the gateway's DuckDB connection."""
    con.execute(
        """
        INSERT INTO audit_log
          (ts, run_id, actor, role, action, resource, decision,
           policy_applied, rows_returned, items_withheld, columns_masked, detail)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            datetime.now(),
            current_run_id(),
            actor,
            role,
            action,
            resource,
            decision,
            policy_applied,
            int(rows_returned),
            int(items_withheld),
            ",".join(columns_masked or []),
            detail,
        ],
    )


def read_all(con: Any):
    """Return the whole log. Used by the audit tab and by tests."""
    return con.execute("SELECT * FROM audit_log ORDER BY ts").df()
