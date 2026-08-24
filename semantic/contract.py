"""KPI contracts: YAML on disk, Pydantic in memory, SQL at the boundary.

YAML because a judge and a business owner can read it. Pydantic because it must
be validated, versioned and typed. SQL compiled from it because that is the only
way every number in the system provably comes from one definition.

Architecture reference: Part 8.1, Part 8.2.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from semantic.types import LineageRecord, Window


class Formula(BaseModel):
    base_table: str
    date_column: str
    expression: str | None = None                 # additive KPIs
    numerator_expression: str | None = None       # ratio KPIs
    denominator_expression: str | None = None
    denominator_table: str | None = None          # cross-source ratio
    denominator_date_column: str | None = None
    denominator_filters: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_shape_only(self) -> "Formula":
        has_simple = self.expression is not None
        has_ratio = (
            self.numerator_expression is not None
            and self.denominator_expression is not None
        )
        if has_simple == has_ratio:
            raise ValueError(
                "formula must define either 'expression' or both "
                "'numerator_expression' and 'denominator_expression'"
            )
        return self

    @property
    def is_ratio(self) -> bool:
        return self.numerator_expression is not None

    @property
    def is_cross_source(self) -> bool:
        return bool(self.denominator_table) and self.denominator_table != self.base_table


class Dimension(BaseModel):
    name: str
    cardinality: int
    hierarchy_level: int


class Drivers(BaseModel):
    identity: str
    children: list[str]


class DetectionConfig(BaseModel):
    seasonality_period: int
    method: str
    z_threshold: float = 3.0
    pelt_penalty: float = 12.0
    min_history_days: int


class MaterialityRule(BaseModel):
    min_abs_effect: float
    min_abs_effect_unit: str
    min_rel_effect_pct: float
    min_duration_days: int
    rule: str


class FreshnessRule(BaseModel):
    cadence: str
    expected_lag_hours: float
    stale_after_hours: float


class LineageSpec(BaseModel):
    source_id: str
    source_table: str
    upstream: list[str] = Field(default_factory=list)
    owner: str


class SecuritySpec(BaseModel):
    classification: str = "internal"
    row_filter_by_role: dict[str, str] = Field(default_factory=dict)
    restricted_columns: dict[str, list[str]] = Field(default_factory=dict)


class QualitySpec(BaseModel):
    known_null_columns: list[str] = Field(default_factory=list)
    expected_null_rate_pct: float = 0.0
    null_reason: str = ""


class KPIContract(BaseModel):
    id: str
    version: str
    name: str
    definition: str
    unit: str
    additive: bool
    attribute_via: list[str] | None = None

    formula: Formula
    grain: list[str]
    grain_note: str | None = None
    column_map: dict[str, str]
    dimensions: list[Dimension]
    optional_columns: dict[str, str] = Field(default_factory=dict)
    drivers: Drivers | None = None
    quality: QualitySpec | None = None

    detection: DetectionConfig
    materiality: MaterialityRule
    freshness: FreshnessRule
    lineage: LineageSpec
    security: SecuritySpec

    business_owner: str
    allowed_levers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _checks(self) -> "KPIContract":
        missing = [g for g in self.grain if g not in self.column_map]
        if missing:
            raise ValueError(f"{self.id}: grain entries missing from column_map: {missing}")
        dim_names = {d.name for d in self.dimensions}
        grain_dims = {g for g in self.grain if g not in ("date", "week", "hour")}
        if not grain_dims.issubset(dim_names):
            raise ValueError(
                f"{self.id}: grain dimensions {grain_dims - dim_names} have no "
                "entry in 'dimensions'"
            )
        if not self.additive and not self.attribute_via:
            raise ValueError(
                f"{self.id}: non-additive KPI must declare 'attribute_via' so "
                "attribution is routed to the fundamentals (CMMD / Adtributor s4)"
            )
        return self

    # -- helpers ----------------------------------------------------------
    @property
    def time_key(self) -> str:
        """The logical grain entry that carries time ('date' or 'week')."""
        for candidate in ("date", "week", "hour"):
            if candidate in self.grain:
                return candidate
        raise ValueError(f"{self.id}: grain has no time key")

    def dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]

    def physical(self, logical: str) -> str:
        try:
            return self.column_map[logical]
        except KeyError as exc:  # pragma: no cover - guarded by validator
            raise ValueError(f"{self.id}: no column mapping for '{logical}'") from exc

    # -- SQL compilation --------------------------------------------------
    def compile_sql(
        self,
        window: Window,
        dims: list[str],
        access: Any,
        include_columns: list[str] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Compile this contract into SQL for one read.

        Row predicates and column projections are injected here, so denied
        columns never enter the result set (Part 21.3, enforcement point 1).

        Returns the SQL plus the metadata the gateway needs to build lineage.
        """
        unknown = [d for d in dims if d not in self.dimension_names()]
        if unknown:
            raise ValueError(
                f"{self.id}: dimensions {unknown} are not in this contract's "
                f"grain (available: {self.dimension_names()})"
            )

        time_key = self.time_key
        time_col = self.physical(time_key)
        f = self.formula

        # requested optional columns, minus anything the role may not see
        requested = list(include_columns or [])
        masked = [c for c in requested if c in (access.denied_columns or [])]
        kept = [c for c in requested if c not in masked]
        unknown_opt = [c for c in kept if c not in self.optional_columns]
        if unknown_opt:
            raise ValueError(f"{self.id}: unknown optional columns {unknown_opt}")

        filters = list(f.filters)
        filters.append(
            f"{time_col} >= DATE '{window.start.isoformat()}' "
            f"AND {time_col} < DATE '{window.end.isoformat()}' + INTERVAL 1 DAY"
        )
        if access.row_filter_sql:
            filters.append(f"({access.row_filter_sql})")

        group_cols = [f"CAST({time_col} AS DATE) AS {time_key}"] + [
            f"{self.physical(d)} AS {d}" for d in dims
        ]
        group_by = ", ".join(str(i + 1) for i in range(len(group_cols)))

        select_extra = [f"{self.optional_columns[c]} AS {c}" for c in kept]

        if not f.is_ratio:
            select_list = group_cols + [f"{f.expression} AS value"] + select_extra
            sql = (
                f"SELECT {', '.join(select_list)}\n"
                f"FROM {f.base_table}\n"
                f"WHERE {' AND '.join(filters)}\n"
                f"GROUP BY {group_by}\n"
                f"ORDER BY {group_by}"
            )
        elif not f.is_cross_source:
            select_list = group_cols + [
                f"{f.numerator_expression} AS numerator",
                f"{f.denominator_expression} AS denominator",
                f"CASE WHEN {f.denominator_expression} = 0 THEN NULL "
                f"ELSE {f.numerator_expression} / NULLIF({f.denominator_expression},0) END AS value",
            ] + select_extra
            sql = (
                f"SELECT {', '.join(select_list)}\n"
                f"FROM {f.base_table}\n"
                f"WHERE {' AND '.join(filters)}\n"
                f"GROUP BY {group_by}\n"
                f"ORDER BY {group_by}"
            )
        else:
            # Cross-source ratio: numerator and denominator live in different
            # systems at different grains, so reconcile them explicitly.
            den_time = f.denominator_date_column or time_col
            den_filters = list(f.denominator_filters)
            den_filters.append(
                f"{den_time} >= DATE '{window.start.isoformat()}' "
                f"AND {den_time} < DATE '{window.end.isoformat()}' + INTERVAL 1 DAY"
            )
            if access.row_filter_sql:
                den_filters.append(f"({access.row_filter_sql})")

            # align the denominator's daily grain onto the numerator's weeks
            den_time_expr = (
                f"DATE_TRUNC('week', {den_time})" if time_key == "week" else f"CAST({den_time} AS DATE)"
            )
            join_dims = [d for d in dims]
            num_cols = [f"CAST({time_col} AS DATE) AS {time_key}"] + [
                f"{self.physical(d)} AS {d}" for d in join_dims
            ]
            den_cols = [f"CAST({den_time_expr} AS DATE) AS {time_key}"] + [
                f"{d} AS {d}" for d in join_dims
            ]
            num_group = ", ".join(str(i + 1) for i in range(len(num_cols)))
            den_group = ", ".join(str(i + 1) for i in range(len(den_cols)))
            join_on = " AND ".join(
                [f"n.{time_key} = d.{time_key}"] + [f"n.{d} = d.{d}" for d in join_dims]
            )
            outer_extra = [f"n.{c}" for c in kept]
            sql = (
                f"WITH num AS (\n"
                f"  SELECT {', '.join(num_cols)}, {f.numerator_expression} AS numerator"
                + (", " + ", ".join(f"{self.optional_columns[c]} AS {c}" for c in kept) if kept else "")
                + f"\n  FROM {f.base_table}\n"
                f"  WHERE {' AND '.join(filters)}\n"
                f"  GROUP BY {num_group}\n"
                f"),\n"
                f"den AS (\n"
                f"  SELECT {', '.join(den_cols)}, {f.denominator_expression} AS denominator\n"
                f"  FROM {f.denominator_table}\n"
                f"  WHERE {' AND '.join(den_filters)}\n"
                f"  GROUP BY {den_group}\n"
                f")\n"
                f"SELECT n.{time_key}, "
                + ", ".join(f"n.{d}" for d in join_dims)
                + (", " if join_dims else " ")
                + "n.numerator, d.denominator, "
                f"CASE WHEN d.denominator = 0 THEN NULL "
                f"ELSE n.numerator / NULLIF(d.denominator,0) END AS value"
                + (", " + ", ".join(outer_extra) if outer_extra else "")
                + f"\nFROM num n JOIN den d ON {join_on}\n"
                f"ORDER BY 1"
            )

        meta = {
            "filters_applied": filters,
            "columns_masked": masked,
            "columns_included": kept,
            "grain": [time_key] + dims,
            "source_id": self.lineage.source_id,
            "source_table": f.base_table,
            "is_ratio": f.is_ratio,
            "is_cross_source": f.is_cross_source,
        }
        return sql, meta

    def build_lineage(
        self,
        *,
        sql: str,
        meta: dict[str, Any],
        as_of: datetime,
        computed_at: datetime,
        evaluated_at: datetime,
        row_count: int,
        null_rate: float,
    ) -> LineageRecord:
        # Lag is measured against the evaluation clock, not wall time, so that
        # lineage and the freshness panel can never disagree (ADR-014).
        lag = (evaluated_at - as_of).total_seconds() / 3600.0
        return LineageRecord(
            metric_id=self.id,
            contract_version=self.version,
            source_id=meta["source_id"],
            source_table=meta["source_table"],
            compiled_sql=sql,
            as_of=as_of,
            computed_at=computed_at,
            freshness_lag_hours=round(lag, 2),
            row_count=row_count,
            null_rate=round(null_rate, 4),
            filters_applied=meta["filters_applied"],
            columns_masked=meta["columns_masked"],
            grain=meta["grain"],
        )
