"""Gate 2 — the deterministic post-generation verifier, and the fallback.

Two public functions, both operating purely on typed inputs:

    verify_narrative(bundle, narrative) -> VerificationReport
    build_deterministic_narrative(bundle) -> Narrative

Neither knows about Streamlit, LangGraph, prompts, retrieval or the database.
Neither calls a model. Given the same bundle and the same narrative, the report
is byte-identical — there is no randomness and no external service anywhere in
the path.

**The deterministic narrative is a feature, not a hidden fallback.** It is
mechanically rendered from the frozen bundle, so it is faithful by
construction: every number it states is a metric fact, every citation is an
evidence id from the bundle, and it uses causal wording only where the licence
was granted. Being able to show the moment a system refuses to let a fluent
sentence through is a stronger demonstration than the fluent sentence.

It is also the verifier's own test. If the mechanically faithful narrative
fails Gate 2, the gate is wrong — `test_the_deterministic_narrative_passes_its
_own_verifier` pins that.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from evidence.types import EvidenceBundle, HypothesisStatus
from verification import causal as causal_check
from verification import citations as citation_check
from verification import coverage as coverage_check
from verification import direction as direction_check
from verification import membership as membership_check
from verification import numeric as numeric_check
from verification.types import (
    VERIFICATION_VERSION,
    CheckResult,
    Claim,
    ClaimType,
    Narrative,
    Severity,
    VerificationReport,
    Violation,
)


# --------------------------------------------------------------------------
# hashing
# --------------------------------------------------------------------------
def narrative_hash(narrative: Narrative) -> str:
    """Canonical hash of a narrative, so a report names what it verified."""
    payload = narrative.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Gate 2
# --------------------------------------------------------------------------
def verify_narrative(
    bundle: EvidenceBundle,
    narrative: Narrative,
    *,
    run_id: str | None = None,
    known_evidence_ids: set[str] | None = None,
) -> VerificationReport:
    """Run every check. Hard violations block delivery."""
    checks: list[CheckResult] = []
    violations: list[Violation] = []

    def run(name: str, found: list[Violation], note: str = "") -> None:
        checks.append(CheckResult(
            name=name, passed=not found, violation_count=len(found), note=note
        ))
        violations.extend(found)

    run("numeric_allowlist", numeric_check.check(narrative, bundle),
        note=f"{len(numeric_check.allowed_numbers(bundle))} allowed values")
    run("driver_membership", membership_check.check_drivers(narrative, bundle))
    run("metric_ref_validity",
        membership_check.check_metric_refs(narrative, bundle))
    run("direction_consistency", direction_check.check(narrative, bundle))
    run("evidence_coverage",
        coverage_check.check_evidence_coverage(narrative, bundle))
    run("citation_validity", citation_check.check(narrative, bundle))
    if known_evidence_ids:
        run("foreign_citation",
            citation_check.check_foreign_citation(
                narrative, bundle, known_evidence_ids
            ))
    run("dominant_driver_coverage",
        coverage_check.check_dominant_driver(narrative, bundle))
    run("causal_language_licence", causal_check.check(narrative, bundle))
    run("lever_membership", membership_check.check_levers(narrative, bundle))
    run("unused_evidence",
        coverage_check.check_unused_evidence(narrative, bundle))

    hard = [v for v in violations if v.severity is Severity.HARD]
    soft = [v for v in violations if v.severity is Severity.SOFT]
    info = [v for v in violations if v.severity is Severity.INFO]

    # Ordered so a report reads the same way every time: hard first, then by
    # code, then by claim. Determinism includes the order of the list.
    ordered = tuple(sorted(
        violations,
        key=lambda v: (
            {Severity.HARD: 0, Severity.SOFT: 1, Severity.INFO: 2}[v.severity],
            v.code.value,
            v.claim_id or "",
            v.offending_value or "",
        ),
    ))

    return VerificationReport(
        run_id=run_id or bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        narrative_hash=narrative_hash(narrative),
        passed=not hard,
        violations=ordered,
        hard_violation_count=len(hard),
        soft_violation_count=len(soft),
        info_violation_count=len(info),
        checks_run=tuple(checks),
        checks_passed=sum(1 for c in checks if c.passed),
        checks_failed=sum(1 for c in checks if not c.passed),
        verification_version=VERIFICATION_VERSION,
        verified_at=datetime.now(),
        mode=("deterministic_template" if narrative.generated_deterministically
              else "structured"),
    )


# --------------------------------------------------------------------------
# the deterministic narrative
# --------------------------------------------------------------------------
def _fmt(fact) -> str:
    """Render a fact's value exactly as the numeric check will read it."""
    if fact.unit == "INR":
        return f"{fact.value:,.0f} INR"
    if fact.unit in ("pct", "%"):
        return f"{fact.value:.2f}%"
    if fact.unit == "days":
        return f"{fact.value:.0f} days"
    if fact.unit == "ratio":
        return f"{fact.value:.4f}"
    return f"{fact.value:,.2f}"


