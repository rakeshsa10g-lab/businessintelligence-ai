"""The business-lever catalogue and eligibility rules (Part 14.2, 14.3).

A closed set, loaded from `config/levers.yaml`. The future LLM may phrase one
of these actions; it cannot author one. Eligibility is an exact match on cause
bucket, driver, evidence preconditions and persona decision rights — never a
similarity search, because a lever retrieved by embedding is a lever that
nearly applies, and "nearly applies" is how a system recommends rolling back a
deploy that was not the cause.

Stage 6 only decides WHICH levers are eligible and puts them in the bundle.
Impact modelling, owner lookup and monitoring plans are Stage 7.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "levers.yaml"

# The lever that lets the system recommend doing nothing. Without it a weak
# bundle has no eligible action at all, and an empty list reads as a failure
# rather than as the correct answer.
FALLBACK_LEVER = "L_MONITOR_ONLY"


class LeverError(ValueError):
    """The lever catalogue is unusable, or an unknown lever was requested."""


@functools.lru_cache(maxsize=4)
def load_catalogue(path: str | None = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise LeverError(f"no lever catalogue at {p}")
    catalogue = yaml.safe_load(p.read_text(encoding="utf-8"))
    if "levers" not in catalogue:
        raise LeverError("lever catalogue has no 'levers' key")

    seen: set[str] = set()
    for lever in catalogue["levers"]:
        lever_id = lever.get("lever_id")
        if not lever_id:
            raise LeverError("a lever has no lever_id")
        if lever_id in seen:
            raise LeverError(f"duplicate lever_id '{lever_id}'")
        seen.add(lever_id)
    return catalogue


def reload_catalogue() -> None:
    load_catalogue.cache_clear()


def known_lever_ids(path: str | None = None) -> set[str]:
    """The closed set. A recommendation naming anything else is dropped."""
    return {l["lever_id"] for l in load_catalogue(path)["levers"]}


def get(lever_id: str, path: str | None = None) -> dict:
    for lever in load_catalogue(path)["levers"]:
        if lever["lever_id"] == lever_id:
            return lever
    raise LeverError(f"unknown lever '{lever_id}'")


def eligible_levers(
    *,
    cause_bucket: str,
    driver_id: str,
    evidence_types: set[str],
    evidence_strength: float,
    causal_language_allowed: bool,
    has_stable_baseline: bool,
    history_days: int | None,
    contract_allowed_levers: list[str] | None,
    persona_role: str,
    path: str | None = None,
) -> list[tuple[dict, str]]:
    """Which levers apply, and why. Returns (lever, reason) pairs.

    Every gate below can block, and each one exists because of a specific way
    a recommendation goes wrong:

      bucket / driver       a pricing review does not fix a payment gateway
      contract allowlist    the KPI contract names which levers its owner
                            permits at all
      evidence strength     do not act on a hypothesis nothing corroborates
      causal language       a disruptive lever needs the counterfactual to
                            have licensed a causal claim, not merely a
                            correlation
      stable baseline       blocks Scenario 4: no pricing change off 23 days
                            of history
      persona rights        Priya may *request* a rollback; only engineering
                            may approve one
    """
    catalogue = load_catalogue(path)
    out: list[tuple[dict, str]] = []

    for lever in catalogue["levers"]:
        lever_id = lever["lever_id"]
        conditions = lever.get("trigger_conditions") or {}
        rights = lever.get("decision_rights") or {}

        if lever_id == FALLBACK_LEVER:
            continue                              # added last, unconditionally

        buckets = lever.get("applies_to_buckets") or []
        if buckets and cause_bucket not in buckets:
            continue
        drivers = lever.get("applies_to_drivers") or []
        if drivers and driver_id not in drivers:
            continue

        if contract_allowed_levers and lever_id not in contract_allowed_levers:
            continue

        required_types = set(conditions.get("requires_evidence_types") or [])
        if required_types and not (required_types & evidence_types):
            continue

        if evidence_strength < float(conditions.get("min_evidence_strength", 0.0)):
            continue

        if conditions.get("requires_causal_language") and not causal_language_allowed:
            continue

        if conditions.get("requires_stable_baseline") and not has_stable_baseline:
            continue

        min_history = conditions.get("min_history_days")
        if min_history and (history_days is None or history_days < min_history):
            continue

        may_approve = persona_role in (rights.get("can_approve") or [])
        may_request = persona_role in (rights.get("can_request") or [])
        if not (may_approve or may_request):
            continue

        reason = (
            f"bucket '{cause_bucket}' and driver '{driver_id}' match; "
            f"evidence strength {evidence_strength:.2f} >= "
            f"{conditions.get('min_evidence_strength', 0.0)}; "
            f"role '{persona_role}' may "
            f"{'approve' if may_approve else 'request'}"
        )
        out.append((lever, reason))

    fallback = next(
        (l for l in catalogue["levers"] if l["lever_id"] == FALLBACK_LEVER), None
    )
    if fallback is not None:
        rights = fallback.get("decision_rights") or {}
        if persona_role in (rights.get("can_approve") or []) or persona_role in (
            rights.get("can_request") or []
        ):
            out.append(
                (
                    fallback,
                    "always eligible: the system must be able to recommend "
                    "taking no action yet",
                )
            )
    return out
