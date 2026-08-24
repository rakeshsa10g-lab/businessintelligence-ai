"""Stage 9 scenario evaluation.

    python -m eval.run_recommendation_eval

For each scenario: the hypothesis, the recommendation, the computed impact, the
confidence state, the automate/defer/abstain decision and the monitoring plan.

Nothing here calls a model. Every figure is computed or looked up, which is the
property the whole stage exists to establish.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from attribution import engine as att
from confidence import engine as conf_engine
from data import spec
from deferral import engine as defer_engine
from deferral.types import DeferralOutcome
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from recommendation import engine as rec_engine
from retrieval import engine as ret
from retrieval.embeddings import load_index
from retrieval.types import (
    FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
)
from security.entitlements import Principal
from semantic.types import Window

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval" / "recommendation_report.md"
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)

PERSONAS = {
    "meera": ("analytics_lead", None),
    "priya": ("ops_lead", "West"),
    "arjun": ("finance_director", None),
}

SCENARIOS = [
    ("S1", "West revenue - high confidence",
     {"region": ["West"], "channel": ["Web", "Mobile App"]},
     date(2026, 7, 12), "meera"),
    ("S2", "South x Apparel - conflicting evidence",
     {"region": ["South"], "product_category": ["Apparel"]},
     date(2026, 6, 2), "meera"),
    ("S3", "East x SMB - thin evidence",
     {"region": ["East"], "segment": ["SMB"]},
     date(2026, 8, 5), "meera"),
    ("S4", "NewLaunch - sparse history",
     {"product_category": ["NewLaunch"]}, None, "meera"),
    ("S5a", "West - operations lead",
     {"region": ["West"], "channel": ["Web", "Mobile App"]},
     date(2026, 7, 12), "priya"),
    ("S5b", "West - finance director",
     {"region": ["West"], "channel": ["Web", "Mobile App"]},
     date(2026, 7, 12), "arjun"),
    ("S6", "West - ops lead, CRM withheld",
     {"region": ["West"], "channel": ["Web", "Mobile App"]},
     date(2026, 7, 12), "priya"),
    ("S7", "Marketplace rename - schema change",
     {"channel": ["Marketplace"]}, date(2026, 6, 14), "meera"),
]


# --------------------------------------------------------------------------
# One vocabulary for the decision, used by both the table and the detail, so
# the two cannot drift apart.
# --------------------------------------------------------------------------
_SCOPE_LABEL = {
    "none": "—",
    "raise_request": "raise request",
    "execute": "execute action",
}

_SCOPE_SENTENCE = {
    "none": (
        "nothing is automated; no action is taken on the persona's behalf"
    ),
    "raise_request": (
        "the **request** is raised automatically. The technical remediation "
        "itself is NOT performed - approval rests with the lever's owner role, "
        "and no lever in this catalogue authorises the system to execute a "
        "rollback"
    ),
    "execute": (
        "the action itself is taken, because this persona holds approval "
        "rights on this lever"
    ),
}


def _scope_label(scope: str) -> str:
    return _SCOPE_LABEL[scope]


def _scope_sentence(scope: str) -> str:
    return _SCOPE_SENTENCE[scope]


def run(scenario_id, label, slice_filter, cause_date, persona_id, index):
    role, region = PERSONAS[persona_id]
    principal = Principal(
        user_id=persona_id, display_name=persona_id.title(),
        role=role, user_region=region,
    )
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario_id,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=30)
    if d.observed_start is None and d.changepoint_date is None:
        r = RetrievalResult(
            query=RetrievalQuery(text=""), filters=FilterConditions(),
            config=RetrievalConfig(
                embedding_model=index.model_name,
                embedding_dim=index.embedding_dim,
                corpus_hash=index.corpus_hash,
            ),
        )
    else:
        r = ret.retrieve_evidence(a, principal, index=index)

    bundle = freeze_evidence_bundle(
        bundle_id=f"R-{scenario_id}", persona_id=persona_id,
        detection=d, attribution=a, retrieval=r,
        history_days=23 if scenario_id == "S4" else 229,
        has_stable_baseline=scenario_id != "S4",
    )
    confidence = conf_engine.compute(bundle)
    recs = rec_engine.recommend(bundle, confidence)
    decision = defer_engine.decide(bundle, confidence, recs)
    packet = (
        defer_engine.build_analyst_packet(bundle, confidence, decision, recs)
        if decision.review else None
    )
    return bundle, confidence, recs, decision, packet


def main() -> None:
    index = load_index()
    rows = []
    rule = "=" * 78

    print(rule)
    print("STAGE 9 - RECOMMENDATION, CONFIDENCE, DEFERRAL")
    print(rule)

    for scenario_id, label, slice_filter, cause_date, persona in SCENARIOS:
        bundle, confidence, recs, decision, packet = run(
            scenario_id, label, slice_filter, cause_date, persona, index
        )
        top = bundle.hypotheses[0] if bundle.hypotheses else None
        primary = recs.primary

        print(f"\n{scenario_id}  {label}   [{persona} / {bundle.persona.role}]")
        print(f"  hypothesis     "
              f"{top.statement if top else '(none - the system declined)'}")
        if top:
            print(f"                 {top.status.value}, "
                  f"{top.evidence_count} distinct document(s)")
        print(f"  confidence     {confidence.render()}")
        print(f"                 score {confidence.score:.3f}, "
              f"coverage {confidence.coverage.value}")
        if primary:
            print(f"  recommendation [{primary.lever_id}] {primary.lever_name}")
            print(f"                 owner {primary.owner_role}, "
                  f"persona may {primary.persona_right.value}, "
                  f"urgency {primary.urgency}")
            print(f"  impact         {primary.expected_impact.render()}")
            print(f"  monitoring     {primary.monitoring.render()}")
        else:
            print("  recommendation (none)")
            for lever_id, reason in recs.rejected_lever_ids[:2]:
                print(f"                 {lever_id} rejected: {reason[:60]}")
        print(f"  decision       {decision.render()[:110]}")
        if decision.model_arm:
            print(f"                 {decision.model_arm.render()}")
            print(f"                 {decision.human_arm.render()}")
        if packet:
            print(f"  packet         {packet.packet_id}, "
                  f"{len(packet.hypotheses)} hypotheses, "
                  f"{len(packet.supporting_evidence)} evidence, "
                  f"~{packet.estimated_review_minutes} min review")

        rows.append({
            "scenario": scenario_id, "label": label, "persona": persona,
            "role": bundle.persona.role,
            "hypothesis": top.statement if top else None,
            "status": top.status.value if top else bundle.overall_status.value,
            "confidence_band": confidence.band.value,
            "confidence_score": round(confidence.score, 3),
            "confidence_render": confidence.render(),
            "coverage": confidence.coverage.value,
            "calibration_state": (
                f"{confidence.calibration.correct}/"
                f"{confidence.calibration.total}"
                if getattr(confidence, "calibration", None) else "none"
            ),
            "lever_id": primary.lever_id if primary else None,
            "lever_name": primary.lever_name if primary else None,
            "owner": primary.owner_role if primary else None,
            "persona_right": primary.persona_right.value if primary else None,
            "impact": primary.expected_impact.render() if primary else None,
            "impact_low": primary.expected_impact.low if primary else None,
            "impact_high": primary.expected_impact.high if primary else None,
            "monitoring": primary.monitoring.render() if primary else None,
            "outcome": decision.outcome.value,
            "automation_scope": decision.automation_scope.value,
            "withheld_count": bundle.security_context.withheld_item_count,
            "withheld_sources": list(bundle.security_context.withheld_source_ids),
            "abstention_reason": decision.abstention_reason.value,
            "rationale": decision.rationale,
            "model_loss": decision.expected_model_loss,
            "human_loss": decision.expected_human_loss,
            "has_packet": packet is not None,
        })

    outcomes = {r["outcome"] for r in rows}
    print(f"\n{rule}")
    print(f"outcomes present: {', '.join(sorted(outcomes))}")
    for needed in ("automate", "review", "abstain"):
        print(f"  {needed:<10}{'yes' if needed in outcomes else 'NO'}")
    print(rule)

    write_report(rows)
    print(f"\nwrote {REPORT.relative_to(ROOT)}")


def write_report(rows) -> None:
    table = conf_engine.load_calibration()
    conf_cfg = conf_engine.load_config()
    policy = defer_engine.load_policy()

    L = ["# Stage 9 — recommendation, confidence and deferral", ""]
    L.append("Generated by `python -m eval.run_recommendation_eval`. "
             "No model is called anywhere in this stage.")
    L.append("")

    L.append("## Scenario results")
    L.append("")
    L.append("This table is the single authoritative statement of each "
             "scenario's terminal decision. Any other description of these "
             "outcomes that disagrees with it is stale.")
    L.append("")
    L.append("| Scenario | Persona | Confidence | Calibration | Recommendation "
             "| Scope | Decision | State | Withheld |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(
            f"| {r['scenario']} | {r['role']} | "
            f"{r['confidence_band']} ({r['confidence_score']:.2f}) | "
            f"{r['calibration_state']} | "
            f"{r['lever_id'] or '—'} | "
            f"{_scope_label(r['automation_scope'])} | "
            f"**{r['outcome']}** | "
            f"{r['abstention_reason'] if r['abstention_reason'] != 'none' else '—'} | "
            f"{r['withheld_count'] or '—'} |"
        )
    L.append("")

    L.append("### Detail")
    L.append("")
    for r in rows:
        L.append(f"**{r['scenario']} — {r['label']}** ({r['role']})")
        L.append("")
        L.append(f"- hypothesis: {r['hypothesis'] or '(none)'} "
                 f"[{r['status']}]")
        L.append(f"- confidence: {r['confidence_render']}")
        if r["lever_id"]:
            L.append(f"- recommendation: `{r['lever_id']}` {r['lever_name']}, "
                     f"owner {r['owner']}, persona may {r['persona_right']}")
            L.append(f"- expected impact: {r['impact']}")
            L.append(f"- monitoring: {r['monitoring']}")
        else:
            L.append("- recommendation: none")
        L.append(f"- decision: **{r['outcome']}** — {r['rationale']}")
        L.append(f"- automation scope: {_scope_sentence(r['automation_scope'])}")
        if r["model_loss"]:
            L.append(f"- expected loss: model {r['model_loss']:,.0f} INR vs "
                     f"human+review {r['human_loss']:,.0f} INR")
        if r["abstention_reason"] != "none":
            # A review is not an abstention. The same enum names the open
            # question in both cases; only in the abstain case is it a reason
            # for declining.
            word = ("abstention reason" if r["outcome"] == "abstain"
                    else "open question for the reviewer")
            L.append(f"- {word}: `{r['abstention_reason']}`")
        if r["withheld_count"]:
            L.append(f"- entitlement: {r['withheld_count']} item(s) withheld "
                     f"from {', '.join(r['withheld_sources'])} for role "
                     f"`{r['role']}`; counted, never silently dropped")
        else:
            L.append(f"- entitlement: nothing withheld for role `{r['role']}`")
        L.append("")

    L.append("## Confidence")
    L.append("")
    L.append(f"Config `{conf_cfg['version']}`. Six weighted components summing "
             f"to 1.0, scaled by a contradiction multiplier, then mapped to a "
             f"band and a calibration lookup.")
    L.append("")
    L.append("| Component | Weight |")
    L.append("|---|---:|")
    for name, weight in sorted(conf_cfg["weights"].items()):
        L.append(f"| {name} | {weight:.2f} |")
    L.append("")
    L.append("Part 13.4 weights `(1 - p_value)` at 0.20. That p-value is the "
             "Welch test on the PELT-selected window, which ADR-017 showed is "
             "a post-selection statistic reading p < 0.001 on pure noise. "
             "Bootstrap robustness replaces it; the Welch value is carried as "
             "diagnostic metadata and scores nothing.")
    L.append("")

    L.append("## Calibration")
    L.append("")
    L.append(f"**Synthetic.** Seeded from {table.n_cases} labelled cases in "
             f"the ground-truth run over the generated dataset. "
             f"**Not production history.**")
    L.append("")
    L.append("| Band | Correct | Total | Observed | Used in arithmetic | Reportable |")
    L.append("|---|---:|---:|---:|---:|:--:|")
    for e in table.entries:
        reportable = e.total >= table.min_cases_per_band
        L.append(
            f"| {e.band.value} | {e.correct} | {e.total} | "
            f"{(e.accuracy or 0):.0%} | "
            f"{(e.estimated_accuracy or 0):.3f} | "
            f"{'yes' if reportable else 'no - UNCALIBRATED'} |"
        )
    L.append("")
    L.append("The two accuracy columns differ on purpose. The observed rate is "
             "what was seen and is what a reader is shown. The arithmetic uses "
             "a Laplace-smoothed estimate, because 12 correct out of 12 is not "
             "evidence of a 100% success rate — it is evidence that no failure "
             "has been observed yet, and feeding 1.0 into "
             "`(1 - p_model) x cost` makes the model's expected loss "
             "identically zero at every decision value, which silently turns "
             "the cost-sensitive rule into 'always automate'.")
    L.append("")
    L.append(f"Bands below {table.min_cases_per_band} observed cases report "
             f"`UNCALIBRATED` rather than a quoted rate. On this seed that is "
             f"MEDIUM and LOW — the system says it does not know how often a "
             f"medium call has been right, because it genuinely does not.")
    L.append("")

    L.append("## Deferral")
    L.append("")
    L.append(f"Policy `{policy['version']}`. The rule is not "
             f"`confidence < 0.7 -> human`:")
    L.append("")
    L.append("```")
    L.append("E[loss | model] = (1 - p_model) x cost_of_error")
    L.append("E[loss | human] = (1 - p_human) x cost_of_error + review_cost")
    L.append("defer  <=>  E[loss | model] >= E[loss | human]")
    L.append("```")
    L.append("")
    L.append(f"Review cost is analyst time "
             f"({policy['review']['analyst_hourly_inr']:,} INR/h x "
             f"{policy['review']['estimated_review_hours']} h) plus the delay "
             f"cost on a live incident "
             f"({policy['review']['delay_cost_per_hour_inr']:,} INR/h x "
             f"{policy['review']['delay_hours_if_deferred']} h).")
    L.append("")
    L.append("These guardrails override the arithmetic, because expected-loss "
             "reasoning is sound on average and these are the cases where the "
             "average is the wrong frame:")
    L.append("")
    L.append(f"- **never automated**: "
             f"{', '.join(f'`{l}`' for l in policy['overrides']['never_automate_lever_ids'])} "
             f"— the asymmetry between a wrong action and a delayed one is not "
             f"captured by one cost-of-error figure")
    # ADR-027 rule 1: read the flag, do not paraphrase it. The earlier text
    # described an "approval rights" guardrail that the config had already
    # replaced, and only the hand-written sentence was wrong.
    if policy["overrides"].get("require_persona_any_rights"):
        L.append("- **no rights, no automation** "
                 "(`require_persona_any_rights: true`): a persona with neither "
                 "approval nor request rights on a lever never has it "
                 "automated on their behalf. Request rights automate the "
                 "*request*; only approval rights would automate the action")
    L.append(f"- **at or below `"
             f"{policy['overrides'].get('abstain_at_or_below')}` the system "
             f"abstains** rather than deferring: there is nothing for a "
             f"reviewer to review")
    L.append("- **UNCALIBRATED always defers**: with no observed hit rate there "
             "is no `p_model` to put in the comparison")
    L.append("")

    L.append("")
    L.append("### What \"automate\" is permitted to mean")
    L.append("")
    L.append("`automate` is not a single privilege. It is bounded by the "
             "persona's rights on the specific lever, and the bound is "
             "recorded on the decision as `automation_scope`:")
    L.append("")
    L.append("| Scope | The system may | The system may not |")
    L.append("|---|---|---|")
    L.append("| `raise_request` | raise the request with the owning role | "
             "perform the remediation |")
    L.append("| `execute` | take the action itself | act outside the lever's "
             "`action_template` |")
    L.append("| `none` | nothing | anything |")
    L.append("")
    L.append("For `L_GATEWAY_ESCALATE` specifically, every persona in this "
             "system (`ops_lead`, `analytics_lead`, `finance_director`) holds "
             "**request** rights only - `can_approve` is `[engineering_lead, "
             "cto]`, and neither is a persona the system runs as. So the "
             "automated act is *raising an escalation with Engineering*. "
             "Rolling back the release is a different lever, "
             "`L_CHECKOUT_ROLLBACK`, and it is unreachable by automation "
             "through three independent guards: it is on the "
             "`never_automate_lever_ids` list, no persona can approve it, and "
             "it requires a licensed causal claim. **No lever in this "
             "catalogue authorises the system to execute a technical "
             "remediation.** Permitting one would require a new lever, "
             "reviewed as such.")
    L.append("")
    L.append("## Abstention states")
    L.append("")
    from deferral.types import ABSTENTION_REMEDY, AbstentionReason

    L.append("| State | Remedy |")
    L.append("|---|---|")
    for reason in AbstentionReason:
        if reason is AbstentionReason.NONE:
            continue
        L.append(f"| `{reason.value}` | {ABSTENTION_REMEDY[reason]} |")
    L.append("")
    L.append("Six states rather than one, because each has a different "
             "remedy. A reader told *why* the system declined can act; a "
             "reader told only *that* it declined cannot.")
    L.append("")

    L.append("## Feedback routing")
    L.append("")
    from feedback.types import ROUTING

    L.append("| Outcome | Artifact updated | Timing | Visible effect |")
    L.append("|---|---|---|---|")
    for outcome, update in ROUTING.items():
        L.append(f"| `{outcome.value}` | `{update.artifact}` | "
                 f"{update.timing.value} | {update.visible_effect} |")
    L.append("")
    L.append("Two outcomes update live because both are counters and neither "
             "needs a model. The other three accumulate and are applied on "
             "human review. No fine-tuning, no auto-applied prompt changes, no "
             "unbounded weight drift — saying so is a credibility gain rather "
             "than a gap.")
    L.append("")

    L.append("## Limitations")
    L.append("")
    L.append(f"- **The calibration set is synthetic and small** "
             f"({table.n_cases} cases, {sum(1 for e in table.entries if e.total >= 10)} "
             f"band(s) above the reporting floor). It measures this system on "
             f"this generated dataset and says nothing about production "
             f"accuracy.")
    L.append("- **HIGH at 12/12 is not a 100% success rate.** It is a small "
             "sample with no observed failure, which is why the arithmetic "
             "smooths it and why the displayed text shows the counts.")
    L.append("- **`p_human` is seeded, not measured.** The values in "
             "`config/deferral.yaml` are estimates that the `escalated` "
             "feedback outcome would refine; until analysts have resolved real "
             "escalations, the human arm of the comparison rests on an "
             "assumption.")
    L.append("- **Decision values are illustrative.** The rupee figures for "
             "what a wrong call costs each persona are plausible placeholders, "
             "not measured business impact, and they move the automate/defer "
             "boundary directly.")
    L.append("- **S6 is not an independent entitlement test.** S5a and S6 run "
             "the same KPI, slice, window and persona, so they produce "
             "identical decisions by construction. The CRM note is withheld "
             "in both, because withholding is a property of the *role*, not "
             "of the scenario - which is the correct behaviour, but it means "
             "S6 demonstrates nothing that S5a does not. The contrast worth "
             "reading is S5a/S6 (`ops_lead`, 1 item withheld) against S1 and "
             "S5b (`analytics_lead`, `finance_director`, nothing withheld) on "
             "the same underlying event.")
    L.append("- **Elasticity impact is a fraction, not a fitted model.** "
             "`elasticity_estimate` currently applies a configured recovery "
             "fraction to the measured movement rather than fitting a real "
             "price-response curve; the range is wider to reflect that, and "
             "the method is named in the output.")
    L.append("")

    L.append("## Commands")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.run_recommendation_eval")
    L.append("```")
    L.append("")
    L.append("```bash")
    L.append("python -m eval.seed_calibration")
    L.append("```")
    L.append("")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
