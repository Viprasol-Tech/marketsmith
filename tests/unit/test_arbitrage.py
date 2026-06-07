from __future__ import annotations

import pytest

from marketsmith import arbitrage
from marketsmith.feed import FakeFeed
from marketsmith.models import Market


def _market(venue: str, ticker: str, yes_ask: int, no_ask: int, question: str) -> Market:
    return Market(
        venue=venue,
        ticker=ticker,
        question=question,
        yes_bid=max(1, yes_ask - 2),
        yes_ask=yes_ask,
        no_bid=max(1, no_ask - 2),
        no_ask=no_ask,
        volume=1000,
    )


def test_single_market_arbitrage_detected() -> None:
    m = _market("kalshi", "X", yes_ask=48, no_ask=49, question="Q?")
    opp = arbitrage.single_market_arbitrage(m)
    assert opp is not None
    assert opp.kind == "single-venue"
    assert opp.cost_cents == pytest.approx(97.0)
    assert opp.profit_cents == pytest.approx(3.0)


def test_single_market_no_arbitrage_when_sum_exceeds_payout() -> None:
    m = _market("kalshi", "X", yes_ask=55, no_ask=49, question="Q?")
    assert arbitrage.single_market_arbitrage(m) is None


def test_single_market_fee_can_remove_arbitrage() -> None:
    m = _market("kalshi", "X", yes_ask=49, no_ask=49, question="Q?")
    assert arbitrage.single_market_arbitrage(m) is not None  # 98 < 100
    # 2% fee -> 98 * 1.02 = 99.96 still < 100 but 5% removes it.
    assert arbitrage.single_market_arbitrage(m, fee_fraction=0.05) is None


def test_cross_venue_arbitrage_direction() -> None:
    a = _market("kalshi", "T", yes_ask=47, no_ask=55, question="Same Q?")
    b = _market("polymarket", "T", yes_ask=51, no_ask=49, question="Same Q?")
    opp = arbitrage.cross_venue_arbitrage(a, b)
    assert opp is not None
    assert opp.kind == "cross-venue"
    # Cheapest lock: YES on kalshi (47) + NO on polymarket (49) = 96.
    assert opp.yes_leg == "kalshi:T"
    assert opp.no_leg == "polymarket:T"
    assert opp.cost_cents == pytest.approx(96.0)
    assert opp.profit_cents == pytest.approx(4.0)


def test_cross_venue_picks_more_profitable_direction() -> None:
    # Reverse direction is the profitable one here.
    a = _market("kalshi", "T", yes_ask=60, no_ask=44, question="Same Q?")
    b = _market("polymarket", "T", yes_ask=50, no_ask=55, question="Same Q?")
    opp = arbitrage.cross_venue_arbitrage(a, b)
    assert opp is not None
    # YES on polymarket (50) + NO on kalshi (44) = 94 is best.
    assert opp.yes_leg == "polymarket:T"
    assert opp.no_leg == "kalshi:T"
    assert opp.profit_cents == pytest.approx(6.0)


def test_cross_venue_none_when_no_lock() -> None:
    a = _market("kalshi", "T", yes_ask=60, no_ask=55, question="Same Q?")
    b = _market("polymarket", "T", yes_ask=58, no_ask=52, question="Same Q?")
    assert arbitrage.cross_venue_arbitrage(a, b) is None


def test_find_arbitrage_on_fake_feed_finds_seeded_arbs() -> None:
    opps = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=1.0)
    assert len(opps) >= 2
    kinds = {o.kind for o in opps}
    assert "cross-venue" in kinds
    assert "single-venue" in kinds


def test_find_arbitrage_includes_election_cross_venue() -> None:
    opps = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=1.0)
    cross = [o for o in opps if o.kind == "cross-venue"]
    assert any("ELECTION-2028" in o.yes_leg and "ELECTION-2028" in o.no_leg for o in cross)
    # The seeded election arb: YES kalshi 47 + NO polymarket 49 = 96 -> 4c profit.
    election = next(o for o in cross if "ELECTION-2028" in o.yes_leg)
    assert election.profit_cents == pytest.approx(4.0)


def test_find_arbitrage_sorted_by_profit_desc() -> None:
    opps = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=0.0)
    profits = [o.profit_cents for o in opps]
    assert profits == sorted(profits, reverse=True)


def test_find_arbitrage_respects_min_profit() -> None:
    low = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=0.0)
    high = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=3.5)
    assert len(high) <= len(low)
    assert all(o.profit_cents >= 3.5 for o in high)


def test_find_arbitrage_fee_reduces_opportunities() -> None:
    no_fee = arbitrage.find_arbitrage(FakeFeed().markets(), min_profit_cents=0.1)
    with_fee = arbitrage.find_arbitrage(
        FakeFeed().markets(), fee_fraction=0.05, min_profit_cents=0.1
    )
    assert len(with_fee) <= len(no_fee)


def test_arbitrage_roi() -> None:
    m = _market("kalshi", "X", yes_ask=48, no_ask=49, question="Q?")
    opp = arbitrage.single_market_arbitrage(m)
    assert opp is not None
    assert opp.roi == pytest.approx(3.0 / 97.0)
