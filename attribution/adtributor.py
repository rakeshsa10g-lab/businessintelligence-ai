"""Stage B — dimensional attribution by Adtributor (Architecture Part 10.2).

Bhagwan, Kumar, Ramjee, Varghese, Mohapatra, Manoharan & Shah,
*Adtributor: Revenue Debugging in Advertising Systems*, USENIX NSDI '14.

Given a forecast F and an actual A for a measure, broken down by several
dimensions, find the dimension and the set of elements that best explains the
deviation. Three ingredients, all of them necessary:

  Explanatory power   EP_ij = (A_ij - F_ij) / (A - F)          (Eq. 4)
                      the fraction of the total change contributed by element
                      j of dimension i. EPs within a dimension sum to 1.

  Succinctness        Occam's razor: prefer the smallest element set clearing
                      a threshold T_EP of the change, with a per-element floor
                      T_EEP so that noise elements cannot pad the set.

  Surprise            how much the element's *share* moved, as a
                      Jensen-Shannon divergence between the prior
                      p_ij = F_ij/F (Eq. 5) and posterior q_ij = A_ij/A (Eq. 6):

                          S_ij = 1/2 p ln(p/m) + 1/2 q ln(q/m),  m = (p+q)/2
                                                                  (Eq. 7)

                      JS rather than KL because it is symmetric and stays
                      finite when a share collapses to zero - which is exactly
                      the case that matters when a channel stops serving.

Why surprise is not optional, in the paper's own words: revenue falls
100 -> 50; data centre X alone explains 94% of the drop, so a pure
explanatory-power method blames X. But X *also produced* 94% of forecast
revenue - it is big, not broken. Device type PC meanwhile went from 50% of
forecast to 98% of actual while mobile went to nearly zero. The true cause was
a config error killing mobile ads. Surprise finds it; explanatory power alone
does not. The paper measures 95% accuracy against 20% for the
succinctness-only strawman.

`tests/test_adtributor.py` reproduces that example numerically, which is the
difference between implementing Adtributor and implementing something
Adtributor-flavoured.

This module is deliberately a readable implementation of the equations rather
than a call into an opaque package: the ranking has to be auditable line by
line, and no LLM is involved in producing it.
"""

from __future__ import annotations

import math

import pandas as pd

from attribution.types import (
    AdtributorElement,
    AdtributorResult,
    AttributionOutcome,
    DimensionExplanation,
)

# Paper defaults (NSDI '14, section 5): explain at least 67% of the change,
# with each contributing element worth at least 10% of it.
T_EP = 0.67
T_EEP = 0.10

# A dimension only localises a movement if its *distribution* moved. Zero JS
# divergence means prior and posterior are the same distribution, so the
# dimension carries no localisation information at all - every element shrank
# in proportion. That happens exactly when the cause lives in a combination of
# dimensions: drop the (A,X) and (B,Y) cells and the d1 marginal still reads
# 50/50, as does d2, while EP happily reaches 1.0 by naming every element.
#
# This is not a tuned threshold. It is the numerical tolerance on the
# statement "the two distributions are identical", and it is the one signal
# that separates a one-dimensional cause from a case only HotSpot or Squeeze
# could localise (Architecture Part 4.2, both deliberately out of scope).
T_SURPRISE = 1e-9


def js_divergence_term(p: float, q: float) -> float:
    """One element's contribution to the Jensen-Shannon divergence (Eq. 7).

    Zero-share terms drop out rather than diverging, which is the whole reason
    JS is used instead of KL: a share going to zero is the signal, not an
    error.
    """
    if p <= 0 and q <= 0:
        return 0.0
    m = (p + q) / 2.0
    if m <= 0:
        return 0.0
    total = 0.0
    if p > 0:
        total += 0.5 * p * math.log(p / m)
    if q > 0:
        total += 0.5 * q * math.log(q / m)
    return total


