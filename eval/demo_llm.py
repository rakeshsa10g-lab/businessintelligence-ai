"""The constrained narrator, end to end.

    python -m eval.demo_llm --scenario S1
    python -m eval.demo_llm --scenario S2
    python -m eval.demo_llm --scenario S3
    python -m eval.demo_llm --scenario S6
    python -m eval.demo_llm --scenario S1 --persona priya
    python -m eval.demo_llm --scenario S1 --prompt narration_v1_concise

With `ANTHROPIC_API_KEY` set, this calls the model. Without one it still runs:
the client returns a typed failure, the system falls back to the deterministic
template, and the output says so. That is the point — an application whose
behaviour depends on a model being reachable has made the model load-bearing.
"""

from __future__ import annotations

import argparse
import os
from datetime import date

from attribution import engine as att
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from llm.client import API_KEY_ENV, AnthropicClient, load_config
from llm.narrator import DeliveryMode, deliver_insight
from retrieval import engine as ret
from retrieval.embeddings import load_index
from security.entitlements import Principal
from semantic.types import Window
from verification.types import Severity

RULE = "=" * 78
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)

SCENARIOS = {
    "S1": ({"region": ["West"], "channel": ["Web", "Mobile App"]},
           date(2026, 7, 12), "high confidence, one clear explanation"),
    "S2": ({"region": ["South"], "product_category": ["Apparel"]},
           date(2026, 6, 2), "conflicting evidence, no winner permitted"),
    "S3": ({"region": ["East"], "segment": ["SMB"]},
           date(2026, 8, 5), "thin evidence"),
    "S4": ({"product_category": ["NewLaunch"]},
           None, "sparse history, must abstain"),
    "S6": ({"region": ["West"], "channel": ["Web", "Mobile App"]},
           date(2026, 7, 12), "ops lead, CRM notes withheld"),
    "S7": ({"channel": ["Marketplace"]},
           date(2026, 6, 14), "schema change"),
}

PERSONAS = {
    "meera": ("analytics_lead", None),
    "priya": ("ops_lead", "West"),
    "arjun": ("finance_director", None),
}


def build_bundle(scenario_id: str, persona_id: str, index):
    slice_filter, cause_date, _ = SCENARIOS[scenario_id]
    role, region = PERSONAS[persona_id]
    principal = Principal(
        user_id=persona_id, display_name=persona_id.title(),
        role=role, user_region=region,
    )
    d = det.detect(
        "net_revenue", WINDOW, principal, slice_filter=slice_filter,
        scenario_id=scenario_id,
    )
    a = att.attribute(d, principal, cause_date=cause_date, n_resamples=40)

    if d.changepoint_date is None and d.observed_start is None:
        from retrieval.types import (
            FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
        )
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

    return freeze_evidence_bundle(
        bundle_id=f"R-{scenario_id}-{persona_id}", persona_id=persona_id,
        detection=d, attribution=a, retrieval=r,
        history_days=23 if scenario_id == "S4" else 229,
        has_stable_baseline=scenario_id != "S4",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="S1", choices=sorted(SCENARIOS))
    parser.add_argument("--persona", default="meera", choices=sorted(PERSONAS))
    parser.add_argument("--prompt", default=None)
    args = parser.parse_args()

    cfg = load_config()
    index = load_index()
    bundle = build_bundle(args.scenario, args.persona, index)

    print(RULE)
    print(f"BUSINESSINTELLIGENCE.AI - NARRATION  [{args.scenario}]")
    print(f"  {SCENARIOS[args.scenario][2]}")
    print(RULE)
    print(f"bundle hash    {bundle.bundle_hash[:32]}")
    print(f"bundle status  {bundle.overall_status.value}")
    print(f"persona        {bundle.persona.display_name} ({bundle.persona.role})")
    print(f"model route    narrate -> {cfg['routes']['narrate']}")
    print(f"prompt         {args.prompt or cfg['prompts']['narration']}")
    key = os.environ.get(API_KEY_ENV)
    print(f"api key        {'present' if key else 'NOT SET - expect template mode'}")

    client = AnthropicClient() if key else None
    result = deliver_insight(bundle, client, prompt_version=args.prompt)

    print(f"\n{RULE}")
    print("NARRATIVE")
    print(RULE)
    print(f"\n  {result.narrative.headline}\n")
    for c in result.narrative.claims:
        print(f"  [{c.claim_id}] {c.claim_type.value}")
        print(f"      {c.text}")
        bits = []
        if c.metric_refs:
            bits.append(f"facts={list(c.metric_refs)}")
        if c.evidence_ids:
            bits.append(f"evidence={list(c.evidence_ids)}")
        if c.hypothesis_id:
            bits.append(f"hypothesis={c.hypothesis_id}")
        if c.lever_id:
            bits.append(f"lever={c.lever_id}")
        if bits:
            print(f"      {'  '.join(bits)}")
    for caveat in result.narrative.caveats:
        print(f"  CAVEAT  {caveat}")
    if result.narrative.recommendation_ids:
        print(f"  ACTIONS {list(result.narrative.recommendation_ids)}")

    print(f"\n{RULE}")
    print("GATE 2")
    print(RULE)
    r = result.report
    print(f"  {'PASSED' if r.passed else 'BLOCKED'}  "
          f"{r.checks_passed}/{len(r.checks_run)} checks, "
          f"{r.hard_violation_count} hard, {r.soft_violation_count} soft")
    for v in r.violations:
        if v.severity is not Severity.INFO:
            print(f"    {v}")

    print(f"\n{RULE}")
    print("DELIVERY")
    print(RULE)
    print(f"  mode           {result.mode.value}")
    print(f"  model calls    {result.telemetry.llm_calls}")
    print(f"  retries        {result.telemetry.retry_count}")
    if result.fallback_reason:
        print(f"  fallback why   {result.fallback_reason}")
    t = result.telemetry
    if t.llm_calls:
        print(f"  tokens         {t.total_input_tokens} in "
              f"({t.total_cached_tokens} cached) / {t.total_output_tokens} out")
        print(f"  latency        {t.total_latency_ms:.0f} ms model, "
              f"{t.total_wall_ms:.0f} ms wall")
        print(f"  est. cost      ${t.total_cost_usd:.4f}")
    else:
        print("  tokens         - (the model was not called)")
    print(f"  tools offered  {t.any_call_had_tools}")
    print(RULE)


if __name__ == "__main__":
    main()
