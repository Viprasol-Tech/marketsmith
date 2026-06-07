from __future__ import annotations

import math

import pytest

from marketsmith import analytics


def test_implied_probability_basic() -> None:
    assert analytics.implied_probability(60) == pytest.approx(0.60)
    assert analytics.implied_probability(1) == pytest.approx(0.01)
    assert analytics.implied_probability(99) == pytest.approx(0.99)


def test_implied_probability_rejects_out_of_range() -> None:
    with pytest.raises(ValueError):
        analytics.implied_probability(0)
    with pytest.raises(ValueError):
        analytics.implied_probability(100)


def test_break_even_probability_no_fee() -> None:
    # At 40c with no fee you need a 40% win rate to break even.
    assert analytics.break_even_probability(40) == pytest.approx(0.40)


def test_break_even_probability_with_fee() -> None:
    # 40c at 5% fee -> cost 42c -> break-even 0.42.
    assert analytics.break_even_probability(40, fee_fraction=0.05) == pytest.approx(0.42)


def test_break_even_rejects_negative_fee() -> None:
    with pytest.raises(ValueError):
        analytics.break_even_probability(40, fee_fraction=-0.1)


def test_expected_value_hand_computed() -> None:
    # Buy YES @ 40c, no fee, true prob 0.5: EV = 0.5*100 - 40 = 10c.
    assert analytics.expected_value(0.5, 40) == pytest.approx(10.0)


def test_expected_value_negative_edge() -> None:
    # Buy YES @ 70c, true prob 0.5: EV = 50 - 70 = -20c.
    assert analytics.expected_value(0.5, 70) == pytest.approx(-20.0)


def test_expected_value_with_fee() -> None:
    # Buy YES @ 40c at 10% fee -> cost 44c; true prob 0.5 -> EV = 50 - 44 = 6c.
    assert analytics.expected_value(0.5, 40, fee_fraction=0.10) == pytest.approx(6.0)


def test_expected_value_break_even_is_zero() -> None:
    p = analytics.break_even_probability(40, fee_fraction=0.05)
    assert analytics.expected_value(p, 40, fee_fraction=0.05) == pytest.approx(0.0, abs=1e-9)


def test_expected_value_rejects_bad_probability() -> None:
    with pytest.raises(ValueError):
        analytics.expected_value(1.5, 40)
    with pytest.raises(ValueError):
        analytics.expected_value(-0.1, 40)


def test_kelly_fraction_hand_computed() -> None:
    # Price 50c, no fee: b = 50/50 = 1. p = 0.6 -> f = (1*0.6 - 0.4)/1 = 0.2.
    assert analytics.kelly_fraction(0.6, 50) == pytest.approx(0.20)


def test_kelly_fraction_known_odds() -> None:
    # Price 40c, no fee: b = 60/40 = 1.5. p = 0.6:
    # f = (1.5*0.6 - 0.4)/1.5 = (0.9 - 0.4)/1.5 = 0.5/1.5 = 1/3.
    assert analytics.kelly_fraction(0.6, 40) == pytest.approx(1.0 / 3.0)


def test_kelly_fraction_clamped_to_zero_on_no_edge() -> None:
    # True prob equals implied prob -> no edge -> Kelly 0.
    assert analytics.kelly_fraction(0.5, 50) == pytest.approx(0.0)
    # Negative edge stays clamped at 0.
    assert analytics.kelly_fraction(0.3, 50) == 0.0


def test_kelly_fraction_full_certainty_clamped_to_one() -> None:
    assert analytics.kelly_fraction(1.0, 50) == pytest.approx(1.0)


def test_kelly_fraction_with_fee_reduces_size() -> None:
    no_fee = analytics.kelly_fraction(0.6, 50)
    with_fee = analytics.kelly_fraction(0.6, 50, fee_fraction=0.05)
    assert with_fee < no_fee


def test_kelly_stake_scales_bankroll() -> None:
    # Kelly fraction 0.2 at price 50 over a 1000 bankroll -> stake 200.
    assert analytics.kelly_stake(0.6, 50, 1000.0) == pytest.approx(200.0)


def test_kelly_stake_half_kelly() -> None:
    full = analytics.kelly_stake(0.6, 50, 1000.0)
    half = analytics.kelly_stake(0.6, 50, 1000.0, kelly_multiplier=0.5)
    assert half == pytest.approx(full / 2.0)


def test_kelly_stake_rejects_negative_bankroll() -> None:
    with pytest.raises(ValueError):
        analytics.kelly_stake(0.6, 50, -100.0)


def test_edge_report_bundle() -> None:
    report = analytics.edge_report(0.6, 50)
    assert report.implied_probability == pytest.approx(0.5)
    assert report.edge == pytest.approx(0.1)
    assert report.expected_value_cents == pytest.approx(10.0)
    assert report.kelly_fraction == pytest.approx(0.2)
    assert report.is_favorable() is True


def test_edge_report_unfavorable() -> None:
    report = analytics.edge_report(0.4, 50)
    assert report.expected_value_cents < 0
    assert report.is_favorable() is False


def test_expected_value_monotonic_in_probability() -> None:
    evs = [analytics.expected_value(p / 10, 50) for p in range(0, 11)]
    assert evs == sorted(evs)
    assert math.isclose(evs[5], 0.0, abs_tol=1e-9)