def _explain_dimension(
    dimension: str,
    forecast_by_element: dict[str, float],
    actual_by_element: dict[str, float],
    total_forecast: float,
    total_actual: float,
    t_ep: float,
    t_eep: float,
) -> DimensionExplanation:
    """Score every element of one dimension, then select greedily by surprise."""
    total_change = total_actual - total_forecast
    names = sorted(set(forecast_by_element) | set(actual_by_element))

    elements: list[AdtributorElement] = []
    for name in names:
        fe = float(forecast_by_element.get(name, 0.0))
        ae = float(actual_by_element.get(name, 0.0))
        ep = (ae - fe) / total_change if total_change != 0 else 0.0
        p = fe / total_forecast if total_forecast else 0.0
        q = ae / total_actual if total_actual else 0.0
        elements.append(
            AdtributorElement(
                dimension=dimension,
                element=name,
                forecast=fe,
                actual=ae,
                explanatory_power=ep,
                prior=p,
                posterior=q,
                surprise=js_divergence_term(p, q),
            )
        )

    # Rank by SURPRISE, not by size of change. This single line is the
    # difference between Adtributor and the strawman it was written to beat.
    ranked = sorted(
        elements, key=lambda e: (-e.surprise, -abs(e.explanatory_power), e.element)
    )

    candidates: list[AdtributorElement] = []
    explained = 0.0
    surprise = 0.0
    for el in ranked:
        # Succinctness floor: an element must be worth T_EEP of the change on
        # its own before it may join the explanation.
        if el.explanatory_power > t_eep:
            candidates.append(el)
            explained += el.explanatory_power
            surprise += el.surprise
        if explained >= t_ep:
            break

    passed = explained >= t_ep
    selected_names = {e.element for e in candidates}
    for el in elements:
        el.selected = el.element in selected_names

    # Succinctness as a reportable property, not just a stopping rule: an
    # "explanation" needing most of the dimension's elements explains nothing.
    succinct = bool(candidates) and len(candidates) <= max(1, len(elements) // 2)

    if passed:
        reason = (
            f"{len(candidates)} of {len(elements)} elements explain "
            f"{explained:.0%} of the change (>= {t_ep:.0%}), "
            f"total surprise {surprise:.4f}"
        )
    else:
        reason = (
            f"no element set cleared the {t_ep:.0%} explanatory-power "
            f"threshold; best was {explained:.0%}"
        )

    return DimensionExplanation(
        dimension=dimension,
        candidates=candidates,
        all_elements=ranked,
        explanatory_power=explained,
        surprise=surprise,
        n_candidates=len(candidates),
        n_elements=len(elements),
        passed_ep_threshold=passed,
        succinct=succinct,
        reason=reason,
    )


def adtributor(
    forecast: pd.DataFrame,
    actual: pd.DataFrame,
    dims: list[str],
    *,
    value_column: str = "value",
    t_ep: float = T_EP,
    t_eep: float = T_EEP,
) -> AdtributorResult:
    """Run Adtributor over every dimension independently, then rank.

    Each dimension is evaluated on its own before any drill-down. That
    independence is the design: a top-down walk commits to the biggest region
    before it has looked at channel at all, which is how the strawman reaches
    20% accuracy.

    `forecast` is the STL trend+seasonal counterfactual from detection, per
    cell - a clean reuse, since Stage 3 already produced exactly the F that
    attribution needs.
    """
    if not dims:
        raise ValueError("adtributor needs at least one dimension")

    total_forecast = float(forecast[value_column].sum())
    total_actual = float(actual[value_column].sum())
    total_change = total_actual - total_forecast

    explanations: list[DimensionExplanation] = []
    for dim in dims:
        if dim not in forecast.columns or dim not in actual.columns:
            continue
        f = forecast.groupby(dim)[value_column].sum().to_dict()
        a = actual.groupby(dim)[value_column].sum().to_dict()
        explanations.append(
            _explain_dimension(
                dim, f, a, total_forecast, total_actual, t_ep, t_eep
            )
        )

    # A dimension must clear the explanatory-power threshold AND have
    # actually redistributed. See T_SURPRISE above for why the second half is
    # not optional.
    qualifying = [
        e
        for e in explanations
        if e.passed_ep_threshold and e.surprise > T_SURPRISE
    ]
    # The winner is the most surprising qualifying dimension - not the one with
    # the largest change.
    ranked = sorted(qualifying, key=lambda d: -d.surprise)
    # Every dimension stays in the output, qualifying or not. A dimension that
    # was considered and rejected is information the reader is entitled to -
    # dropping it would hide, for instance, that data centre X did clear the
    # explanatory-power bar and was set aside because its share never moved.
    qualifying_ids = {id(e) for e in qualifying}
    all_ranked = ranked + sorted(
        [e for e in explanations if id(e) not in qualifying_ids],
        key=lambda d: -d.surprise,
    )

    if not qualifying:
        # No single dimension accounts for the movement. Adtributor cannot
        # localise causes spanning dimension combinations - that is HotSpot's
        # and Squeeze's problem, deliberately out of scope. Say so rather than
        # returning the least bad option as though it were an answer.
        outcome = AttributionOutcome.MULTI_DIMENSIONAL_CASE
        winner = None
        cleared_ep = [e for e in explanations if e.passed_ep_threshold]
        if cleared_ep:
            reason = (
                f"{len(cleared_ep)} dimension(s) reached {t_ep:.0%} "
                "explanatory power, but only by naming elements whose shares "
                "did not move (total surprise ~0). The distribution is "
                "unchanged within every dimension, which is the signature of a "
                "cause spanning a combination of dimensions - Adtributor does "
                "not localise those"
            )
        else:
            reason = (
                "no single dimension explained "
                f"{t_ep:.0%} of the movement; the cause appears to span a "
                "combination of dimensions, which Adtributor does not localise"
            )
    else:
        winner = ranked[0]
        outcome = AttributionOutcome.ATTRIBUTED
        reason = (
            f"{winner.dimension} selected on surprise "
            f"({winner.surprise:.4f}) among {len(qualifying)} qualifying "
            f"dimension(s)"
        )

    return AdtributorResult(
        total_forecast=total_forecast,
        total_actual=total_actual,
        total_change=total_change,
        dimensions=all_ranked,
        winner=winner,
        outcome=outcome,
        t_ep=t_ep,
        t_eep=t_eep,
        reason=reason,
    )


# --------------------------------------------------------------------------
# the strawman, implemented on purpose
# --------------------------------------------------------------------------
def rank_by_contribution_only(
    forecast: pd.DataFrame,
    actual: pd.DataFrame,
    dims: list[str],
    *,
    value_column: str = "value",
) -> list[tuple[str, str, float]]:
    """Rank dimensions and elements by size of change alone - NO surprise.

    This is Adtributor's own strawman, and it exists here so the difference can
    be demonstrated rather than asserted. The paper measured it at 20% accuracy
    against Adtributor's 95%; on the paper's worked example it blames the data
    centre that produced 94% of revenue and was working perfectly.

    It is never used for attribution. `eval/run_attribution_eval.py` runs it
    beside the real algorithm to show what surprise buys.

    Returns (dimension, element, |delta|) sorted by absolute change.
    """
    rows: list[tuple[str, str, float]] = []
    for dim in dims:
        if dim not in forecast.columns or dim not in actual.columns:
            continue
        f = forecast.groupby(dim)[value_column].sum()
        a = actual.groupby(dim)[value_column].sum()
        for element in sorted(set(f.index) | set(a.index)):
            delta = float(a.get(element, 0.0)) - float(f.get(element, 0.0))
            rows.append((dim, str(element), abs(delta)))
    return sorted(rows, key=lambda r: -r[2])
