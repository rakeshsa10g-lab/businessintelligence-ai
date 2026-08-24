"""LLM evaluation — Gate 2 as the correctness measure.

    python -m eval.run_llm_eval                 the full suite (70 generations)
    python -m eval.run_llm_eval --quick         3 per scenario, for a smoke test
    python -m eval.run_llm_eval --prompts       compare the three variants
    python -m eval.run_llm_eval --plan          print the cost estimate and exit

**This spends money.** The full suite is 70 generations plus retries against
the narration model; `--plan` prints the estimated cost from
`config/models.yaml` before anything is sent, and the run refuses to start
without `ANTHROPIC_API_KEY`.

The measure is the deterministic verifier, not a human reading the output and
finding it agreeable. "Sounds good" is not a metric — it is the thing this
whole architecture is built to distrust.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path

from eval.demo_llm import PERSONAS, SCENARIOS, build_bundle
from llm.client import API_KEY_ENV, AnthropicClient, load_config
from llm.narrator import DeliveryMode, deliver_insight
from llm.telemetry import append_jsonl
from retrieval.embeddings import load_index
from verification.types import Severity, ViolationCode

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval" / "llm_report.md"
TELEMETRY = ROOT / "eval" / "llm_telemetry.jsonl"

# scenario -> (persona, generations) per the Stage 8 brief
PLAN = {
    "S1": ("meera", 20),
    "S2": ("meera", 20),
    "S3": ("meera", 10),
    "S4": ("meera", 10),
    "S6": ("priya", 10),
}

PROMPT_VARIANTS = [
    "narration_v1_concise",
    "narration_v2_evidence_forward",
    "narration_v3_constrained",
]


def estimate_plan_cost(n_generations: int, cfg: dict) -> float:
    """Rough cost before spending anything, from the config's own prices."""
    from llm.client import estimate_cost_usd

    model = cfg["routes"]["narrate"]
    # ~3k input (measured payload) and ~800 output per generation, plus a
    # pessimistic 30% retry rate
    per_call = estimate_cost_usd(model, 3000, 800, 0, cfg)
    return per_call * n_generations * 1.3


def run_one(bundle, client, prompt_version: str | None) -> dict:
    started = time.perf_counter()
    result = deliver_insight(bundle, client, prompt_version=prompt_version)
    wall_ms = (time.perf_counter() - started) * 1000

    codes = Counter(
        v.code.value for v in result.report.violations
        if v.severity is Severity.HARD
    )
    return {
        "mode": result.mode.value,
        "delivered": result.delivered,
        "first_pass": result.mode is DeliveryMode.LLM_FIRST_PASS,
        "after_retry": result.mode is DeliveryMode.LLM_AFTER_RETRY,
        "template": result.mode is DeliveryMode.VERIFIED_TEMPLATE_MODE,
        "abstained": result.mode is DeliveryMode.ABSTAINED,
        "hard_violations": result.report.hard_violation_count,
        "violation_codes": dict(codes),
        "llm_calls": result.telemetry.llm_calls,
        "retries": result.telemetry.retry_count,
        "input_tokens": result.telemetry.total_input_tokens,
        "output_tokens": result.telemetry.total_output_tokens,
        "cached_tokens": result.telemetry.total_cached_tokens,
        "cost_usd": result.telemetry.total_cost_usd,
        "model_latency_ms": result.telemetry.total_latency_ms,
        "wall_ms": wall_ms,
        "n_claims": len(result.narrative.claims),
        "n_causal_claims": sum(
            1 for c in result.narrative.claims if c.claim_type.value == "causal"
        ),
        "n_hypotheses_referenced": len(
            {c.hypothesis_id for c in result.narrative.claims if c.hypothesis_id}
        ),
        "fallback_reason": result.fallback_reason,
        "telemetry": result.telemetry.to_dict(),
    }


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {}
    delivered = sum(r["delivered"] for r in rows)
    llm_rows = [r for r in rows if r["llm_calls"] > 0]
    latencies = [r["model_latency_ms"] for r in llm_rows] or [0.0]
    return {
        "n": n,
        "first_pass_rate": sum(r["first_pass"] for r in rows) / n,
        "after_retry_rate": sum(r["after_retry"] for r in rows) / n,
        "final_verified_rate": delivered / n,
        "template_fallback_rate": sum(r["template"] for r in rows) / n,
        "abstention_rate": sum(r["abstained"] for r in rows) / n,
        "retry_rate": sum(1 for r in rows if r["retries"]) / n,
        "hard_violations_delivered": sum(
            r["hard_violations"] for r in rows if r["delivered"]
        ),
        "mean_latency_ms": statistics.mean(latencies),
        "total_input_tokens": sum(r["input_tokens"] for r in rows),
        "total_output_tokens": sum(r["output_tokens"] for r in rows),
        "total_cost_usd": sum(r["cost_usd"] for r in rows),
        "cost_per_insight_usd": (
            sum(r["cost_usd"] for r in rows) / max(1, len(llm_rows))
        ),
    }


