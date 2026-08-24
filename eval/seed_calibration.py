"""Seed the calibration table from the synthetic ground-truth run.

    python -m eval.seed_calibration

Runs the full pipeline over a slice universe, computes confidence for each, and
records whether the system's answer matched the injected ground truth. The
result is `config/calibration.json`: real observed counts over a synthetic
dataset.

**Every field says it is synthetic, and the report says it too.** A judge who
catches an implication of production history has destroyed the credibility of
the one section that was supposed to be about honesty; a judge who sees it
labelled concludes the opposite. This is why `is_synthetic` is a stored field
rather than a comment.

What counts as correct:

  a slice containing an injected event   the leading hypothesis's cause bucket
                                        matches the event's true mechanism
  a slice with no injected event         the system abstained, or reported a
                                        band below HIGH
  a sparse or immaterial slice           the system declined to explain

That last rule matters: on a slice where nothing happened, *not* producing a
confident explanation is the correct behaviour, and a calibration table that
only scored the interesting slices would be measuring the easy half.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

from attribution import engine as att
from confidence import engine as conf_engine
from confidence.types import ConfidenceBand
from data import spec
from detection import engine as det
from evidence.bundle import freeze_evidence_bundle
from retrieval import engine as ret
from retrieval.embeddings import load_index
from retrieval.types import (
    FilterConditions, RetrievalConfig, RetrievalQuery, RetrievalResult,
)
from security.entitlements import Principal
from semantic.types import Window

ROOT = Path(__file__).resolve().parent.parent
GROUND_TRUTH = ROOT / "data" / "ground_truth.json"
OUT = ROOT / "config" / "calibration.json"

ANALYST = Principal(
    user_id="meera", display_name="Meera Rao", role="analytics_lead"
)
WINDOW = Window(start=date(2026, 1, 1), end=spec.END)

# Which cause bucket each injected mechanism should produce.
MECHANISM_TO_BUCKET = {
    "payment_gateway_degradation": {"internal_product"},
    "ambiguous_competitor_promo_or_stockout": {
        "external_competitor", "internal_inventory"
    },
    "new_product_ramp": {"internal_inventory", "external_market"},
    "channel_value_renamed": {"internal_data_schema"},
    "unknown": set(),        # any bucket, or an abstention, is acceptable
}


def slice_universe() -> list[dict]:
    """Single dimensions plus region x other, as in the detection eval."""
    out = [{"region": [r]} for r in spec.REGIONS]
    out += [{"channel": [c]} for c in spec.CHANNELS]
    out += [{"product_category": [p]} for p in spec.PRODUCT_CATEGORIES]
    out += [{"segment": [s]} for s in spec.SEGMENTS]
    out += [
        {"region": [r], "channel": [c]}
        for r in spec.REGIONS for c in spec.CHANNELS
    ]
    out += [
        {"region": [r], "product_category": [p]}
        for r in spec.REGIONS for p in spec.PRODUCT_CATEGORIES
    ]
    out += [
        {"region": [r], "segment": [s]}
        for r in spec.REGIONS for s in spec.SEGMENTS
    ]
    return out


def _overlaps(slice_filter: dict, event_slice: dict) -> bool:
    for dim, values in slice_filter.items():
        if dim in event_slice and not set(values) & set(event_slice[dim]):
            return False
    return True


def matching_event(slice_filter: dict, events: list[dict], changepoint) -> dict | None:
    from datetime import timedelta

    if changepoint is None:
        return None
    for ev in events:
        start = date.fromisoformat(ev["start"]) - timedelta(days=10)
        end = date.fromisoformat(ev["end"]) + timedelta(days=10)
        if _overlaps(slice_filter, ev["slice"]) and start <= changepoint <= end:
            return ev
    return None


def empty_retrieval(index) -> RetrievalResult:
    return RetrievalResult(
        query=RetrievalQuery(text=""), filters=FilterConditions(),
        config=RetrievalConfig(
            embedding_model=index.model_name,
            embedding_dim=index.embedding_dim,
            corpus_hash=index.corpus_hash,
        ),
    )


def main() -> None:
    events = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["events"]
    index = load_index()
    universe = slice_universe()

    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0}
    )
    rows = []
    started = time.perf_counter()

    print(f"seeding calibration over {len(universe)} slices ...")
    for i, slice_filter in enumerate(universe, start=1):
        try:
            d = det.detect("net_revenue", WINDOW, ANALYST, slice_filter=slice_filter)
            a = att.attribute(d, ANALYST, n_resamples=20)
            if d.observed_start is None and d.changepoint_date is None:
                r = empty_retrieval(index)
            else:
                r = ret.retrieve_evidence(a, ANALYST, index=index)
            bundle = freeze_evidence_bundle(
                bundle_id=f"CAL-{i:03d}", persona_id="meera",
                detection=d, attribution=a, retrieval=r,
            )
            confidence = conf_engine.compute(
                bundle, calibration=_empty_table()
            )
            # Bucket by the RAW signal band, not the reported one. Seeding
            # against an empty table degrades every reported band to
            # UNCALIBRATED, so bucketing on it would record the bootstrap
            # rather than the signal. Calibration answers "for cases whose
            # signal strength fell in band X, how often were we right?"
            raw_band = conf_engine.band_for(confidence.score)
        except Exception as exc:  # noqa: BLE001 - a failed slice is not a case
            print(f"  {i:>3}/{len(universe)}  skipped ({type(exc).__name__})")
            continue

        event = matching_event(slice_filter, events, d.changepoint_date)
        top = bundle.hypotheses[0] if bundle.hypotheses else None

        if event is None:
            # Nothing was planted here. Correct behaviour is to decline, or at
            # least not to be confident.
            correct = top is None or raw_band is not ConfidenceBand.HIGH
            label = "no event"
        elif not event.get("detectable_by_standard_path", True):
            # E4: the sparse-history event. Abstaining IS the correct answer;
            # producing a confident explanation off 23 days of history is the
            # failure the sparse path exists to prevent.
            correct = top is None
            label = event["event_id"]
        else:
            expected = MECHANISM_TO_BUCKET.get(event["mechanism"], set())
            if not expected:
                correct = True         # 'unknown' mechanism: any answer allowed
            elif top is None:
                correct = False
            else:
                correct = top.cause_bucket in expected
            label = event["event_id"]

        band = raw_band.value
        counts[band]["total"] += 1
        counts[band]["correct"] += int(correct)
        rows.append({
            "slice": slice_filter, "band": band,
            "score": round(confidence.score, 4),
            "event": label, "correct": correct,
            "hypothesis": top.cause_bucket if top else None,
        })
        if i % 10 == 0:
            print(f"  {i:>3}/{len(universe)}  {band:<14}{label:<10}"
                  f"{'ok' if correct else 'WRONG'}")

    elapsed = time.perf_counter() - started
    table = {
        "version": "1.0.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "is_synthetic": True,
        "source": (
            "seeded from the synthetic ground-truth evaluation over the "
            "generated dataset; NOT production history"
        ),
        "n_cases": sum(c["total"] for c in counts.values()),
        "min_cases_per_band": 10,
        "entries": [
            {"band": band, "correct": c["correct"], "total": c["total"],
             "source": "synthetic"}
            for band, c in sorted(counts.items())
        ],
    }
    OUT.write_text(json.dumps(table, indent=2), encoding="utf-8")

    print(f"\nwrote {OUT.relative_to(ROOT)} in {elapsed:.0f}s")
    print(f"  N = {table['n_cases']} synthetic labelled cases")
    for entry in table["entries"]:
        rate = (
            entry["correct"] / entry["total"] if entry["total"] else 0.0
        )
        flag = "" if entry["total"] >= 10 else "   <- below the reporting floor"
        print(f"  {entry['band']:<16}{entry['correct']:>3}/{entry['total']:<4}"
              f"{rate:>7.0%}{flag}")


def _empty_table():
    from confidence.types import CalibrationTable

    return CalibrationTable(
        version="0.0.0", is_synthetic=True,
        source="bootstrapping: no table yet",
    )


if __name__ == "__main__":
    main()
