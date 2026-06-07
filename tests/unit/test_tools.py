from __future__ import annotations

import json

import pytest

from marketsmith import tools
from marketsmith.feed import FakeFeed


def _json_serializable(obj: object) -> None:
    json.dumps(obj)


def test_search_markets_finds_by_keyword() -> None:
    result = tools.search_markets("election")
    assert result["query"] == "election"
    assert result["count"] >= 2
    tickers = {r["ticker"] for r in result["results"]}
    assert tickers == {"ELECTION-2028"}
    _json_serializable(result)


def test_search_markets_matches_venue() -> None:
    result = tools.search_markets("polymarket")
    assert result["count"] >= 1
    assert all(r["venue"] == "polymarket" for r in result["results"])


def test_search_markets_empty_returns_all() -> None:
    result = tools.search_markets("")
    assert result["count"] == len(FakeFeed().markets())


def test_search_markets_no_match() -> None:
    result = tools.search_markets("zzz-nothing-here")
    assert result["count"] == 0
    assert result["results"] == []


def test_search_results_include_implied_probability() -> None:
    result = tools.search_markets("election")
    for r in result["results"]:
        assert 0.0 < r["yes_implied_probability"] < 1.0


def test_get_odds_returns_implied_probability() -> None:
    result = tools.get_odds("kalshi", "ELECTION-2028")
    assert "error" not in result
    # YES mid = (45 + 47) / 2 = 46 -> 0.46.
    assert result["yes_mid"] == pytest.approx(46.0)
    assert result["yes_implied_probability"] == pytest.approx(0.46)
    assert result["no_implied_probability"] == pytest.approx(0.54)
    _json_serializable(result)


def test_get_odds_missing_market() -> None:
    result = tools.get_odds("kalshi", "NOPE")
    assert "error" in result


def test_find_arbitrage_returns_seeded_arb() -> None:
    result = tools.find_arbitrage_tool(min_profit=1.0)
    assert result["count"] >= 2
    kinds = {o["kind"] for o in result["opportunities"]}
    assert "cross-venue" in kinds
    assert "single-venue" in kinds
    _json_serializable(result)


def test_find_arbitrage_election_profit() -> None:
    result = tools.find_arbitrage_tool(min_profit=1.0)
    cross = [
        o
        for o in result["opportunities"]
        if o["kind"] == "cross-venue" and "ELECTION-2028" in o["yes_leg"]
    ]
    assert cross
    assert cross[0]["profit_cents"] == pytest.approx(4.0)


def test_find_arbitrage_fee_param_passed_through() -> None:
    result = tools.find_arbitrage_tool(min_profit=0.0, fee_fraction=0.5)
    assert result["fee_fraction"] == 0.5
    # A 50% fee wipes out every small lock.
    assert result["count"] == 0


def test_compute_ev_correct() -> None:
    # YES ask on ELECTION-2028 (kalshi) is 47c. your_prob 0.6:
    # EV = 0.6 * 100 - 47 = 13c; edge = 0.6 - 0.47 = 0.13.
    result = tools.compute_ev("kalshi", "ELECTION-2028", 0.6)
    assert result["entry_price_cents"] == 47
    assert result["implied_probability"] == pytest.approx(0.47)
    assert result["edge"] == pytest.approx(0.13)
    assert result["expected_value_cents"] == pytest.approx(13.0)
    assert result["favorable"] is True
    _json_serializable(result)


def test_compute_ev_unfavorable() -> None:
    result = tools.compute_ev("kalshi", "ELECTION-2028", 0.3)
    assert result["expected_value_cents"] < 0
    assert result["favorable"] is False


def test_compute_ev_missing_market() -> None:
    assert "error" in tools.compute_ev("kalshi", "NOPE", 0.5)


def test_suggest_kelly_correct() -> None:
    # YES ask 47c, b = 53/47. p = 0.6:
    # f = (b*0.6 - 0.4)/b. Verify stake = bankroll * f.
    result = tools.suggest_kelly("kalshi", "ELECTION-2028", 0.6, 1000.0)
    b = 53.0 / 47.0
    expected_f = (b * 0.6 - 0.4) / b
    assert result["kelly_fraction"] == pytest.approx(round(expected_f, 4))
    assert result["recommended_stake"] == pytest.approx(round(1000.0 * expected_f, 4))
    _json_serializable(result)


def test_suggest_kelly_half_kelly() -> None:
    full = tools.suggest_kelly("kalshi", "ELECTION-2028", 0.6, 1000.0)
    half = tools.suggest_kelly("kalshi", "ELECTION-2028", 0.6, 1000.0, kelly_multiplier=0.5)
    assert half["recommended_stake"] == pytest.approx(full["recommended_stake"] / 2.0)


def test_suggest_kelly_no_edge_zero_stake() -> None:
    # Implied prob of YES ask 47 is 0.47; betting at 0.40 has no edge -> 0 stake.
    result = tools.suggest_kelly("kalshi", "ELECTION-2028", 0.40, 1000.0)
    assert result["recommended_stake"] == pytest.approx(0.0)


def test_suggest_kelly_missing_market() -> None:
    assert "error" in tools.suggest_kelly("kalshi", "NOPE", 0.5, 1000.0)


def test_tool_specs_cover_all_functions() -> None:
    names = {spec["name"] for spec in tools.TOOL_SPECS}
    assert names == {
        "search_markets",
        "get_odds",
        "find_arbitrage",
        "compute_ev",
        "suggest_kelly",
    }
    for spec in tools.TOOL_SPECS:
        assert callable(spec["fn"])
