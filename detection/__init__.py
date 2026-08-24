"""Stage 3 — deterministic detection.

Answers one question, without an LLM anywhere in the path:

    did this KPI movement represent a statistically meaningful and
    commercially material change, or was it noise?

The pipeline is fixed and ordered (Architecture Part 9.2):

    coverage gate -> STL -> robust MAD z -> PELT -> materiality gate

Statistical significance and business materiality are computed separately and
reported separately. Only their conjunction produces MATERIAL_EVENT, so
"why did you alert me?" always has two distinct, quotable answers.
"""

from detection.engine import detect
from detection.types import (
    CoverageStatus,
    DetectionOutcome,
    DetectionResult,
    ShiftType,
)

__all__ = [
    "detect",
    "CoverageStatus",
    "DetectionOutcome",
    "DetectionResult",
    "ShiftType",
]
