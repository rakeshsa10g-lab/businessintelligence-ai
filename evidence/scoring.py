"""Deterministic hypothesis scoring (Architecture Part 10.5; ADR-022).

Explicit, configurable, versioned, deterministic, testable — in that order of
importance. No model here, opaque or otherwise, and no literal weight in this
file: every number comes from `config/scoring.yaml`, so a reviewer can change a
weight, re-run, and watch the ranking move without reading a line of Python.

    score = movement_confidence x evidence_fit x contradiction_multiplier

**Why a product of two parts rather than one weighted sum.** Part 10.5's
formula assumes competing hypotheses differ in contribution — true when they
are different drivers or slices. Ours are competing cause buckets for one
driver and one slice, and for those, contribution, robustness, the
counterfactual, temporal precedence and surprise are all properties of the
*movement*: every hypothesis about it inherits them identically. Measured on
Scenario 1, five of six components had a spread of exactly 0.000 and 80% of the
weight was a constant, which turned a textbook high-confidence case into a
three-way tie. Separating the two questions and multiplying fixes it, and the
product is the right operator because both must hold.

**Contradiction multiplies, it does not subtract.** With subtraction a
hypothesis with a large enough evidence base absorbs any amount of
disconfirming evidence and still ranks first. It is floored, so a contradicted
hypothesis is demoted and still shown.

**Evidence counts DISTINCT documents and saturates.** Thirty copies of one
ticket are one finding; the cohort roll-up carries the volume.

**The Welch p-value is not a scoring input.** Stage 3 established that the
event window is selected to maximise displacement, so it is a post-selection
statistic reading p < 0.001 on pure noise (ADR-017). It is carried as
diagnostic metadata and scores nothing; bootstrap robustness takes its place.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "scoring.yaml"


class ScoringError(ValueError):
    """The scoring configuration is unusable."""


@functools.lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict:
    """Load and validate the scoring weights."""
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise ScoringError(f"no scoring configuration at {p}")
    config = yaml.safe_load(p.read_text(encoding="utf-8"))

    for key in ("version", "movement_confidence", "evidence_fit",
                "contradiction", "separation"):
        if key not in config:
            raise ScoringError(f"scoring config is missing '{key}'")

    for block in ("movement_confidence", "evidence_fit"):
        weights = {
            k: v for k, v in config[block].items() if isinstance(v, float)
        }
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ScoringError(
                f"'{block}' weights sum to {total}, not 1.0. A weighted mean "
                f"whose weights do not sum to one produces scores that are "
                f"not comparable across configuration versions."
            )
    return config


def reload_config() -> None:
    load_config.cache_clear()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _weights(block: dict) -> dict[str, float]:
    return {k: v for k, v in block.items() if isinstance(v, float)}


# --------------------------------------------------------------------------
# movement confidence
# --------------------------------------------------------------------------
def movement_confidence(
    *,
    contribution_share: float,
    surprise_normalised: float,
    robustness_score: float,
    temporal_precedence: bool,
    counterfactual_passed: bool,
    config: dict | None = None,
) -> tuple[float, dict[str, float]]:
    """Is this movement real, material and localised?

    Identical for every hypothesis about one movement, which is exactly why it
    is computed once and multiplied in rather than summed per hypothesis.
    """
    cfg = config or load_config()
    weights = _weights(cfg["movement_confidence"])

    components = {
        "contribution": _clamp(abs(contribution_share)),
        "statistical_strength": _clamp(surprise_normalised),
        "robustness": _clamp(robustness_score),
        "temporal_precedence": 1.0 if temporal_precedence else 0.0,
        "counterfactual": 1.0 if counterfactual_passed else 0.0,
    }
    missing = set(weights) - set(components)
    if missing:
        raise ScoringError(
            f"movement_confidence weights {sorted(missing)} have no computed "
            f"component; add the component or remove the weight."
        )
    score = sum(weights[k] * v for k, v in components.items())
    return _clamp(score), components


# --------------------------------------------------------------------------
# evidence fit
# --------------------------------------------------------------------------
def evidence_fit(
    *,
    bucket_alignment: float,
    distinct_documents: int,
    source_types: int,
    cohort_signal: float,
    temporal_tightness: float,
    config: dict | None = None,
) -> tuple[float, dict[str, float]]:
    """How well does THIS explanation fit the evidence? The discriminating part."""
    cfg = config or load_config()
    block = cfg["evidence_fit"]
    weights = _weights(block)

    components = {
        "bucket_alignment": _clamp(bucket_alignment),
        "distinct_documents": _clamp(
            distinct_documents / max(1, block["max_distinct_documents"])
        ),
        "source_diversity": _clamp(
            source_types / max(1, block["max_source_types"])
        ),
        "cohort_signal": _clamp(cohort_signal),
        "temporal_tightness": _clamp(temporal_tightness),
    }
    missing = set(weights) - set(components)
    if missing:
        raise ScoringError(
            f"evidence_fit weights {sorted(missing)} have no computed "
            f"component; add the component or remove the weight."
        )
    score = sum(weights[k] * v for k, v in components.items())
    return _clamp(score), components


def contradiction_multiplier(
    signals: list[tuple[str, float]], config: dict | None = None
) -> float:
    """Scale the score down by the weight of disconfirming evidence."""
    cfg = (config or load_config())["contradiction"]
    penalty = sum(cfg["penalty_per_signal"] * _clamp(s) for _, s in signals)
    penalty = min(penalty, cfg["max_penalty"])
    return 1.0 - penalty


# --------------------------------------------------------------------------
# the score
# --------------------------------------------------------------------------
def score_hypothesis(
    *,
    contribution_share: float,
    surprise_normalised: float,
    robustness_score: float,
    temporal_precedence: bool,
    counterfactual_passed: bool,
    bucket_alignment: float,
    distinct_documents: int,
    source_types: int,
    cohort_signal: float,
    temporal_tightness: float,
    contradiction_signals: list[tuple[str, float]],
    config: dict | None = None,
) -> tuple[float, dict]:
    """One hypothesis score plus the full breakdown.

    Deterministic: identical inputs and identical configuration always give an
    identical score, with no randomness and no ordering dependence.
    """
    cfg = config or load_config()

    confidence, conf_parts = movement_confidence(
        contribution_share=contribution_share,
        surprise_normalised=surprise_normalised,
        robustness_score=robustness_score,
        temporal_precedence=temporal_precedence,
        counterfactual_passed=counterfactual_passed,
        config=cfg,
    )
    fit, fit_parts = evidence_fit(
        bucket_alignment=bucket_alignment,
        distinct_documents=distinct_documents,
        source_types=source_types,
        cohort_signal=cohort_signal,
        temporal_tightness=temporal_tightness,
        config=cfg,
    )
    multiplier = contradiction_multiplier(contradiction_signals, cfg)
    final = _clamp(confidence * fit * multiplier)

    components = {f"movement.{k}": v for k, v in conf_parts.items()}
    components.update({f"evidence.{k}": v for k, v in fit_parts.items()})

    breakdown = {
        "components": tuple(sorted(components.items())),
        "weighted": (
            ("movement_confidence", confidence),
            ("evidence_fit", fit),
        ),
        "weighted_sum": confidence * fit,
        "contradiction_multiplier": multiplier,
        "final": final,
        "scoring_version": cfg["version"],
        "movement_confidence": confidence,
        "evidence_fit": fit,
    }
    return final, breakdown


# --------------------------------------------------------------------------
# separation
# --------------------------------------------------------------------------
def separation_verdict(
    scores: list[float],
    movement_confidence_score: float | None = None,
    config: dict | None = None,
) -> tuple[str, str]:
    """Is the top hypothesis actually distinguishable from the runner-up?

    Returns (verdict, reason) as strings, so this module stays free of the type
    layer; the caller maps them onto the enum.

    A fake single winner is the failure this exists to prevent. Two hypotheses
    inside the ambiguity margin are reported as two, which is the right answer
    to an ambiguous case rather than an inability to decide.
    """
    cfg = (config or load_config())["separation"]

    if movement_confidence_score is not None and (
        movement_confidence_score < cfg["min_movement_confidence"]
    ):
        return "INSUFFICIENT", (
            f"movement confidence {movement_confidence_score:.3f} is below "
            f"{cfg['min_movement_confidence']:.2f}; the movement itself is too "
            f"weakly established to explain, whatever the evidence says"
        )

    if not scores:
        return "INSUFFICIENT", "no hypothesis cleared the reporting threshold"

    top = scores[0]
    if top < cfg["min_score_to_report"]:
        return "INSUFFICIENT", (
            f"top score {top:.3f} is below the reporting floor "
            f"{cfg['min_score_to_report']:.2f}"
        )

    if len(scores) == 1:
        if top >= cfg["min_score_for_supported"]:
            return "SUPPORTED", (
                f"a single hypothesis scoring {top:.3f}, with no competing "
                f"explanation above the reporting floor"
            )
        return "PLAUSIBLE", (
            f"one hypothesis at {top:.3f}, below the "
            f"{cfg['min_score_for_supported']:.2f} needed to call it supported"
        )

    second = scores[1]
    margin = top - second
    ratio = top / second if second > 0 else float("inf")

    # Margin is the test, on a bounded [0,1] score. The ratio is applied only
    # in the low-score band, where a small absolute margin can still be a big
    # relative difference; combining the two with OR across the whole range
    # would let the stricter test bind arbitrarily (see config).
    ambiguous = margin < cfg["ambiguous_margin"]
    if not ambiguous and top < cfg["low_score_band"]:
        ambiguous = ratio < cfg["dominance_ratio"]

    if ambiguous:
        return "CONFLICTED", (
            f"top two scores are {top:.3f} and {second:.3f} "
            f"(margin {margin:.3f}, threshold {cfg['ambiguous_margin']:.2f}); "
            f"the evidence does not separate them, so both are reported"
        )

    if top < cfg["min_score_for_supported"]:
        return "PLAUSIBLE", (
            f"the leading hypothesis at {top:.3f} is clear of the runner-up at "
            f"{second:.3f} but below the "
            f"{cfg['min_score_for_supported']:.2f} needed to call it supported"
        )

    return "SUPPORTED", (
        f"the leading hypothesis at {top:.3f} separates from the runner-up at "
        f"{second:.3f} by {margin:.3f}, clear of the "
        f"{cfg['ambiguous_margin']:.2f} ambiguity margin"
    )