def violation_rates(rows: list[dict]) -> dict[str, float]:
    n = max(1, len(rows))
    counts: Counter = Counter()
    for r in rows:
        for code, count in r["violation_codes"].items():
            counts[code] += count
    return {code: counts[code] / n for code in sorted(counts)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="3 generations per scenario")
    parser.add_argument("--prompts", action="store_true",
                        help="compare the three prompt variants on S1 and S2")
    parser.add_argument("--plan", action="store_true",
                        help="print the cost estimate and exit")
    args = parser.parse_args()

    cfg = load_config()
    plan = {k: (p, 3 if args.quick else n) for k, (p, n) in PLAN.items()}
    total = sum(n for _, n in plan.values())
    if args.prompts:
        total += len(PROMPT_VARIANTS) * 6

    print("=" * 78)
    print("LLM EVALUATION")
    print("=" * 78)
    print(f"narration model   {cfg['routes']['narrate']}")
    print(f"prompt            {cfg['prompts']['narration']}")
    print(f"generations       {total}")
    print(f"estimated cost    ${estimate_plan_cost(total, cfg):.2f} "
          f"(from config/models.yaml, assumes a 30% retry rate)")

    if args.plan:
        print("\n--plan given; nothing was sent.")
        return

    if not os.environ.get(API_KEY_ENV):
        print(f"\n{API_KEY_ENV} is not set.")
        print("This suite measures a live model against Gate 2; without a key")
        print("every generation would fall back to the deterministic template")
        print("and the numbers would describe the fallback, not the model.")
        print("\nSet the key and re-run:")
        print("    export ANTHROPIC_API_KEY=sk-ant-...")
        print("    python -m eval.run_llm_eval --quick")
        raise SystemExit(1)

    index = load_index()
    client = AnthropicClient()
    all_rows: dict[str, list[dict]] = {}

    for scenario_id, (persona, n) in plan.items():
        bundle = build_bundle(scenario_id, persona, index)
        rows = []
        print(f"\n[{scenario_id}] {SCENARIOS[scenario_id][2]} "
              f"({persona}, {n} generations)")
        for i in range(n):
            row = run_one(bundle, client, None)
            rows.append(row)
            append_jsonl(
                {"scenario": scenario_id, "run": i, **row["telemetry"]},
                TELEMETRY,
            )
            print(f"  {i + 1:>3}/{n}  {row['mode']:<24}"
                  f"{row['llm_calls']} call(s)  "
                  f"{row['model_latency_ms']:>7.0f} ms  "
                  f"${row['cost_usd']:.4f}")
        all_rows[scenario_id] = rows

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"{'scenario':<10}{'first pass':>11}{'after retry':>12}"
          f"{'verified':>10}{'template':>10}{'abstain':>9}{'hard@deliver':>13}")
    for scenario_id, rows in all_rows.items():
        s = summarise(rows)
        print(f"{scenario_id:<10}{s['first_pass_rate']:>10.0%}"
              f"{s['after_retry_rate']:>12.0%}{s['final_verified_rate']:>10.0%}"
              f"{s['template_fallback_rate']:>10.0%}"
              f"{s['abstention_rate']:>9.0%}"
              f"{s['hard_violations_delivered']:>13}")

    flat = [r for rows in all_rows.values() for r in rows]
    overall = summarise(flat)
    print(f"\n  HARD VIOLATIONS REACHING DELIVERY: "
          f"{overall['hard_violations_delivered']}  (target 0)")
    print(f"  final verified rate:  {overall['final_verified_rate']:.0%}")
    print(f"  mean model latency:   {overall['mean_latency_ms']:.0f} ms")
    print(f"  total cost:           ${overall['total_cost_usd']:.4f}")
    print(f"  cost per insight:     ${overall['cost_per_insight_usd']:.4f}")

    print("\n  violation rate by type (per generation)")
    for code, rate in violation_rates(flat).items():
        print(f"    {code:<38}{rate:.3f}")

    prompt_rows = {}
    if args.prompts:
        print("\n" + "=" * 78)
        print("PROMPT VARIANTS")
        print("=" * 78)
        print(f"{'variant':<34}{'first pass':>11}{'verified':>10}"
              f"{'latency':>10}{'cost':>10}")
        for variant in PROMPT_VARIANTS:
            rows = []
            for scenario_id in ("S1", "S2"):
                bundle = build_bundle(scenario_id, PLAN[scenario_id][0], index)
                for _ in range(3):
                    rows.append(run_one(bundle, client, variant))
            s = summarise(rows)
            prompt_rows[variant] = s
            print(f"{variant:<34}{s['first_pass_rate']:>10.0%}"
                  f"{s['final_verified_rate']:>10.0%}"
                  f"{s['mean_latency_ms']:>9.0f}ms"
                  f"${s['total_cost_usd']:>9.4f}")

    write_report(all_rows, overall, violation_rates(flat), prompt_rows, cfg)
    print(f"\nwrote {REPORT.relative_to(ROOT)}")


