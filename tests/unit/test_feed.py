from __future__ import annotations

import pytest

from marketsmith.feed import FakeFeed, LiveFeed, MarketFeed
from marketsmith.models import Market


def test_fake_feed_is_a_market_feed() -> None:
    assert isinstance(FakeFeed(), MarketFeed)


def test_fake_feed_has_expected_market_count() -> None:
    assert len(FakeFeed().markets()) == 9


def test_fake_feed_is_deterministic() -> None:
    a = FakeFeed().markets()
    b = FakeFeed().markets()
    assert [m.key() for m in a] == [m.key() for m in b]
    assert a == b


def test_fake_feed_returns_a_fresh_list() -> None:
    feed = FakeFeed()
    first = feed.markets()
    first.clear()
    assert len(feed.markets()) == 9


def test_fake_feed_get_found_and_missing() -> None:
    feed = FakeFeed()
    m = feed.get("kalshi", "ELECTION-2028")
    assert m is not None
    assert isinstance(m, Market)
    assert m.venue == "kalshi"
    assert feed.get("kalshi", "DOES-NOT-EXIST") is None


def test_fake_feed_has_cross_venue_pair() -> None:
    feed = FakeFeed()
    assert feed.get("kalshi", "ELECTION-2028") is not None
    assert feed.get("polymarket", "ELECTION-2028") is not None


def test_fake_feed_prices_within_bounds() -> None:
    for m in FakeFeed().markets():
        for price in (m.yes_bid, m.yes_ask, m.no_bid, m.no_ask):
            assert 1 <= price <= 99


def test_live_feed_construct_without_network() -> None:
    feed = LiveFeed(base_url="https://example.invalid", api_key="x")
    assert isinstance(feed, MarketFeed)
    assert feed.base_url == "https://example.invalid"


def test_live_feed_markets_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        LiveFeed().markets()
