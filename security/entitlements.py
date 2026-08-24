"""Role-based access decisions.

Produces an AccessDecision that the semantic layer injects into SQL *before*
execution. Nothing here touches the database — enforcement happens upstream of
every consumer, including the model (Architecture Part 21.3).

The ordering is the security property: filtering before retrieval means a
restricted document cannot influence an answer even indirectly. Masking at
render time would leave it in the model's context.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

POLICY_PATH = Path(__file__).parent / "policy.yaml"


class Principal(BaseModel):
    """A simulated identity. In production this is built from an OIDC claim."""

    user_id: str
    display_name: str
    role: str
    user_region: str | None = None

    def __str__(self) -> str:  # pragma: no cover - display only
        scope = self.user_region or "all regions"
        return f"{self.display_name} ({self.role}, {scope})"


class AccessDecision(BaseModel):
    """The full set of restrictions to apply to one read."""

    principal_id: str
    role: str
    kpi_id: str
    allowed: bool
    row_filter_sql: str | None = None          # already parameter-substituted
    denied_columns: list[str] = Field(default_factory=list)
    allowed_sources: list[str] = Field(default_factory=list)
    denied_sources: list[str] = Field(default_factory=list)
    extra_capabilities: list[str] = Field(default_factory=list)
    policy_version: str = ""
    reason: str = ""

    @property
    def decision_label(self) -> str:
        if not self.allowed:
            return "DENIED"
        if self.row_filter_sql or self.denied_columns:
            return "PARTIAL"
        return "ALLOWED"

    def source_permitted(self, source_id: str) -> bool:
        if source_id in self.denied_sources:
            return False
        if "*" in self.allowed_sources:
            return True
        return source_id in self.allowed_sources


class PolicyError(ValueError):
    """Raised when the policy file is malformed or a role is unknown."""


@lru_cache(maxsize=1)
def load_policy(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else POLICY_PATH
    if not p.exists():
        raise PolicyError(f"policy file not found: {p}")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    if "roles" not in doc:
        raise PolicyError("policy file has no 'roles' section")
    return doc


def known_roles() -> list[str]:
    return sorted(load_policy()["roles"].keys())


def decide(principal: Principal, contract: Any) -> AccessDecision:
    """Resolve what `principal` may see of `contract`.

    `contract` is a semantic.contract.KPIContract but is typed loosely here so
    that security/ never imports semantic/ — that direction would create a
    cycle and, worse, would let policy depend on metric definitions.
    """
    policy = load_policy()
    roles = policy["roles"]

    if principal.role not in roles:
        return AccessDecision(
            principal_id=principal.user_id,
            role=principal.role,
            kpi_id=contract.id,
            allowed=False,
            policy_version=policy.get("version", ""),
            reason=f"unknown role '{principal.role}'",
        )

    rp = roles[principal.role]
    source_id = contract.lineage.source_id

    denied_sources = list(rp.get("denied_sources") or [])
    allowed_sources = list(rp.get("allowed_sources") or [])

    # source allowlist is checked first: a denied source is a hard stop
    permitted = source_id not in denied_sources and (
        "*" in allowed_sources or source_id in allowed_sources
    )
    if not permitted:
        return AccessDecision(
            principal_id=principal.user_id,
            role=principal.role,
            kpi_id=contract.id,
            allowed=False,
            allowed_sources=allowed_sources,
            denied_sources=denied_sources,
            policy_version=policy.get("version", ""),
            reason=(
                f"source '{source_id}' is not permitted for role "
                f"'{principal.role}'"
            ),
        )

    # row filter: policy first, contract as the fallback definition
    raw_filter = (rp.get("row_filters") or {}).get(contract.id)
    if raw_filter is None:
        raw_filter = (contract.security.row_filter_by_role or {}).get(principal.role)

    row_filter_sql = None
    if raw_filter and raw_filter.strip().upper() != "TRUE":
        if ":user_region" in raw_filter:
            if not principal.user_region:
                return AccessDecision(
                    principal_id=principal.user_id,
                    role=principal.role,
                    kpi_id=contract.id,
                    allowed=False,
                    policy_version=policy.get("version", ""),
                    reason=(
                        "row filter requires :user_region but the principal "
                        "has none"
                    ),
                )
            raw_filter = raw_filter.replace(
                ":user_region", f"'{principal.user_region}'"
            )
        row_filter_sql = raw_filter

    # denied columns: union of the role policy and anything the contract marks
    # restricted where this role is not on the allow list
    denied = set(rp.get("denied_columns") or [])
    for col, allowed_roles in (contract.security.restricted_columns or {}).items():
        if principal.role not in allowed_roles:
            denied.add(col)

    return AccessDecision(
        principal_id=principal.user_id,
        role=principal.role,
        kpi_id=contract.id,
        allowed=True,
        row_filter_sql=row_filter_sql,
        denied_columns=sorted(denied),
        allowed_sources=allowed_sources,
        denied_sources=denied_sources,
        extra_capabilities=list(rp.get("extra_capabilities") or []),
        policy_version=policy.get("version", ""),
        reason="",
    )


# --------------------------------------------------------------------------
# Stage 5 — source access without a KPI contract
# --------------------------------------------------------------------------
class SourceAccess(BaseModel):
    """Which document sources a role may read.

    `decide()` answers the same question for a KPI, but it needs a contract to
    do it. Evidence documents have no contract, so this resolves the role's
    source allowlist directly from the same policy file. One policy, two entry
    points - not two policies.
    """

    role: str
    policy_version: str
    allowed_sources: list[str] = Field(default_factory=list)
    denied_sources: list[str] = Field(default_factory=list)

    def permits(self, policy_source: str, source_id: str = "") -> bool:
        """Specific source names outrank the coarse source id.

        The ops_lead policy is the case that fixes the precedence: it denies
        `S3` wholesale but allowlists `support_tickets`, `market_events` and
        `deploy_changelog` by name. Those documents live in S3, so a rule that
        checked the source id first would strip an ops lead of the ticket
        evidence the case explicitly says they should have, while a rule that
        ignored the id would hand them `finance_adjustments`, which they are
        not listed for.

        Order:
          1. named deny      -> refuse (an explicit deny is never overridden)
          2. named allow     -> permit (beats a coarse deny on the source id)
          3. source-id deny  -> refuse
          4. wildcard or source-id allow -> permit
          5. otherwise       -> refuse
        """
        if policy_source and policy_source in self.denied_sources:
            return False
        if policy_source and policy_source in self.allowed_sources:
            return True
        if source_id and source_id in self.denied_sources:
            return False
        if "*" in self.allowed_sources:
            return True
        return bool(source_id and source_id in self.allowed_sources)


def source_access(principal: Principal, path: str | None = None) -> SourceAccess:
    """Resolve a principal's document-source permissions."""
    policy = load_policy(path)
    roles = policy.get("roles", {})
    if principal.role not in roles:
        raise PolicyError(
            f"unknown role '{principal.role}'; known roles: {sorted(roles)}"
        )
    rp = roles[principal.role]
    return SourceAccess(
        role=principal.role,
        policy_version=policy.get("version", "unknown"),
        allowed_sources=list(rp.get("allowed_sources") or []),
        denied_sources=list(rp.get("denied_sources") or []),
    )