def build_deterministic_narrative(bundle: EvidenceBundle) -> Narrative:
    """A mechanical narrative, faithful by construction.

    No model, no retrieval, no arithmetic beyond formatting values the bundle
    already holds. Six parts: what changed, the primary driver, the evidence,
    the uncertainty, a recommendation where one is eligible, and a caveat
    whenever causal wording was denied.
    """
    claims: list[Claim] = []
    caveats: list[str] = []
    n = 0

    def add(text, claim_type, **kw) -> None:
        nonlocal n
        n += 1
        claims.append(Claim(
            claim_id=f"C{n:02d}", text=text, claim_type=claim_type, **kw
        ))

    slice_label = ", ".join(
        f"{k}={v}" for k, v in (bundle.hypotheses[0].slice
                                if bundle.hypotheses else ())
    ) or "all slices"

    # --- 1. what changed --------------------------------------------------
    movement_pct = bundle.fact("F-movement-pct")
    movement_abs = bundle.fact("F-movement-abs")
    if movement_pct is not None:
        direction = "down" if movement_pct.value < 0 else "up"
        verb = "declined" if movement_pct.value < 0 else "rose"
        refs = [movement_pct.fact_id]
        text = (
            f"{bundle.kpi_name} in {slice_label} {verb} by "
            f"{abs(movement_pct.value):.2f}% between {bundle.window_start} "
            f"and {bundle.window_end}"
        )
        if movement_abs is not None:
            refs.append(movement_abs.fact_id)
            text += f", a change of {abs(movement_abs.value):,.0f} INR"
        add(text + ".", ClaimType.OBSERVATION,
            metric_refs=tuple(refs), direction=direction)
    else:
        # UNCERTAINTY, not OBSERVATION. "We could not establish a movement"
        # is a statement about the analysis, not about the world, and the
        # evidence-coverage rule rightly demands a citation for the latter.
        # Requiring one here would be asking what evidence proves an absence -
        # and on a sparse bundle there are no metric facts to cite anyway.
        add(
            f"No material movement was established for {bundle.kpi_name} in "
            f"{slice_label} over {bundle.window_start} to {bundle.window_end}.",
            ClaimType.UNCERTAINTY, direction="flat",
        )

    # --- 2. the primary driver -------------------------------------------
    if not bundle.hypotheses:
        add(
            f"The system did not identify an explanation: {bundle.status_reason}",
            ClaimType.UNCERTAINTY,
        )
        caveats.append(
            "No hypothesis reached the reporting threshold, so no cause is "
            "offered. This is an abstention, not a finding of no cause."
        )
        return Narrative(
            headline=(
                f"{bundle.kpi_name}, {slice_label}: no explanation offered"
            ),
            claims=tuple(claims), caveats=tuple(caveats),
            generated_deterministically=True,
        )

    top = bundle.hypotheses[0]
    driver_fact = bundle.fact(f"F-driver-{top.driver_id}")
    refs = [driver_fact.fact_id] if driver_fact else []

    # A hypothesis records every evidence id that scored for or against it.
    # The BUNDLE keeps a top-k subset. Citing straight from the hypothesis can
    # therefore reference a document the bundle does not contain — which Gate 2
    # correctly rejects as indistinguishable from a fabricated citation.
    #
    # Found in Stage 13 when a wider document corpus produced 3 contradicting
    # ids on S2 against 1 retained in the bundle, and Gate 2 blocked the
    # deterministic template. The template is documented as unfailable by
    # construction; it was only unfailable by luck.
    _in_bundle = {i.evidence_id for i in bundle.supporting_evidence}
    _in_bundle |= {i.evidence_id for i in bundle.contradicting_evidence}

    def cited(ids, limit: int = 3) -> tuple[str, ...]:
        """Only ids the bundle actually holds, in the hypothesis's order."""
        return tuple(e for e in ids if e in _in_bundle)[:limit]

    if top.status is HypothesisStatus.SUPPORTED:
        lead = f"The leading explanation is {top.statement}"
    elif top.status is HypothesisStatus.CONFLICTED:
        lead = f"Two explanations are equally supported; the first is {top.statement}"
    else:
        lead = f"One possible explanation is {top.statement}"

    share = (
        f", where {top.driver_name} accounts for "
        f"{abs(top.contribution_share) * 100:.2f}% of the movement"
        if top.contribution_share is not None and driver_fact else ""
    )
    add(
        f"{lead}{share}.",
        ClaimType.ATTRIBUTION,
        evidence_ids=cited(top.supporting_evidence_ids),
        metric_refs=tuple(refs),
        hypothesis_id=top.hypothesis_id,
        direction="down" if (movement_pct and movement_pct.value < 0) else "up",
    )

    # --- 3. the evidence --------------------------------------------------
    cohort = next(
        (c for c in bundle.cohorts if c.cohort_id in top.cohort_ids), None
    )
    if cohort is not None:
        add(
            cohort.statement + ".",
            ClaimType.OBSERVATION,
            evidence_ids=(cohort.cohort_id,),
            direction="up" if (cohort.novel or (cohort.ratio or 0) > 1) else "flat",
        )
    elif top.supporting_evidence_ids:
        profile = top.evidence_profile
        add(
            f"{profile.distinct_documents} distinct documents across "
            f"{len(profile.source_types)} source types corroborate this "
            f"explanation.",
            ClaimType.OBSERVATION,
            evidence_ids=cited(top.supporting_evidence_ids),
            direction="n/a",
        )

    # --- 4. uncertainty ---------------------------------------------------
    alternatives = bundle.hypotheses[1:]
    if alternatives:
        # Stated without scores. A hypothesis score is a ranking artefact,
        # not a business figure, and quoting it would mean widening the
        # numeric allowlist to admit numbers no metric fact backs.
        add(
            "Alternative explanations considered, in rank order: "
            + "; ".join(h.statement for h in alternatives)
            + ".",
            ClaimType.UNCERTAINTY,
        )
    if top.contradiction_count:
        add(
            f"Evidence arguing against this explanation was also found and is "
            f"listed alongside it.",
            ClaimType.UNCERTAINTY,
            evidence_ids=cited(top.contradicting_evidence_ids),
        )

    # --- 5. recommendation ------------------------------------------------
    recommendation_ids: list[str] = []
    for lever in bundle.allowed_levers:
        if lever.applies_to_hypothesis_id != top.hypothesis_id:
            continue
        if lever.lever_id == "L_MONITOR_ONLY" and len(bundle.allowed_levers) > 1:
            continue
        recommendation_ids.append(lever.lever_id)
        rights = (
            "may approve" if lever.persona_may_approve
            else "may request" if lever.persona_may_request
            else "has no decision rights on"
        )
        add(
            f"Eligible action: {lever.name}. Owner: {lever.owner_role}. "
            f"{bundle.persona.display_name} {rights} it.",
            ClaimType.RECOMMENDATION, lever_id=lever.lever_id,
        )
        break

    # --- 6. the caveat when causal language was denied --------------------
    if not top.causal_language_allowed:
        caveats.append(
            "This is an association, not an established cause. "
            + (top.causal_language_reason or
               "The counterfactual checks did not license causal language.")
        )
    if bundle.security_context.withheld_item_count:
        caveats.append(
            f"{bundle.security_context.withheld_item_count} evidence source(s) "
            f"were withheld from this view: "
            f"{', '.join(bundle.security_context.withheld_source_ids)}."
        )
    for note in bundle.data_quality_notes[:1]:
        caveats.append(f"Data preparation note: {note}")

    verb = "declined" if (movement_pct and movement_pct.value < 0) else "moved"
    headline = f"{bundle.kpi_name} {verb} in {slice_label}"
    if top.status is HypothesisStatus.CONFLICTED:
        headline += " - two explanations remain open"

    return Narrative(
        headline=headline,
        claims=tuple(claims),
        caveats=tuple(caveats),
        recommendation_ids=tuple(recommendation_ids),
        generated_deterministically=True,
    )
