"""Reproduction of the Adtributor paper's worked example.

Bhagwan et al., *Adtributor: Revenue Debugging in Advertising Systems*,
USENIX NSDI '14 - the motivating example from section 3, as summarised in
Architecture Part 4.2.

The scenario
------------
Revenue falls from 100 to 50.

  Data centre X alone explains 94% of the drop. A pure explanatory-power
  method blames X. But X *also produced* 94% of forecast revenue - it is big,
  not broken. Its share of revenue did not move at all.

  Device type PC went from 50% of forecast revenue to 98% of actual, while
  mobile and tablet went from 25% each to nearly zero. The true cause was a
  configuration error that killed mobile ads.

  Surprise finds it. Explanatory power alone does not.

This test exists to prove the implementation is Adtributor rather than
something Adtributor-flavoured. A `sort(abs(delta))` heuristic - or any
implementation that ranks by size of change - blames data centre X and fails
here. So does an implementation that ranks dimensions by explanatory power
instead of by surprise.

Notation mapping (paper -> implementation)
------------------------------------------
    F, A            total_forecast, total_actual
    F_ij, A_ij      AdtributorElement.forecast, .actual
    Eq. 4  EP_ij    AdtributorElement.explanatory_power
    Eq. 5  p_ij     AdtributorElement.prior
    Eq. 6  q_ij     AdtributorElement.posterior
    Eq. 7  S_ij     AdtributorElement.surprise   (js_divergence_term)
    T_EP            adtributor(t_ep=...)     default 0.67
    T_EEP           adtributor(t_eep=...)    default 0.10
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from attribution.adtributor import adtributor, js_divergence_term
from attribution.types import AttributionOutcome

# --------------------------------------------------------------------------
# The paper's example as a two-dimensional cube.
#
# Revenue 100 -> 50.
#   data_centre : X is 94 of the forecast and 47 of the actual  (share 94% -> 94%)
#                 Y is  6 of the forecast and  3 of the actual  (share  6% ->  6%)
#   device      : PC     50 -> 49    (share 50% -> 98%)
#                 Mobile 25 -> 0.5   (share 25% ->  1%)
#                 Tablet 25 -> 0.5   (share 25% ->  1%)
#
# Both dimensions total 100 forecast and 50 actual, as they must.
# --------------------------------------------------------------------------

FORECAST_ROWS = [
    ("X", "PC", 47.0),
    ("X", "Mobile", 23.5),
    ("X", "Tablet", 23.5),
    ("Y", "PC", 3.0),
    ("Y", "Mobile", 1.5),
    ("Y", "Tablet", 1.5),
]

ACTUAL_ROWS = [
    ("X", "PC", 46.06),
    ("X", "Mobile", 0.47),
    ("X", "Tablet", 0.47),
    ("Y", "PC", 2.94),
    ("Y", "Mobile", 0.03),
    ("Y", "Tablet", 0.03),
]


@pytest.fixture
def cube():
    cols = ["data_centre", "device", "value"]
    f = pd.DataFrame(FORECAST_ROWS, columns=cols)
    a = pd.DataFrame(ACTUAL_ROWS, columns=cols)
    return f, a


def test_the_example_totals_match_the_paper(cube):
    f, a = cube
    assert f.value.sum() == pytest.approx(100.0)
    assert a.value.sum() == pytest.approx(50.0)


# --------------------------------------------------------------------------
# Eq. 7 - surprise
# --------------------------------------------------------------------------
def test_js_divergence_term_is_zero_when_the_share_does_not_move():
    """An element that keeps its share is not surprising, however large."""
    assert js_divergence_term(0.94, 0.94) == pytest.approx(0.0, abs=1e-15)
    assert js_divergence_term(0.5, 0.5) == pytest.approx(0.0, abs=1e-15)


def test_js_divergence_term_is_finite_when_a_share_collapses_to_zero():
    """The reason JS is used instead of KL: a paused campaign is the signal."""
    value = js_divergence_term(0.25, 0.0)
    assert math.isfinite(value)
    assert value > 0
    # KL would be infinite here; JS is bounded by ln(2)/2 per term
    assert value <= 0.5 * math.log(2) + 1e-12


def test_js_divergence_term_is_symmetric():
    assert js_divergence_term(0.25, 0.01) == pytest.approx(
        js_divergence_term(0.01, 0.25)
    )


def test_surprise_matches_a_hand_computed_value():
    """Pin Eq. 7 against arithmetic done by hand, not against our own output."""
    p, q = 0.25, 0.01
    m = (p + q) / 2
    expected = 0.5 * p * math.log(p / m) + 0.5 * q * math.log(q / m)
    assert js_divergence_term(p, q) == pytest.approx(expected, rel=1e-12)


# --------------------------------------------------------------------------
# Eq. 4 - explanatory power
# --------------------------------------------------------------------------
def test_explanatory_power_identifies_data_centre_x_as_the_biggest_mover(cube):
    """The trap: X really does explain ~94% of the drop."""
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    dc = next(d for d in result.dimensions if d.dimension == "data_centre")
    x = next(e for e in dc.all_elements if e.element == "X")

    assert x.explanatory_power == pytest.approx(0.94, abs=0.005)
    # and yet its share did not move at all
    assert x.prior == pytest.approx(0.94, abs=0.005)
    assert x.posterior == pytest.approx(0.94, abs=0.005)
    assert x.surprise == pytest.approx(0.0, abs=1e-4)


def test_explanatory_power_sums_to_one_within_each_dimension(cube):
    """Eq. 4 is a decomposition of the total change; the shares must close."""
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    for dim in result.dimensions:
        total = sum(e.explanatory_power for e in dim.all_elements)
        assert total == pytest.approx(1.0, abs=1e-9), (
            f"{dim.dimension} EPs sum to {total}, not 1"
        )


def test_priors_and_posteriors_each_sum_to_one(cube):
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    for dim in result.dimensions:
        assert sum(e.prior for e in dim.all_elements) == pytest.approx(1.0, abs=1e-9)
        assert sum(e.posterior for e in dim.all_elements) == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------------------------
# the result the paper is about
# --------------------------------------------------------------------------
def test_selected_dimension_is_device_not_data_centre(cube):
    """The headline claim: surprise beats size.

    A method that ranks by magnitude of change picks data_centre. Adtributor
    picks device, because that is where the distribution actually shifted.
    """
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])

    assert result.outcome is AttributionOutcome.ATTRIBUTED
    assert result.winner is not None
    assert result.winner.dimension == "device", (
        f"selected {result.winner.dimension}; the paper's answer is device"
    )

    dc = next(d for d in result.dimensions if d.dimension == "data_centre")
    assert result.winner.surprise > dc.surprise, (
        "device must be more surprising than data_centre"
    )


def test_selected_elements_are_the_mobile_devices(cube):
    """The config error killed mobile ads; that is what must be returned."""
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    selected = set(result.winner.element_names)

    assert selected == {"Mobile", "Tablet"}, (
        f"selected {selected}; the cause is the collapsed mobile/tablet share"
    )
    assert "PC" not in selected, "PC gained share; it is not the cause"


def test_the_mobile_elements_carry_the_explanatory_power(cube):
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    device = result.winner

    assert device.explanatory_power >= 0.67
    assert device.explanatory_power == pytest.approx(0.98, abs=0.02)
    for el in device.candidates:
        assert el.explanatory_power > result.t_eep


def test_data_centre_qualifies_on_explanatory_power_but_loses_on_surprise(cube):
    """Both dimensions explain the change; only one is informative.

    This is the precise shape of the paper's argument, so it is worth
    asserting rather than inferring from the winner alone.
    """
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"])
    dc = next(d for d in result.dimensions if d.dimension == "data_centre")

    assert dc.passed_ep_threshold, "X alone does clear the 67% threshold"
    assert dc.surprise == pytest.approx(0.0, abs=1e-4)
    assert result.dimensions[0].dimension == "device", (
        "dimensions must be ranked by surprise, most surprising first"
    )


def test_a_magnitude_ranking_heuristic_would_get_this_wrong(cube):
    """Guard the guard: confirm the strawman really does fail this example.

    If sort-by-magnitude happened to give the same answer, this whole test
    file would prove nothing.
    """
    f, a = cube
    merged = (
        f.groupby("data_centre").value.sum().rename("f").to_frame()
        .join(a.groupby("data_centre").value.sum().rename("a"))
    )
    biggest_dc = (merged.a - merged.f).abs().idxmax()
    assert biggest_dc == "X", "the naive heuristic blames data centre X"

    result = adtributor(f, a, ["data_centre", "device"])
    assert result.winner.dimension != "data_centre", (
        "our implementation must not agree with the strawman"
    )


# --------------------------------------------------------------------------
# threshold behaviour
# --------------------------------------------------------------------------
def test_succinctness_floor_excludes_negligible_elements(cube):
    """T_EEP keeps noise elements out of the explanation."""
    f, a = cube
    result = adtributor(f, a, ["device"], t_eep=0.60)
    device = next(d for d in result.dimensions if d.dimension == "device")
    # each mobile element is worth ~0.49, below a 0.60 floor, so nothing
    # qualifies and the dimension cannot explain the change
    assert device.n_candidates == 0
    assert not device.passed_ep_threshold


def test_no_qualifying_dimension_returns_the_multi_dimensional_case(cube):
    """When nothing clears T_EP the engine must decline, not guess."""
    f, a = cube
    result = adtributor(f, a, ["data_centre", "device"], t_ep=0.999, t_eep=0.99)
    assert result.outcome is AttributionOutcome.MULTI_DIMENSIONAL_CASE
    assert result.winner is None
    assert "combination" in result.reason


def test_ranking_is_deterministic(cube):
    """Same input, same order, every time - a ranking judges can re-run."""
    f, a = cube
    first = adtributor(f, a, ["data_centre", "device"])
    for _ in range(5):
        again = adtributor(f, a, ["data_centre", "device"])
        assert [d.dimension for d in again.dimensions] == [
            d.dimension for d in first.dimensions
        ]
        assert again.winner.element_names == first.winner.element_names
        assert again.winner.surprise == pytest.approx(first.winner.surprise)
