"""Stage 4 — deterministic attribution.

Once detection has established that a movement is real and material, this layer
answers three separate questions and keeps them separate:

    which FACTOR moved      LMDI over the revenue identity      (lmdi.py)
    which SLICE moved       Adtributor, NSDI '14                (adtributor.py)
    may we say CAUSED       DiD + temporal precedence           (counterfactual.py)

The third is a boolean a downstream gate reads, not a matter of narrative tone.
`AttributionResult.causal_statement()` returns None unless it was granted, so
there is exactly one way to obtain causal wording and no way to phrase around
it.

No LLM appears anywhere in this package, and no ranking here is produced by a
model.
"""

from attribution.engine import attribute
from attribution.types import (
    AttributionOutcome,
    AttributionResult,
    CounterfactualResult,
    DriverStrength,
    IdentityDecomposition,
)

__all__ = [
    "attribute",
    "AttributionOutcome",
    "AttributionResult",
    "CounterfactualResult",
    "DriverStrength",
    "IdentityDecomposition",
]
