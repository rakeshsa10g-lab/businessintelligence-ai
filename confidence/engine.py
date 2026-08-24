"""Computing confidence deterministically (Architecture Part 13.4).

Six weighted components, a contradiction multiplier, a band, and a calibration
lookup. Every number comes from `config/confidence.yaml` or from the frozen
bundle; nothing here is generated, and the model is not consulted.

The one deviation from Part 13.4 is documented in the config: `(1 - p_value)`
is replaced by bootstrap robustness, because the Welch p-value is computed on a
window PELT selected for maximal displacement and therefore reads p < 0.001 on
pure noise (ADR-017). Weighting a post-selection statistic at 0.20 would put a
fifth of the confidence on a number that is high whether or not anything
happened.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path

import yaml

from confidence.types import (
    CalibrationCoverage,
    CalibrationEntry,
    CalibrationTable,
    Confidence,
    ConfidenceBand,
    ConfidenceComponent,
)
from evidence.types import DataQualityState, EvidenceBundle, HypothesisStatus

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "confidence.yaml"
CALIBRATION_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "calibration.json"
)


class ConfidenceError(ValueError):
    """The confidence configuration is unusable."""


@functools.lru_cache(maxsize=4)
def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else CONFIG_PATH
    if not p.exists():
        raise ConfidenceError(f"no confidence configuration at {p}")
    config = yaml.safe_load(p.read_text(encoding="utf-8"))

    for key in ("version", "weights", "contradiction", "data_quality",
                "bands", "calibration"):
        if key not in config:
            raise ConfidenceError(f"confidence config is missing '{key}'")

    total = sum(config["weights"].values())
    if abs(total - 1.0) > 1e-6:
        raise ConfidenceError(
            f"confidence weights sum to {total}, not 1.0; scores would not be "
            f"comparable across configuration versions"
        )
    return config


@functools.lru_cache(maxsize=4)
def load_calibration(path: str | None = None) -> CalibrationTable:
    """The seeded reliability table, or an empty one.

    An absent table is not an error: it means every band reports
    UNCALIBRATED, which is the correct behaviour before any history exists.
    Inventing accuracies to fill it would be worse than having none.
    """
    p = Path(path) if path else CALIBRATION_PATH
    if not p.exists():
        return CalibrationTable(
            version="0.0.0", is_synthetic=True,
            source="no calibration table present",
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return CalibrationTable(
        version=data.get("version", "0.0.0"),
        generated_at=data.get("generated_at", ""),
        is_synthetic=data.get("is_synthetic", True),
        source=data.get("source", ""),
        n_cases=data.get("n_cases", 0),
        min_cases_per_band=data.get("min_cases_per_band", 10),
        entries=tuple(
            CalibrationEntry(
                band=ConfidenceBand(e["band"]), correct=e["correct"],
                total=e["total"], source=e.get("source", "synthetic"),
            )
            for e in data.get("entries", [])
        ),
    )


def reload_all() -> None:
    load_config.cache_clear()
    load_calibration.cache_clear()


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------
# data quality
# --------------------------------------------------------------------------
def data_quality_score(
    bundle: EvidenceBundle, config: dict | None = None
) -> tuple[float, str]:
    """Deduct for each measurable defect in the data behind the movement."""
    cfg = (config or load_config())["data_quality"]
    score = cfg["base"]
    reasons: list[str] = []

    states = set(bundle.data_quality_state)
    if DataQualityState.IMPUTED in states:
        score -= cfg["penalty_imputed"]
        reasons.append("imputed days in the window")
    if DataQualityState.SPARSE in states:
        score -= cfg["penalty_sparse"]
        reasons.append("sparse history")
    if DataQualityState.STALE in states:
        score -= cfg["penalty_stale"]
        reasons.append("a source past its staleness SLA")
    if DataQualityState.SCHEMA_CHANGE_APPLIED in states:
        score -= cfg["penalty_schema_change"]
        reasons.append("a stitched schema change")

    return _clamp(score), ", ".join(reasons) or "no data-quality deductions"


# --------------------------------------------------------------------------
# the score
# --------------------------------------------------------------------------
def compute(
    bundle: EvidenceBundle,
    config: dict | None = None,
    calibration: CalibrationTable | None = None,
) -> Confidence:
    """The confidence for a bundle's leading hypothesis."""
    cfg = config or load_config()
    table = calibration if calibration is not None else load_calibration()
    weights = cfg["weights"]

    if not bundle.hypotheses:
        return Confidence(
            score=0.0, band=ConfidenceBand.INSUFFICIENT,
            config_version=cfg["version"],
            coverage=CalibrationCoverage.NO_HISTORY,
            reason=(
                f"no hypothesis to be confident about: {bundle.status_reason}"
            ),
        )

    top = bundle.hypotheses[0]
    quality, quality_reason = data_quality_score(bundle, cfg)
    breakdown = top.score_breakdown
    parts = dict(breakdown.components)

    raw = {
        "contribution": _clamp(abs(top.contribution_share or 0.0)),
        "robustness": _clamp(top.robustness_score),
        "evidence_strength": _clamp(breakdown.evidence_fit),
        "counterfactual": 1.0 if (
            top.counterfactual is not None and top.counterfactual.passed
        ) else 0.0,
        "data_quality": quality,
        "temporal_precedence": 1.0 if top.temporal_precedence else 0.0,
    }
    basis = {
        "contribution": "share of the movement from the LMDI decomposition",
        "robustness": (
            "moving-block bootstrap stability; replaces Part 13.4's "
            "(1 - p_value), see ADR-017"
        ),
        "evidence_strength": "retrieval corroboration for this hypothesis",
        "counterfactual": "difference-in-differences against a matched control",
        "data_quality": quality_reason,
        "temporal_precedence": "a dated cause precedes the changepoint",
    }

    missing = set(weights) - set(raw)
    if missing:
        raise ConfidenceError(
            f"config weights {sorted(missing)} have no computed component"
        )

    components = tuple(
        ConfidenceComponent(
            name=name, raw=raw[name], weight=weights[name],
            weighted=weights[name] * raw[name], basis=basis[name],
        )
        for name in sorted(weights)
    )
    subtotal = sum(c.weighted for c in components)

    contra_cfg = cfg["contradiction"]
    penalty = min(
        contra_cfg["max_penalty"],
        contra_cfg["penalty_per_signal"] * top.evidence_profile.contradiction_count,
    )
    multiplier = 1.0 - penalty
    score = _clamp(subtotal * multiplier)

    band = band_for(score, cfg)

    # A CONFLICTED hypothesis is capped: the analysis declined to separate two
    # explanations, and reporting HIGH confidence in one of them would assert
    # exactly what it refused to.
    if top.status is HypothesisStatus.CONFLICTED and band is ConfidenceBand.HIGH:
        band = ConfidenceBand.MEDIUM

    entry = table.entry_for(band)
    min_cases = cfg["calibration"]["min_cases_per_band"]
    if entry is None or entry.total < min_cases:
        coverage = (
            CalibrationCoverage.NO_HISTORY if entry is None
            else CalibrationCoverage.OUT_OF_COVERAGE
        )
        reported_band = (
            ConfidenceBand.INSUFFICIENT if band is ConfidenceBand.INSUFFICIENT
            else ConfidenceBand.UNCALIBRATED
        )
        return Confidence(
            score=score, band=reported_band, components=components,
            contradiction_multiplier=multiplier, calibration=entry,
            coverage=coverage, calibration_source=table.source,
            calibration_is_synthetic=table.is_synthetic,
            config_version=cfg["version"],
            reason=(
                f"signal strength {score:.3f} falls in the {band.value} band, "
                f"but only "
                f"{entry.total if entry else 0} comparable case(s) are "
                f"recorded against the {min_cases} required to quote a rate"
            ),
        )

    return Confidence(
        score=score, band=band, components=components,
        contradiction_multiplier=multiplier, calibration=entry,
        coverage=CalibrationCoverage.IN_COVERAGE,
        calibration_source=table.source,
        calibration_is_synthetic=table.is_synthetic,
        config_version=cfg["version"],
        reason=(
            f"signal strength {score:.3f} -> {band.value}; "
            f"{entry.render()}"
        ),
    )


def band_for(score: float, config: dict | None = None) -> ConfidenceBand:
    bands = (config or load_config())["bands"]
    if score >= bands["HIGH"]:
        return ConfidenceBand.HIGH
    if score >= bands["MEDIUM"]:
        return ConfidenceBand.MEDIUM
    if score >= bands["LOW"]:
        return ConfidenceBand.LOW
    return ConfidenceBand.INSUFFICIENT
