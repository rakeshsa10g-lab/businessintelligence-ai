"""Recording feedback, and applying the two updates that are genuinely live.

JSONL append-only: a feedback log that can be rewritten is a feedback log
nobody can audit. The two live updates are counters — calibration and
`p_human` — and both are applied by recomputing from the whole log rather than
by mutating a running total, so a corrupted increment cannot accumulate.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from feedback.types import ArtifactUpdate, FeedbackEvent, FeedbackOutcome, ROUTING

DEFAULT_LOG = Path(__file__).resolve().parent.parent / "eval" / "feedback_log.jsonl"


def record(event: FeedbackEvent, path: Path | None = None) -> Path:
    """Append one event. Never rewrites history."""
    target = path or DEFAULT_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json() + "\n")
    return target


def read_all(path: Path | None = None) -> list[FeedbackEvent]:
    target = path or DEFAULT_LOG
    if not target.exists():
        return []
    events: list[FeedbackEvent] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(FeedbackEvent.model_validate_json(line))
    return events


def consumer_for(outcome: FeedbackOutcome) -> ArtifactUpdate:
    """Which artifact this outcome feeds. Every outcome names one."""
    return ROUTING[outcome]


# --------------------------------------------------------------------------
# the two live updates
# --------------------------------------------------------------------------
def calibration_counters(events: list[FeedbackEvent]) -> dict[str, dict[str, int]]:
    """(band, correct) counts from accepted and rejected events.

    Recomputed from the log rather than incremented, so a bad write cannot
    compound. This is the counter that makes the confidence display honest
    over time, and it needs no model at all.
    """
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0}
    )
    for e in events:
        if e.outcome not in (FeedbackOutcome.ACCEPTED, FeedbackOutcome.REJECTED):
            continue
        if not e.confidence_band:
            continue
        entry = counts[e.confidence_band]
        entry["total"] += 1
        if e.was_correct or e.outcome is FeedbackOutcome.ACCEPTED:
            entry["correct"] += 1
    return dict(counts)


def human_accuracy_from_feedback(
    events: list[FeedbackEvent],
) -> dict[str, tuple[int, int]]:
    """p_human per cause bucket, from escalated events an analyst resolved.

    Returns (correct, total) rather than a rate: a rate over two cases is not
    a rate, and the caller needs the denominator to decide whether to use it.
    """
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for e in events:
        if e.outcome is not FeedbackOutcome.ESCALATED or e.was_correct is None:
            continue
        bucket = e.note or "unknown"
        counts[bucket][1] += 1
        if e.was_correct:
            counts[bucket][0] += 1
    return {k: (v[0], v[1]) for k, v in counts.items()}


def coverage_gaps(events: list[FeedbackEvent], threshold: int = 5) -> dict[str, int]:
    """Sources named as missing, and how often.

    At the threshold a gap stops being an incident and becomes a roadmap item.
    """
    counter = Counter(
        e.missing_source for e in events
        if e.outcome is FeedbackOutcome.INSUFFICIENT_EVIDENCE and e.missing_source
    )
    return {source: n for source, n in counter.items() if n >= threshold}


def summary(events: list[FeedbackEvent]) -> dict:
    by_outcome = Counter(e.outcome.value for e in events)
    return {
        "n_events": len(events),
        "by_outcome": dict(by_outcome),
        "calibration_counters": calibration_counters(events),
        "human_accuracy": human_accuracy_from_feedback(events),
        "coverage_gaps": coverage_gaps(events),
        "live_updates": [
            o.value for o, u in ROUTING.items() if u.timing.value == "live"
        ],
        "batched_updates": [
            o.value for o, u in ROUTING.items() if u.timing.value == "batched"
        ],
    }
