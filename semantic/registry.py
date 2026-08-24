"""Loads and validates every KPI contract at import time.

A malformed contract is a startup failure, not a runtime surprise. That is the
point of validating YAML into Pydantic rather than reading dicts at the call
site.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from semantic.contract import KPIContract
from semantic.types import ContractError

KPI_DIR = Path(__file__).parent / "kpis"


@lru_cache(maxsize=1)
def _load_all() -> dict[str, KPIContract]:
    contracts: dict[str, KPIContract] = {}
    errors: list[str] = []

    for path in sorted(KPI_DIR.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            contract = KPIContract(**doc)
        except Exception as exc:  # noqa: BLE001 - collected and re-raised together
            errors.append(f"{path.name}: {exc}")
            continue
        if contract.id != path.stem:
            errors.append(
                f"{path.name}: contract id '{contract.id}' does not match filename"
            )
            continue
        contracts[contract.id] = contract

    if errors:
        raise ContractError("invalid KPI contracts:\n  " + "\n  ".join(errors))
    if not contracts:
        raise ContractError(f"no KPI contracts found in {KPI_DIR}")
    return contracts


def get(kpi_id: str) -> KPIContract:
    contracts = _load_all()
    if kpi_id not in contracts:
        raise ContractError(
            f"unknown KPI '{kpi_id}'. Known: {sorted(contracts)}"
        )
    return contracts[kpi_id]


def all_ids() -> list[str]:
    return sorted(_load_all())


def all_contracts() -> list[KPIContract]:
    return [_load_all()[k] for k in all_ids()]


def reload() -> None:
    """Drop the cache. Used by tests that write temporary contracts."""
    _load_all.cache_clear()
