"""Shared value types for the semantic layer.

These live here rather than inside contract.py so that `security/` can be
imported by `semantic/` without a cycle: security produces an AccessDecision,
semantic consumes it, and neither imports the other's module-level state.

Architecture reference: Part 7.7 (LineageRecord), Part 8.2 (gateway return type).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

import pandas as pd
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
)


def _to_plain_datetime(value: Any) -> Any:
    """Normalise any `datetime` SUBCLASS down to an exact `datetime`.

    `pandas.Timestamp` subclasses `datetime.datetime`, so Pydantic accepts it
    for a field annotated `datetime` and silently keeps the pandas type. That
    is invisible until the object reaches the LangGraph checkpointer, which
    refuses to deserialise it:

        Blocked deserialization of method call pandas.Timestamp.fromisoformat
        - not in allowed methods set

    LangGraph then falls back, so nothing crashes and nothing is obviously
    lost — which is precisely why it went unnoticed. But the value is being
    reconstructed through an unintended path on every checkpoint restore, and
    the allowlist that blocks it is a security control, not a nuisance.

    The fix belongs at the type boundary rather than at the serialiser: a
    value that never becomes a `pandas.Timestamp` cannot later fail to
    deserialise as one. `to_pydatetime()` preserves the instant and the
    tzinfo; for a tz-aware Timestamp the offset survives unchanged.
    """
    # NaT first. It is NOT a `pandas.Timestamp` subclass — it is `NaTType` —
    # but it IS an `isinstance` of `datetime`, and every one of its date
    # components is `nan`. Checking it after the branches below means it falls
    # through to the reconstruction path and raises
    # `'float' object cannot be interpreted as an integer`.
    if value is pd.NaT:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    # Any other datetime subclass is rebuilt as an exact datetime, preserving
    # tzinfo. `type(...) is not datetime` rather than a negative isinstance:
    # the point is to catch subclasses specifically.
    if isinstance(value, datetime) and type(value) is not datetime:
        return datetime(
            value.year, value.month, value.day, value.hour, value.minute,
            value.second, value.microsecond, tzinfo=value.tzinfo,
        )
    return value


#: A `datetime` field that cannot hold a `pandas.Timestamp`.
#:
#: Use this instead of a bare `datetime` on any model whose values originate
#: from a pandas DataFrame and that is carried in LangGraph state.
PlainDateTime = Annotated[datetime, BeforeValidator(_to_plain_datetime)]


class Window(BaseModel):
    """A closed date interval [start, end]."""

    start: date
    end: date

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, v: date, info: Any) -> date:
        start = info.data.get("start")
        if start is not None and v < start:
            raise ValueError(f"window end {v} precedes start {start}")
        return v

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.start.isoformat()}..{self.end.isoformat()}"


class LineageRecord(BaseModel):
    """Provenance for one metric read. Produced by the semantic layer at read
    time — never reconstructed afterwards (Part 7.7)."""

    metric_id: str
    contract_version: str
    source_id: str  # S1 | S2 | S3
    source_table: str
    compiled_sql: str
    as_of: datetime  # source watermark
    computed_at: datetime
    freshness_lag_hours: float
    row_count: int
    null_rate: float
    filters_applied: list[str] = Field(default_factory=list)
    columns_masked: list[str] = Field(default_factory=list)
    grain: list[str] = Field(default_factory=list)


class FreshnessStatus(BaseModel):
    """Result of comparing a source watermark against the contract's SLA."""

    cadence: str
    as_of: datetime
    lag_hours: float
    expected_lag_hours: float
    stale_after_hours: float
    is_stale: bool
    note: str = ""


class MetricSeries(BaseModel):
    """What guarded_query() returns: data plus everything needed to defend it."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    kpi_id: str
    df: pd.DataFrame
    lineage: LineageRecord
    freshness: FreshnessStatus
    grain: list[str]
    unit: str
    additive: bool
    attribute_via: list[str] | None = None
    columns_masked: list[str] = Field(default_factory=list)
    row_filters_applied: list[str] = Field(default_factory=list)

    @property
    def rows(self) -> int:
        return len(self.df)


class EntitlementError(PermissionError):
    """Raised when a principal is denied access to a KPI or a source."""


class ContractError(KeyError):
    """Raised when a KPI id is unknown or its contract fails validation."""
