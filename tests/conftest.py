from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security.entitlements import Principal  # noqa: E402
from semantic.types import Window  # noqa: E402

DB = ROOT / "data" / "warehouse.duckdb"


@pytest.fixture(scope="session", autouse=True)
def require_warehouse():
    if not DB.exists():
        pytest.skip(
            "data/warehouse.duckdb missing — run `python -m data.generate`",
            allow_module_level=True,
        )


@pytest.fixture(scope="session")
def con():
    """Read-only connection for data-integrity assertions.

    This is a test fixture, not runtime code, so it is exempt from the
    chokepoint rule — and test_chokepoint.py scopes its scan to the runtime
    packages precisely so this exemption is explicit rather than accidental.
    """
    import duckdb

    # same configuration as the gateway, so DuckDB shares the instance
    c = duckdb.connect(str(DB))
    yield c
    c.close()


@pytest.fixture
def priya() -> Principal:
    return Principal(
        user_id="priya", display_name="Priya Nair", role="ops_lead", user_region="West"
    )


@pytest.fixture
def arjun() -> Principal:
    return Principal(
        user_id="arjun", display_name="Arjun Mehta", role="finance_director"
    )


@pytest.fixture
def meera() -> Principal:
    return Principal(
        user_id="meera", display_name="Meera Rao", role="analytics_lead"
    )


@pytest.fixture
def july_window() -> Window:
    """Covers event E1 (West payment gateway degradation)."""
    return Window(start=date(2026, 7, 1), end=date(2026, 7, 31))
