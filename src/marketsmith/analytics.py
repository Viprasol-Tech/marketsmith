"""Pure prediction-market analytics: implied probability, EV, and Kelly sizing.

All functions are deterministic and side-effect free. Probabilities are floats in
``[0, 1]``; prices are in cents (1-99) unless noted otherwise. Fees are expressed
as a fraction of notional (e.g. ``0.01`` for 1%).
"""

from __future__ import annotations

from dataclasses import dataclass

PAYOUT_CENTS = 100.0


def implied_probability(price_cents: float) -> float:
    """Market-implied probability for a contract priced at ``price_cents``.

    A binary contract priced at 60 cents implies a 60% chance of paying out.

    Args:
        price_cents: Contract price in cents, strictly between 0 and 100.

    Returns:
        Implied probability in ``(0, 1)``.
    """
    if not 0 < price_cents < PAYOUT_CENTS:
        raise ValueError(f"price_cents must be in (0, 100); got {price_cents}")
    return price_cents / PAYOUT_CENTS


def break_even_probability(price_cents: float, fee_fraction: float = 0.0) -> float:
    """Probability of winning at which expected value is exactly zero.

    Buying a contract at ``price_cents`` (plus fees) breaks even when the true
    win probability equals the all-in cost divided by the payout.

    Args:
        price_cents: Entry price in cents.
        fee_fraction: Trading fee as a fraction of the contract price.

    Returns:
        Break-even probability in ``(0, 1]``.
    """
    if not 0 < price_cents < PAYOUT_CENTS:
        raise ValueError(f"price_cents must be in (0, 100); got {price_cents}")
    if fee_fraction < 0:
        raise ValueError(f"fee_fraction must be non-negative; got {fee_fraction}")
    cost = price_cents * (1.0 + fee_fraction)
    return cost / PAYOUT_CENTS


def expected_value(
    win_probability: float,
    price_cents: float,
    fee_fraction: float = 0.0,
) -> float:
    """Fee-adjusted expected value per contract, in cents.

    A contract bought at ``price_cents`` costs ``price_cents * (1 + fee)``. If it
    wins (probability ``p``) it returns 100 cents; if it loses it returns 0.

        EV = p * (100 - cost) - (1 - p) * cost = p * 100 - cost

    Args:
        win_probability: Your estimated probability of the contract paying out.
        price_cents: Entry price in cents.
        fee_fraction: Trading fee as a fraction of the contract price.

    Returns:
        Expected profit per contract in cents (may be negative).
    """
    _check_probability(win_probability)
    if not 0 < price_cents < PAYOUT_CENTS:
        raise ValueError(f"price_cents must be in (0, 100); got {price_cents}")
    if fee_fraction < 0:
        raise ValueError(f"fee_fraction must be non-negative; got {fee_fraction}")
    cost = price_cents * (1.0 + fee_fraction)
    return win_probability * PAYOUT_CENTS - cost


def kelly_fraction(
    win_probability: float,
    price_cents: float,
    fee_fraction: float = 0.0,
) -> float:
    """Optimal fraction of bankroll to stake by the Kelly criterion.

    For a binary contract, net odds ``b`` are payoff-per-unit-staked:

        b = (100 - cost) / cost,   cost = price * (1 + fee)
        f* = (b * p - (1 - p)) / b

    The result is clamped to ``[0, 1]``: a non-positive edge yields 0.

    Args:
        win_probability: Your estimated probability of the contract paying out.
        price_cents: Entry price in cents.
        fee_fraction: Trading fee as a fraction of the contract price.

    Returns:
        Kelly fraction in ``[0, 1]``.
    """
    _check_probability(win_probability)
    if not 0 < price_cents < PAYOUT_CENTS:
        raise ValueError(f"price_cents must be in (0, 100); got {price_cents}")
    if fee_fraction < 0:
        raise ValueError(f"fee_fraction must be non-negative; got {fee_fraction}")
    cost = price_cents * (1.0 + fee_fraction)
    net_win = PAYOUT_CENTS - cost
    if net_win <= 0:
        return 0.0
    b = net_win / cost
    p = win_probability
    f = (b * p - (1.0 - p)) / b
    return max(0.0, min(1.0, f))


def kelly_stake(
    win_probability: float,
    price_cents: float,
    bankroll: float,
    fee_fraction: float = 0.0,
    kelly_multiplier: float = 1.0,
) -> float:
    """Recommended stake in account currency for a given bankroll.

    Args:
        win_probability: Your estimated probability of the contract paying out.
        price_cents: Entry price in cents.
        bankroll: Total capital available, in account currency.
        fee_fraction: Trading fee as a fraction of the contract price.
        kelly_multiplier: Scale on full Kelly (e.g. ``0.5`` for half-Kelly).

    Returns:
        Stake amount in account currency (non-negative).
    """
    if bankroll < 0:
        raise ValueError(f"bankroll must be non-negative; got {bankroll}")
    if kelly_multiplier < 0:
        raise ValueError(f"kelly_multiplier must be non-negative; got {kelly_multiplier}")
    frac = kelly_fraction(win_probability, price_cents, fee_fraction)
    return bankroll * frac * kelly_multiplier


@dataclass(frozen=True)
class EdgeReport:
    """Summary of the edge in betting YES at ``price_cents`` given your probability."""

    your_probability: float
    implied_probability: float
    edge: float
    break_even_probability: float
    expected_value_cents: float
    kelly_fraction: float

    def is_favorable(self) -> bool:
        """True when expected value is positive."""
        return self.expected_value_cents > 0


def edge_report(
    win_probability: float,
    price_cents: float,
    fee_fraction: float = 0.0,
) -> EdgeReport:
    """Bundle the core edge metrics for a single contract."""
    implied = implied_probability(price_cents)
    return EdgeReport(
        your_probability=win_probability,
        implied_probability=implied,
        edge=win_probability - implied,
        break_even_probability=break_even_probability(price_cents, fee_fraction),
        expected_value_cents=expected_value(win_probability, price_cents, fee_fraction),
        kelly_fraction=kelly_fraction(win_probability, price_cents, fee_fraction),
    )


def _check_probability(p: float) -> None:
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"probability must be in [0, 1]; got {p}")
