from __future__ import annotations

import pytest
from pydantic import ValidationError

from marketsmith.models import Market


def _valid() -> Market:
    return Market(
        venue="kalshi",
        ticker="X",
        question="Will it happen?",
        yes_bid=45,
        yes_ask=47,
        no_bid=53,
        no_ask=55,
        volume=100,
    )


def test_market_mids_and_key() -> None:
    m = _valid()
    assert m.yes_mid == pytest.approx(46.0)
    assert m.no_mid == pytest.approx(54.0)
    assert m.key() == "kalshi:X"


def test_market_is_frozen() -> None:
    m = _valid()
    with pytest.raises(ValidationError):
        m.yes_ask = 50  # type: ignore[misc]


def test_market_rejects_out_of_range_price() -> None:
    with pytest.raises(ValidationError):
        Market(
            venue="kalshi",
            ticker="X",
            question="Q?",
            yes_bid=0,
            yes_ask=47,
            no_bid=53,
            no_ask=55,
        )
    with pytest.raises(ValidationError):
        Market(
            venue="kalshi",
            ticker="X",
            question="Q?",
            yes_bid=45,
            yes_ask=100,
            no_bid=53,
            no_ask=55,
        )


def test_market_rejects_crossed_spread() -> None:
    with pytest.raises(ValidationError):
        Market(
            venue="kalshi",
            ticker="X",
            question="Q?",
            yes_bid=50,
            yes_ask=40,
            no_bid=53,
            no_ask=55,
        )


def test_market_rejects_empty_strings() -> None:
    with pytest.raises(ValidationError):
        Market(
            venue="",
            ticker="X",
            question="Q?",
            yes_bid=45,
            yes_ask=47,
            no_bid=53,
            no_ask=55,
        )


def test_market_default_volume() -> None:
    m = Market(
        venue="kalshi",
        ticker="X",
        question="Q?",
        yes_bid=45,
        yes_ask=47,
        no_bid=53,
        no_ask=55,
    )
    assert m.volume == 0