def write_report(all_rows, overall, rates, prompt_rows, cfg) -> None:
    L = ["# Stage 8 — LLM narration evaluation", ""]
    L.append("Generated by `python -m eval.run_llm_eval`.")
    L.append("")
    L.append(f"Narration model `{cfg['routes']['narrate']}`, prompt "
             f"`{cfg['prompts']['narration']}`, temperature "
             f"{cfg['generation']['temperature']}.")
    L.append("")
    L.append("Correctness is measured by the deterministic verifier, not by "
             "reading the output and finding it agreeable.")
    L.append("")
    L.append("## Headline")
    L.append("")
    L.append("| Metric | Value | Target |")
    L.append("|---|---:|---:|")
    L.append(f"| **Hard violations reaching delivery** | "
             f"**{overall['hard_violations_delivered']}** | 0 |")
    L.append(f"| **Final verified output rate** | "
             f"**{overall['final_verified_rate']:.0%}** | 100% |")
    L.append(f"| First-pass verification rate | {overall['first_pass_rate']:.0%} | |")
    L.append(f"| Verified after retry | {overall['after_retry_rate']:.0%} | |")
    L.append(f"| Template fallback rate | {overall['template_fallback_rate']:.0%} | |")
    L.append(f"| Abstention rate | {overall['abstention_rate']:.0%} | |")
    L.append(f"| Mean model latency | {overall['mean_latency_ms']:.0f} ms | |")
    L.append(f"| Cost per insight | ${overall['cost_per_insight_usd']:.4f} | |")
    L.append("")

    L.append("## Per scenario")
    L.append("")
    L.append("| Scenario | n | First pass | After retry | Verified | Template | Abstained | Hard@delivery |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for scenario_id, rows in all_rows.items():
        s = summarise(rows)
        L.append(f"| {scenario_id} | {s['n']} | {s['first_pass_rate']:.0%} | "
                 f"{s['after_retry_rate']:.0%} | {s['final_verified_rate']:.0%} | "
                 f"{s['template_fallback_rate']:.0%} | "
                 f"{s['abstention_rate']:.0%} | "
                 f"{s['hard_violations_delivered']} |")
    L.append("")

    L.append("## Violation rate by type")
    L.append("")
    L.append("Per generation, across every scenario. These are the model's "
             "attempts that Gate 2 caught — not failures that reached anyone.")
    L.append("")
    L.append("| Code | Rate |")
    L.append("|---|---:|")
    for code, rate in rates.items():
        L.append(f"| `{code}` | {rate:.3f} |")
    if not rates:
        L.append("| (none) | 0.000 |")
    L.append("")

    if prompt_rows:
        L.append("## Prompt variants")
        L.append("")
        L.append("Selected on measured verification rate, latency and cost — "
                 "not on which wording reads better.")
        L.append("")
        L.append("| Variant | First pass | Verified | Mean latency | Cost |")
        L.append("|---|---:|---:|---:|---:|")
        for variant, s in prompt_rows.items():
            L.append(f"| `{variant}` | {s['first_pass_rate']:.0%} | "
                     f"{s['final_verified_rate']:.0%} | "
                     f"{s['mean_latency_ms']:.0f} ms | "
                     f"${s['total_cost_usd']:.4f} |")
        L.append("")

    L.append("## Reading these numbers")
    L.append("")
    L.append("- **Hard violations reaching delivery** is the only number that "
             "must be zero. Gate 2 blocks before delivery, so a non-zero value "
             "would mean the gate itself is broken.")
    L.append("- **Template fallback is not a failure.** It is the system "
             "choosing a less fluent, completely faithful answer, and it is "
             "labelled as such in the output.")
    L.append("- **Abstention rate on S3 and S4 should be high.** Those bundles "
             "have nothing to explain, and the model is never called for them "
             "— `llm_calls = 0` in the telemetry.")
    L.append("")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
