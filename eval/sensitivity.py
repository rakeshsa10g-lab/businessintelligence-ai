"""Sensitivity of the reported precision/recall to the two calibrated knobs.

A metric that only holds at one setting is a coincidence, not a result. This
sweeps the PELT penalty multiplier and the materiality relative floor around
their chosen values and reports whether the targets still hold.

Run:  python -m eval.sensitivity
"""

from __future__ import annotations

import io

from eval import run_detection_eval as ev
from semantic import registry

KPI = "net_revenue"


def _sweep_penalty(betas: list[float]) -> list[tuple]:
    out = []
    for b in betas:
        s = ev.evaluate(KPI, verbose=False, penalty=b)
        out.append((b, s["precision"], s["recall"], s["true_positives"],
                    s["false_positives"], s["events_recalled"]))
    return out


def _sweep_materiality(values: list[float]) -> list[tuple]:
    path = "semantic/kpis/net_revenue.yaml"
    original = io.open(path, encoding="utf-8").read()
    out = []
    try:
        for v in values:
            patched = original.replace(
                "  min_rel_effect_pct: 9.0", f"  min_rel_effect_pct: {v}"
            )
            io.open(path, "w", encoding="utf-8").write(patched)
            registry.reload()
            s = ev.evaluate(KPI, verbose=False)
            out.append((v, s["precision"], s["recall"], s["true_positives"],
                        s["false_positives"], s["events_recalled"]))
    finally:
        io.open(path, "w", encoding="utf-8").write(original)
        registry.reload()
    return out


def main() -> None:
    print("=" * 74)
    print("SENSITIVITY — targets: precision >= 0.85, recall >= 0.90")
    print("=" * 74)

    print("\nPELT penalty multiplier beta   (chosen: 1.0 = BIC)")
    print(f"{'beta':>6} {'prec':>7} {'recall':>7} {'TP':>4} {'FP':>4} {'events':>7}  ok")
    for b, p, r, tp, fp, er in _sweep_penalty([0.5, 0.75, 1.0, 1.5, 2.0, 3.0]):
        ok = "yes" if (p >= 0.85 and r >= 0.90) else "no"
        print(f"{b:>6} {p:>7.3f} {r:>7.3f} {tp:>4} {fp:>4} {er:>7}  {ok}")

    print("\nMateriality relative floor %   (chosen: 9.0 = p99 of event-free null)")
    print(f"{'pct':>6} {'prec':>7} {'recall':>7} {'TP':>4} {'FP':>4} {'events':>7}  ok")
    for v, p, r, tp, fp, er in _sweep_materiality([5.0, 7.0, 9.0, 11.0, 13.0]):
        ok = "yes" if (p >= 0.85 and r >= 0.90) else "no"
        print(f"{v:>6} {p:>7.3f} {r:>7.3f} {tp:>4} {fp:>4} {er:>7}  {ok}")
    print("=" * 74)


if __name__ == "__main__":
    main()
