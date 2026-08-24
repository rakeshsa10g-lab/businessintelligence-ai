"""Gate 2 evaluation — detection rate on deliberately invalid narratives.

The number that matters is **false acceptance**: an invalid narrative that Gate
2 lets through reaches a human as an authoritative statement that is false.
Target is zero, and it is reported first.

False rejection is reported too, and not hidden. A gate that blocks valid work
gets switched off, so a rejection rate is a real cost even when the target for
it is not zero.

The corrupt narratives are the same ten hand-written cases as
`tests/test_verification.py`, imported rather than duplicated so the eval and
the test suite cannot drift apart.

Run:  python -m eval.run_verification_eval
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window
from eval import provenance
from verification.engine import build_deterministic_narrative, verify_narrative
from verification.types import (
    HARD_RATIONALE,
    SEVERITY,
    Claim,
    ClaimType,
    Narrative,
    Severity,
    ViolationCode,
)

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval" / "verification_report.md"

WINDOW = Window(start=date(2026, 1, 1), end=spec.END)
ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
OPS_LEAD = Principal(
    user_id="priya", display_name="Priya Nair", role="ops_lead",
    user_region="West",
)

SCENARIOS = {
    "S1": ({"region": ["West"], "channel": ["Web", "Mobile App"]},
           date(2026, 7, 12), ANALYST, "meera"),
    "S2": ({"region": ["South"], "product_category": ["Apparel"]},
           date(2026, 6, 2), ANALYST, "meera"),
    "S3": ({"region": ["East"], "segment": ["SMB"]},
           date(2026, 8, 5), ANALYST, "meera"),
    "S6": ({"region": ["West"], "channel": ["Web", "Mobile App"]},
           date(2026, 7, 12), OPS_LEAD, "priya"),
}


def build_bundle(scenario_id: str, index):
    slice_filter, cause_date, principal, persona = SCENARIOS[scenario_id]
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario_id,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=20)
    r = ret.retrieve_evidence(a, principal, index=index)
    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario_id}", persona_id=persona,
        detection=d, attribution=a, retrieval=r,
    )


# --------------------------------------------------------------------------
# the invalid narratives, each carrying the code it should trigger
# --------------------------------------------------------------------------
def corrupt_cases(s1, s2, s6) -> list[tuple[str, str, object, ViolationCode]]:
    top1 = s1.hypotheses[0]
    top2 = s2.hypotheses[0]
    weaker = [h for h in s1.hypotheses if h.hypothesis_id != top1.hypothesis_id]

    from retrieval.types import SourceType

    crm = [
        e for e in s1.supporting_evidence
        if e.source_type is SourceType.CRM_NOTE
    ]

    cases: list[tuple[str, str, object, ViolationCode]] = [
        ("A", "invented number", s1, Narrative(
            headline="Net Revenue fell sharply in the West",
            claims=(Claim(
                claim_id="X1",
                text="Net Revenue declined by 41.70%, a shortfall of 1,204,880 INR.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",), direction="down",
            ),),
        ), ViolationCode.UNGROUNDED_NUMBER),

        ("B", "wrong driver", s1, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="The decline is explained by a courier strike.",
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id="H-logistics_disruption",
                metric_refs=("F-movement-pct",), direction="down",
            ),),
        ), ViolationCode.UNKNOWN_DRIVER),

        ("C", "wrong direction", s1, Narrative(
            headline="Net Revenue improved in the West",
            claims=(Claim(
                claim_id="X1",
                text="Net Revenue rose over the period and conversion improved.",
                claim_type=ClaimType.OBSERVATION,
                metric_refs=("F-movement-pct",), direction="up",
            ),),
        ), ViolationCode.DIRECTION_MISMATCH),

        ("D", "missing evidence", s1, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="Payment failures increased sharply during the window.",
                claim_type=ClaimType.OBSERVATION, direction="up",
            ),),
        ), ViolationCode.MISSING_EVIDENCE),

        ("E", "invalid evidence id", s1, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="Support tickets recorded repeated payment failures.",
                claim_type=ClaimType.OBSERVATION,
                evidence_ids=("T99999",), direction="up",
            ),),
        ), ViolationCode.INVALID_EVIDENCE_ID),

        ("F", "dominant driver omitted", s1, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="The movement is consistent with competitive pressure.",
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=(weaker[0].hypothesis_id if weaker
                               else "H-external_competitor"),
                metric_refs=("F-movement-pct",), direction="down",
            ),),
        ), ViolationCode.DOMINANT_DRIVER_OMITTED),

        ("G", "unsupported causal claim", s2, Narrative(
            headline="Competitor pricing hit Apparel in the South",
            claims=(Claim(
                claim_id="X1",
                text="Competitor pricing caused the decline in Apparel revenue.",
                claim_type=ClaimType.CAUSAL,
                hypothesis_id=top2.hypothesis_id,
                evidence_ids=top2.supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",), direction="down",
            ),),
        ), ViolationCode.CAUSAL_LANGUAGE_NOT_LICENSED),

        ("I", "unauthorised evidence id", s6, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="An account escalation recorded repeated failures.",
                claim_type=ClaimType.OBSERVATION,
                evidence_ids=((crm[0].evidence_id,) if crm else ("C00001",)),
                direction="up",
            ),),
        ), ViolationCode.INVALID_EVIDENCE_ID),

        ("J", "invented lever", s1, Narrative(
            headline="Net Revenue fell in the West",
            claims=(Claim(
                claim_id="X1",
                text="Issue refunds to all affected customers immediately.",
                claim_type=ClaimType.RECOMMENDATION, lever_id="L_BLANKET_REFUND",
            ),),
            recommendation_ids=("L_BLANKET_REFUND",),
        ), ViolationCode.UNKNOWN_LEVER),
    ]
    return cases


def valid_cases(bundles: dict) -> list[tuple[str, str, object, object]]:
    """Narratives that MUST pass. Each false rejection here is a real cost."""
    out = []
    for scenario_id, bundle in bundles.items():
        out.append((
            f"V-{scenario_id}",
            f"deterministic narrative, {scenario_id}",
            bundle,
            build_deterministic_narrative(bundle),
        ))

    s1, s2 = bundles["S1"], bundles["S2"]
    top1 = s1.hypotheses[0]
    if top1.causal_language_allowed:
        out.append((
            "H", "licensed causal claim", s1, Narrative(
                headline="Net Revenue fell in the West",
                claims=(Claim(
                    claim_id="X1",
                    text=(
                        "A product or platform failure caused the decline in "
                        "the affected slice."
                    ),
                    claim_type=ClaimType.CAUSAL,
                    hypothesis_id=top1.hypothesis_id,
                    evidence_ids=top1.supporting_evidence_ids[:2],
                    metric_refs=("F-movement-pct",), direction="down",
                ),),
            ),
        ))

    top2 = s2.hypotheses[0]
    out.append((
        "V-assoc", "associative phrasing on a conflicted case", s2, Narrative(
            headline="Two explanations remain open for Apparel in the South",
            claims=(Claim(
                claim_id="X1",
                text=(
                    "Competitive pressure is one plausible contributor, but "
                    "the available evidence does not establish causality."
                ),
                claim_type=ClaimType.ATTRIBUTION,
                hypothesis_id=top2.hypothesis_id,
                evidence_ids=top2.supporting_evidence_ids[:1],
                metric_refs=("F-movement-pct",), direction="down",
            ),),
        ),
    ))
    return out


# --------------------------------------------------------------------------
def main() -> None:
    index = load_index()
    bundles = {sid: build_bundle(sid, index) for sid in SCENARIOS}

    invalid = corrupt_cases(bundles["S1"], bundles["S2"], bundles["S6"])
    valid = valid_cases(bundles)

    line = "=" * 78
    print(line)
    print("GATE 2 VERIFICATION EVALUATION")
    print(line)

    print("\n[1] INVALID NARRATIVES - each must be blocked")
    print(f"    {'case':<6}{'lie':<32}{'expected code':<34}{'caught':<8}blocked")
    caught = 0
    false_accept: list[str] = []
    by_type: Counter = Counter()
    invalid_rows = []

    for case_id, label, bundle, narrative, expected in [
        (c[0], c[1], c[2], c[3], c[4]) for c in invalid
    ]:
        report = verify_narrative(bundle, narrative)
        found = {v.code for v in report.violations}
        hit = expected in found
        caught += hit
        if report.passed:
            false_accept.append(case_id)
        for v in report.violations:
            by_type[v.code.value] += 1
        invalid_rows.append((case_id, label, expected, hit, report))
        print(f"    {case_id:<6}{label:<32}{expected.value:<34}"
              f"{'yes' if hit else 'NO':<8}{'yes' if not report.passed else 'NO'}")

    print("\n[2] VALID NARRATIVES - each must pass")
    print(f"    {'case':<10}{'description':<44}{'passed':<8}violations")
    false_reject: list[str] = []
    valid_rows = []
    for case_id, label, bundle, narrative in valid:
        report = verify_narrative(bundle, narrative)
        if not report.passed:
            false_reject.append(case_id)
        valid_rows.append((case_id, label, report))
        print(f"    {case_id:<10}{label:<44}"
              f"{'yes' if report.passed else 'NO':<8}{report.hard_violation_count}")
        for v in report.hard_violations:
            print(f"        {v}")

    total_checks = sum(len(r.checks_run) for _, _, _, _, r in invalid_rows)
    total_checks += sum(len(r.checks_run) for _, _, r in valid_rows)
    passed_checks = sum(r.checks_passed for _, _, _, _, r in invalid_rows)
    passed_checks += sum(r.checks_passed for _, _, r in valid_rows)

    print("\n[3] SUMMARY")
    print(f"    invalid narratives      {len(invalid)}")
    print(f"    correctly identified    {caught}/{len(invalid)} "
          f"({caught / len(invalid):.0%}) by the expected code")
    print(f"    FALSE ACCEPTANCE        {len(false_accept)}  "
          f"{'<- TARGET IS 0' if false_accept else '(target 0, met)'}")
    print(f"    false rejection         {len(false_reject)} of {len(valid)} valid")
    if false_reject:
        print(f"      rejected: {', '.join(false_reject)}")
    print(f"    total checks executed   {total_checks}")
    print(f"    checks passed           {passed_checks} "
          f"({passed_checks / total_checks:.1%})")

    print("\n[4] VIOLATIONS BY TYPE (invalid narratives)")
    for code, count in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"    {code:<38}{count}")

    write_report(invalid_rows, valid_rows, false_accept, false_reject,
                 total_checks, passed_checks, by_type)
    print(f"\nwrote {REPORT.relative_to(ROOT)}")
    print(line)


def write_report(invalid_rows, valid_rows, false_accept, false_reject,
                 total_checks, passed_checks, by_type) -> None:
    caught = sum(1 for *_, hit, _ in [(r[0], r[1], r[2], r[3], r[4]) for r in invalid_rows])
    L = ["# Gate 2 — verification evaluation", ""]
    L += provenance.banner(
        what="Gate 2 false-acceptance and false-rejection counts",
        caveat=("The corrupt narratives are hand-written to exercise known "
               "violation classes. Zero false acceptance means none of THOSE "
               "got through — not that no corrupt narrative could."),
    )
    L.append("Generated by `python -m eval.run_verification_eval`.")
    L.append("")
    L.append("Gate 2 is deterministic and calls no model. Same bundle plus "
             "same narrative produces the same report, including the order of "
             "the violation list.")
    L.append("")

    L.append("## Headline")
    L.append("")
    L.append("| Metric | Value | Target |")
    L.append("|---|---:|---:|")
    L.append(f"| **False acceptance** (invalid narrative passed) | "
             f"**{len(false_accept)}** | 0 |")
    L.append(f"| False rejection (valid narrative blocked) | "
             f"{len(false_reject)} of {len(valid_rows)} | 0 |")
    hit_count = sum(1 for r in invalid_rows if r[3])
    L.append(f"| Injected violations identified by expected code | "
             f"{hit_count} / {len(invalid_rows)} | all |")
    L.append(f"| Total checks executed | {total_checks} | |")
    L.append(f"| Checks passed | {passed_checks} "
             f"({passed_checks / total_checks:.1%}) | |")
    L.append("")
    if false_accept:
        L.append(f"**{len(false_accept)} invalid narrative(s) were accepted: "
                 f"{', '.join(false_accept)}.** This is the failure that "
                 f"matters; everything else on this page is secondary.")
    else:
        L.append("No invalid narrative was accepted. That is the only result "
                 "on this page that would matter if it were different: a "
                 "blocked valid narrative costs a retry, while an accepted "
                 "invalid one reaches a human as a false statement carrying "
                 "the system's authority.")
    L.append("")

    L.append("## Invalid narratives")
    L.append("")
    L.append("Hand-written, one lie each, constructed independently of the "
             "checker. A verifier tested only against narratives its own code "
             "produced is a verifier tested against itself.")
    L.append("")
    L.append("| Case | The lie | Expected code | Identified | Blocked |")
    L.append("|---|---|---|:--:|:--:|")
    for case_id, label, expected, hit, report in invalid_rows:
        L.append(f"| {case_id} | {label} | `{expected.value}` | "
                 f"{'yes' if hit else 'NO'} | "
                 f"{'yes' if not report.passed else 'NO'} |")
    L.append("")

    L.append("## Valid narratives")
    L.append("")
    L.append("| Case | Description | Passed | Hard violations |")
    L.append("|---|---|:--:|---:|")
    for case_id, label, report in valid_rows:
        L.append(f"| {case_id} | {label} | "
                 f"{'yes' if report.passed else 'NO'} | "
                 f"{report.hard_violation_count} |")
    L.append("")

    L.append("## Violations by type")
    L.append("")
    L.append("| Code | Severity | Count |")
    L.append("|---|---|---:|")
    for code, count in sorted(by_type.items(), key=lambda kv: -kv[1]):
        sev = SEVERITY[ViolationCode(code)].value
        L.append(f"| `{code}` | {sev} | {count} |")
    L.append("")

    L.append("## Severity policy")
    L.append("")
    L.append("Hard violations block delivery. Each one is a case where a "
             "wrong answer is worse than no answer.")
    L.append("")
    L.append("| Code | Why it is HARD |")
    L.append("|---|---|")
    for code, rationale in HARD_RATIONALE.items():
        L.append(f"| `{code.value}` | {rationale} |")
    L.append("")
    soft = [c.value for c, s in SEVERITY.items() if s is Severity.SOFT]
    info = [c.value for c, s in SEVERITY.items() if s is Severity.INFO]
    L.append(f"SOFT (correctable on retry): {', '.join(f'`{c}`' for c in soft)}.")
    L.append("")
    L.append(f"INFO (logged, never blocks): {', '.join(f'`{c}`' for c in info)}.")
    L.append("")

    L.append("## Limitations")
    L.append("")
    L.append("- **Direction and causal checks match a fixed vocabulary.** A "
             "sentence that conveys a rise without using any of the rise words "
             "passes the direction check unexamined. This is deliberate — a "
             "semantic judge would be a second model whose errors nobody can "
             "audit — but it is a real ceiling, and paraphrase defeats it.")
    L.append("- **The numeric allowlist admits cohort figures as well as "
             "metric facts.** Both are frozen into the bundle and computed "
             "deterministically, so neither can be invented, but the allowlist "
             "is wider than `metric_facts` alone.")
    L.append("- **Structural integers 0-3 are allowed unconditionally**, so a "
             "narrative could state a wrong small count. No business figure in "
             "this system is a bare single digit, and requiring a metric fact "
             "for the `1` in `#1` would make every ranked list unverifiable.")
    L.append("- **Entitlement is checked against the frozen bundle**, which "
             "already excludes restricted sources. The check is a second line, "
             "not the primary control; the primary control is Stage 5 refusing "
             "the read at the gateway.")
    L.append("- **The advisory LLM judge (Part 13.2, check 10) is not built.** "
             "It is advisory by design and would require a model call, which "
             "this stage does not make.")
    L.append("- **No retry loop.** Part 6.4's failure ladder specifies one "
             "re-narration attempt before falling back to the template. There "
             "is nothing to re-narrate yet, so only the template exists.")
    L.append("")

    L.append("## Commands")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.run_verification_eval")
    L.append("```")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.demo_verification")
    L.append("```")
    L.append("")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
