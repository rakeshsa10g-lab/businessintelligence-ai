"""Print the frozen EvidenceBundle for the Stage 6 scenarios.

    python -m eval.demo_bundle              S1 and S2
    python -m eval.demo_bundle --all        every scenario, including the
                                            ones where the system declines
    python -m eval.demo_bundle --personas   the same event, two personas

No narrative prose here, deliberately. The point is to show that the bundle
already contains everything a narrator would need - and nothing it should not
have.
"""

from __future__ import annotations

import sys
from datetime import date

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle, verify_hash
from evidence.types import EvidenceBundle
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
RULE = "=" * 78
THIN = "-" * 78

SCENARIOS = {
    "S1": {
        "label": "West revenue - strong evidence",
        "slice": {"region": ["West"], "channel": ["Web", "Mobile App"]},
        "cause_date": date(2026, 7, 12),
        "expect": "one clearly separated hypothesis",
    },
    "S2": {
        "label": "South x Apparel - conflicting evidence",
        "slice": {"region": ["South"], "product_category": ["Apparel"]},
        "cause_date": date(2026, 6, 2),
        "expect": "at least two credible hypotheses, neither promoted",
    },
    "S3": {
        "label": "East x SMB - thin evidence",
        "slice": {"region": ["East"], "segment": ["SMB"]},
        "cause_date": date(2026, 8, 5),
        "expect": "no false confidence",
    },
    "S4": {
        "label": "NewLaunch - sparse history",
        "slice": {"product_category": ["NewLaunch"]},
        "cause_date": None,
        "expect": "no hypothesis at all; nothing to explain",
    },
    "S7": {
        "label": "Marketplace rename - schema change",
        "slice": {"channel": ["Marketplace"]},
        "cause_date": date(2026, 6, 14),
        "expect": "a data-definition cause, not a commercial one",
    },
}

PERSONAS = {
    "meera": "analytics_lead",
    "priya": "ops_lead",
    "arjun": "finance_director",
}


def build(scenario_id: str, persona_id: str, index) -> EvidenceBundle:
    cfg = SCENARIOS[scenario_id]
    principal = Principal(
        user_id=persona_id,
        display_name=persona_id.title(),
        role=PERSONAS[persona_id],
        user_region="West" if PERSONAS[persona_id] == "ops_lead" else None,
    )
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=cfg["slice"],
        scenario_id=scenario_id,
    )
    a = att.attribute(
        d, principal, cause_date=cfg["cause_date"], n_resamples=40
    )
    if d.observed_start is None and d.changepoint_date is None:
        r = None
    else:
        r = ret.retrieve_evidence(a, principal, index=index)

    if r is None:
        # Sparse history: retrieval has no dated anchor. The bundle is still
        # built, because "we could not establish a movement" is an answer the
        # narrator has to be able to give.
        from retrieval.types import (
            FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
        )
        r = RetrievalResult(
            query=RetrievalQuery(text="", built_from="not run: no dated movement"),
            filters=FilterConditions(),
            config=RetrievalConfig(
                embedding_model=index.model_name,
                embedding_dim=index.embedding_dim,
                corpus_hash=index.corpus_hash,
            ),
            method="not run: detection established no dated movement",
        )

    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario_id}-{persona_id}",
        persona_id=persona_id,
        detection=d,
        attribution=a,
        retrieval=r,
        history_days=23 if scenario_id == "S4" else 229,
        has_stable_baseline=scenario_id != "S4",
    )


