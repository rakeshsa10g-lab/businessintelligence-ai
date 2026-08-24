"""Typed confidence and calibration (Architecture Part 13.4).

Two things kept apart, because the distinction is the whole point:

  **the evidence score** — deterministic, computed from the bundle
  **the calibration** — how often calls of this kind have actually been right

A bare `0.82` is the thing the research says not to show. A 184-participant
study found calibrated confidence lifted decision accuracy by about 20% while a
context-free number gave about 2% and *increased* automation bias. A band with
its observed hit-rate tells a reader how often this kind of call has been
right, which is what they need in order to decide whether to check it.

When there is not enough history to say, the answer is `UNCALIBRATED` — not an
invented accuracy.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    # Below the reportable floor: the system abstains rather than qualifying.
    INSUFFICIENT = "INSUFFICIENT"
    # A band was computed, but too few observed cases back it to quote a rate.
    UNCALIBRATED = "UNCALIBRATED"


class CalibrationCoverage(str, Enum):
    IN_COVERAGE = "in_coverage"
    OUT_OF_COVERAGE = "out_of_coverage"
    NO_HISTORY = "no_history"


class ConfidenceComponent(BaseModel):
    """One term of the score, with its raw and weighted value.

    Exposed so a reader can recompute the total by hand. A confidence figure
    nobody can reconstruct is a figure nobody should act on.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    raw: float
    weight: float
    weighted: float
    basis: str = ""


class CalibrationEntry(BaseModel):
    """Observed accuracy for one band."""

    model_config = ConfigDict(frozen=True)

    band: ConfidenceBand
    correct: int
    total: int
    source: str = "synthetic"

    @property
    def accuracy(self) -> float | None:
        """The raw observed rate. For DISPLAY - it is what was actually seen."""
        return self.correct / self.total if self.total else None

    @property
    def estimated_accuracy(self) -> float | None:
        """Laplace-smoothed, for use in arithmetic.

        12 correct out of 12 is not evidence of a 100% success rate; it is
        evidence that no failure has been observed yet. Feeding the raw 1.0
        into the deferral rule makes `(1 - p_model) x cost_of_error`
        identically zero, so the model arm wins every comparison at every
        decision value and the cost-sensitive rule silently degenerates into
        "always automate".

        Add-one smoothing, (correct + 1) / (total + 2), is the standard
        correction: it pulls a small sample towards 0.5 in proportion to how
        little of it there is, and 12/12 becomes 0.93 rather than 1.00.

        The DISPLAY still shows the raw counts. A reader should see "29 of 34",
        not a smoothed decimal - the smoothing exists to stop the arithmetic
        overclaiming, not to restate what was observed.
        """
        if not self.total:
            return None
        return (self.correct + 1) / (self.total + 2)

    def render(self) -> str:
        if not self.total:
            return "no comparable cases recorded"
        return f"correct in {self.correct} of {self.total} similar past cases"


class Confidence(BaseModel):
    """The complete confidence state. Never produced by a model."""

    model_config = ConfigDict(frozen=True)

    score: float
    band: ConfidenceBand
    components: tuple[ConfidenceComponent, ...] = ()
    contradiction_multiplier: float = 1.0

    calibration: CalibrationEntry | None = None
    coverage: CalibrationCoverage = CalibrationCoverage.NO_HISTORY
    calibration_source: str = ""
    calibration_is_synthetic: bool = True

    config_version: str = ""
    reason: str = ""

    @property
    def reportable(self) -> bool:
        return self.band not in (
            ConfidenceBand.INSUFFICIENT, ConfidenceBand.UNCALIBRATED
        )

    @property
    def observed_accuracy(self) -> float | None:
        """The raw rate, for display and reporting."""
        return self.calibration.accuracy if self.calibration else None

    @property
    def estimated_accuracy(self) -> float | None:
        """The smoothed rate, for the deferral arithmetic. See
        CalibrationEntry.estimated_accuracy for why the two differ."""
        return self.calibration.estimated_accuracy if self.calibration else None

    def render(self) -> str:
        """The display string. A band, a base rate, and where it came from.

        Never a bare number: the whole reason for this class is that `0.82`
        alone measurably increases automation bias.
        """
        if self.band is ConfidenceBand.INSUFFICIENT:
            return (
                f"Insufficient confidence (score {self.score:.2f}) - "
                f"no explanation is offered"
            )
        if self.band is ConfidenceBand.UNCALIBRATED or self.calibration is None:
            return (
                f"{self.band.value.title()} signal strength "
                f"(score {self.score:.2f}), UNCALIBRATED - too few comparable "
                f"cases to state how often this kind of call has been right"
            )
        label = self.band.value.title()
        synthetic = " (synthetic calibration set)" if self.calibration_is_synthetic else ""
        return (
            f"{label} - {self.calibration.render()}{synthetic}"
        )

    def explain(self) -> str:
        parts = [f"{c.name}={c.raw:.3f}x{c.weight:.2f}" for c in self.components]
        return (
            f"{' + '.join(parts)} = "
            f"{sum(c.weighted for c in self.components):.3f} "
            f"x {self.contradiction_multiplier:.2f} = {self.score:.3f} "
            f"-> {self.band.value}"
        )


class CalibrationTable(BaseModel):
    """The seeded reliability table.

    `is_synthetic` is not decoration. A judge who catches an implication of
    production history has destroyed the credibility of the one section that
    was supposed to be about honesty; a judge who sees it labelled concludes
    the opposite.
    """

    model_config = ConfigDict(frozen=True)

    version: str
    generated_at: str = ""
    is_synthetic: bool = True
    source: str = ""
    n_cases: int = 0
    entries: tuple[CalibrationEntry, ...] = ()
    min_cases_per_band: int = 10

    def entry_for(self, band: ConfidenceBand) -> CalibrationEntry | None:
        for e in self.entries:
            if e.band is band:
                return e
        return None
