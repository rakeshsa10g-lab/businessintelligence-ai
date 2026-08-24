"""Gate 2 in action: the same bundle, one faithful narrative and one that lies.

    python -m eval.demo_verification

The demo beat is the second half. A fluent, confident, entirely plausible
paragraph arrives, and the system refuses it — naming which sentence, which
number, and which rule. Being able to show the moment a system declines to pass
a good-looking answer is a stronger claim than showing the answer.
"""

from __future__ import annotations

from datetime import date

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window
from verification.engine import build_deterministic_narrative, verify_narrative
from verification.types import Claim, ClaimType, Narrative

RULE = "=" * 78
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)


def build(slice_filter, principal, persona, cause_date, scenario, index):
    d = det.detect("net_revenue", WINDOW, principal,
                   slice_filter=slice_filter, scenario_id=scenario)
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=40)
    r = ret.retrieve_evidence(a, principal, index=index)
    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario}", persona_id=persona,
        detection=d, attribution=a, retrieval=r,
    )


def show_narrative(title: str, narrative: Narrative) -> None:
    print(f"\n{title}")
    print(f"  HEADLINE  {narrative.headline}")
    for c in narrative.claims:
        print(f"  [{c.claim_id}] {c.claim_type.value:<14}{c.text}")
        refs = []
        if c.metric_refs:
            refs.append(f"facts={list(c.metric_refs)}")
        if c.evidence_ids:
            refs.append(f"evidence={list(c.evidence_ids)}")
        if c.hypothesis_id:
            refs.append(f"hypothesis={c.hypothesis_id}")
        if refs:
            print(f"        {'  '.join(refs)}")
    for caveat in narrative.caveats:
        print(f"  CAVEAT    {caveat}")
    if narrative.recommendation_ids:
        print(f"  ACTIONS   {list(narrative.recommendation_ids)}")


def show_report(report) -> None:
    verdict = "PASSED - may reach a human" if report.passed else "BLOCKED"
    print(f"\n  GATE 2: {verdict}")
    print(f"    {report.checks_passed}/{len(report.checks_run)} checks passed, "
          f"{report.hard_violation_count} hard violations")
    for v in report.violations:
        if v.severity.value == "INFO":
            continue
        print(f"    {v.severity.value} {v.code.value}"
              + (f" [{v.claim_id}]" if v.claim_id else ""))
        print(f"        {v.detail}")
        if v.rationale:
            print(f"        why this blocks: {v.rationale}")


def main() -> None:
    index = load_index()
    analyst = Principal(
        user_id="meera", display_name="Meera Rao", role="analytics_lead"
    )
    bundle = build(
        {"region": ["West"], "channel": ["Web", "Mobile App"]},
        analyst, "meera", date(2026, 7, 12), "S1", index,
    )

    print(RULE)
    print("GATE 2 - DETERMINISTIC POST-GENERATION VERIFICATION")
    print(f"bundle {bundle.bundle_hash[:24]}  persona {bundle.persona.role}")
    print(RULE)

    faithful = build_deterministic_narrative(bundle)
    show_narrative("A. THE DETERMINISTIC NARRATIVE (faithful by construction)",
                   faithful)
    show_report(verify_narrative(bundle, faithful))

    # Everything below is plausible, fluent, and wrong in four separate ways.
    top = bundle.hypotheses[0]
    weaker = [h for h in bundle.hypotheses if h.hypothesis_id != top.hypothesis_id]
    liar = Narrative(
        headline="Competitor discounting drove a 41.7% revenue collapse in the West",
        claims=(
            Claim(
                claim_id="L1",
                text=(
                    "Net Revenue in the West rose by 41.70%, a swing of "
                    "1,204,880 INR over the window."
                ),
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",),
                direction="up",
            ),
            Claim(
                claim_id="L2",
                text=(
                    "Aggressive competitor discounting caused the shortfall "
                    "across the affected channels."
                ),
                claim_type=ClaimType.CAUSAL,
                hypothesis_id=(weaker[0].hypothesis_id if weaker
                               else "H-external_competitor"),
                evidence_ids=("T99999",),
                direction="down",
            ),
            Claim(
                claim_id="L3",
                text="Issue immediate goodwill refunds to all affected accounts.",
                claim_type=ClaimType.RECOMMENDATION,
                lever_id="L_BLANKET_REFUND",
            ),
        ),
        recommendation_ids=("L_BLANKET_REFUND",),
    )
    show_narrative("B. A FLUENT NARRATIVE THAT LIES", liar)
    show_report(verify_narrative(bundle, liar))

    print(f"\n{RULE}")
    print("Every sentence in B reads like analysis. None of it survived.")
    print(RULE)


if __name__ == "__main__":
    main()