def show(bundle: EvidenceBundle, expect: str = "") -> None:
    print(RULE)
    print("BUSINESSINTELLIGENCE.AI")
    print(f"RUN: {bundle.bundle_id}")
    print(f"BUNDLE HASH: {bundle.bundle_hash[:32]}  (verified: {verify_hash(bundle)})")
    print(RULE)

    p = bundle.persona
    print(f"\nPERSONA\n  {p.display_name} - {p.title} ({p.role})")
    print(f"  wants: {p.wants}")
    print(f"  narrator should lead with: {', '.join(p.emphasis)}")

    print(f"\nKPI\n  {bundle.kpi_name} - "
          f"{', '.join(f'{k}={v}' for k, v in (bundle.hypotheses[0].slice if bundle.hypotheses else ()))or 'all slices'}")
    print(f"  Period: {bundle.window_start} -> {bundle.window_end}")

    movement = bundle.fact("F-movement-pct")
    if movement:
        print(f"\nMOVEMENT\n  {movement.value:+.1f}%")
    if expect:
        print(f"\nEXPECTED  {expect}")

    print(f"\nSTATUS\n  {bundle.overall_status.value}")
    print(f"  {bundle.status_reason}")

    print(f"\nHYPOTHESES ({len(bundle.hypotheses)})")
    if not bundle.hypotheses:
        print("  (none - the system declined to offer an explanation)")
    for h in bundle.hypotheses:
        print(f"\n  #{h.rank} {h.statement}")
        print(f"      Score: {h.score:.3f}   "
              f"(movement confidence {h.score_breakdown.movement_confidence:.2f} "
              f"x evidence fit {h.score_breakdown.evidence_fit:.2f} "
              f"x contradiction {h.score_breakdown.contradiction_multiplier:.2f})")
        print(f"      Status: {h.status.value}   Quality: {h.evidence_quality.value}")
        print(f"      Contribution: {h.contribution_share:.0%} of the movement"
              if h.contribution_share is not None else "      Contribution: n/a")
        print(f"      Robustness: {h.robustness}")
        print(f"      Supporting: {h.evidence_count} distinct "
              f"({h.evidence_profile.total_documents} incl. "
              f"{h.evidence_profile.duplicate_documents} duplicates)")
        print(f"      Contradicting: {h.contradiction_count}")
        print(f"      Causal language: "
              f"{'LICENSED' if h.causal_language_allowed else 'DENIED'}")
        if h.eligible_lever_ids:
            print(f"      Eligible levers: {', '.join(h.eligible_lever_ids)}")

    print(f"\nMETRIC FACTS ({len(bundle.metric_facts)}) - the numeric allowlist")
    for f in bundle.metric_facts[:8]:
        print(f"  {f.fact_id:<26}{f.render()}")
    if len(bundle.metric_facts) > 8:
        print(f"  ... and {len(bundle.metric_facts) - 8} more")

    print(f"\nEVIDENCE  {len(bundle.supporting_evidence)} supporting, "
          f"{len(bundle.contradicting_evidence)} contradicting, "
          f"{len(bundle.cohorts)} cohorts")
    for e in bundle.supporting_evidence[:5]:
        dup = f" (+{e.duplicate_count} near-identical)" if e.duplicate_count else ""
        print(f"  [{e.stance.value[:7]}/{e.weight.value:<8}] "
              f"{e.source_type.value:<17}{e.timestamp.date()}  "
              f"{(e.title or e.excerpt)[:44]}{dup}")
    for e in bundle.contradicting_evidence[:3]:
        print(f"  [CONTRA /{e.weight.value:<8}] "
              f"{e.source_type.value:<17}{e.timestamp.date()}  "
              f"{(e.title or e.excerpt)[:44]}")
    for c in bundle.cohorts[:3]:
        print(f"  [cohort] {c.statement[:88]}")

    print(f"\nALLOWED LEVERS ({len(bundle.allowed_levers)}) - a closed set")
    for lever in bundle.allowed_levers:
        rights = ("may approve" if lever.persona_may_approve
                  else "may request" if lever.persona_may_request else "no rights")
        print(f"  {lever.lever_id:<24}{lever.name[:38]:<40}"
              f"owner={lever.owner_role:<20}{rights}")

    sc = bundle.security_context
    print(f"\nSECURITY CONTEXT")
    print(f"  policy {sc.policy_version}, role {sc.role}")
    print(f"  permitted regions: {', '.join(sc.permitted_regions) or 'all'}")
    print(f"  denied sources: {', '.join(sc.denied_sources) or 'none'}")
    if sc.withheld_item_count:
        print(f"  WITHHELD: {sc.withheld_item_count} source(s) "
              f"({', '.join(sc.withheld_source_ids)}) - never loaded, so they "
              f"took no part in ranking")

    print(f"\nDATA QUALITY  {', '.join(q.value for q in bundle.data_quality_state)}")
    for note in bundle.data_quality_notes[:2]:
        print(f"  - {note[:88]}")

    print(f"\nCONFIG VERSIONS  "
          f"{', '.join(f'{k}={v}' for k, v in bundle.config_versions)}")
    print(RULE)
    print()


def main() -> None:
    args = set(sys.argv[1:])
    index = load_index()

    if "--personas" in args:
        print("\nSAME EVENT, THREE PERSONAS - identical facts, different context\n")
        for persona_id in ("meera", "priya", "arjun"):
            b = build("S1", persona_id, index)
            sc = b.security_context
            print(f"{persona_id:<8}{b.persona.role:<20}"
                  f"hash={b.bundle_hash[:12]}  "
                  f"facts={len(b.metric_facts):<3} "
                  f"evidence={len(b.supporting_evidence):<3} "
                  f"levers={len(b.allowed_levers):<3} "
                  f"withheld={sc.withheld_item_count}")
        print("\nFull bundle for the ops lead (note the withheld source):\n")
        show(build("S1", "priya", index))
        return

    wanted = ["S1", "S2"] if "--all" not in args else list(SCENARIOS)
    for scenario_id in wanted:
        show(build(scenario_id, "meera", index), SCENARIOS[scenario_id]["expect"])


if __name__ == "__main__":
    main()
