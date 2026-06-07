"""The tool functions exposed over MCP.

Every function here is plain, typed Python that takes JSON-friendly arguments and
returns a JSON-serialisable ``dict``. They depend only on the pure analytics,
arbitrage, and feed modules - never on the MCP SDK - so they are fully unit
testable and reusable as a normal library.

:func:`marketsmith.server` registers each of these as an MCP tool.
"""

from __future__ import annotations

from typing import Any

from marketsmith import analytics
from marketsmith.arbitrage import find_arbitrage
from marketsmith.feed import FakeFeed, MarketFeed
from marketsmith.models import Market

#: Default trading fee (fraction of notional) used when a caller omits one.
DEFAULT_FEE_FRACTION = 0.0


def _default_feed() -> MarketFeed:
    return FakeFeed()


def _market_to_dict(market: Market) -> dict[str, Any]:
    return {
        "venue": market.venue,
        "ticker": market.ticker,
        "question": market.question,
        "yes_bid": market.yes_bid,
        "yes_ask": market.yes_ask,
        "no_bid": market.no_bid,
        "no_ask": market.no_ask,
        "volume": market.volume,
        "yes_implied_probability": round(analytics.implied_probability(market.yes_mid), 4),
    }


def search_markets(query: str, feed: MarketFeed | None = None) -> dict[str, Any]:
    """Search markets whose question, ticker, or venue contains ``query``.

    Args:
        query: Case-insensitive keyword. Empty string returns all markets.
        feed: Feed to query (defaults to the bundled :class:`FakeFeed`).

    Returns:
        ``{"query", "count", "results": [market, ...]}``.
    """
    feed = feed or _default_feed()
    needle = query.strip().lower()
    results = [
        _market_to_dict(m)
        for m in feed.markets()
        if not needle
        or needle in m.question.lower()
        or needle in m.ticker.lower()
        or needle in m.venue.lower()
    ]
    return {"query": query, "count": len(results), "results": results}


def get_odds(venue: str, ticker: str, feed: MarketFeed | None = None) -> dict[str, Any]:
    """Return live odds and implied probability for a single market.

    Args:
        venue: Marketplace identifier (e.g. ``"kalshi"``).
        ticker: Contract ticker.
        feed: Feed to query (defaults to the bundled :class:`FakeFeed`).

    Returns:
        Quote plus implied YES/NO probabilities, or ``{"error": ...}`` if the
        market is not found.
    """
    feed = feed or _default_feed()
    market = feed.get(venue, ticker)
    if market is None:
        return {"error": f"market not found: {venue}:{ticker}"}
    return {
        "venue": market.venue,
        "ticker": market.ticker,
        "question": market.question,
        "yes_bid": market.yes_bid,
        "yes_ask": market.yes_ask,
        "no_bid": market.no_bid,
        "no_ask": market.no_ask,
        "yes_mid": market.yes_mid,
        "no_mid": market.no_mid,
        "yes_implied_probability": round(analytics.implied_probability(market.yes_mid), 4),
        "no_implied_probability": round(analytics.implied_probability(market.no_mid), 4),
        "volume": market.volume,
    }


def find_arbitrage_tool(
    min_profit: float = 0.0,
    fee_fraction: float = DEFAULT_FEE_FRACTION,
    feed: MarketFeed | None = None,
) -> dict[str, Any]:
    """Find single- and cross-venue arbitrage opportunities.

    Args:
        min_profit: Minimum locked-in profit in cents to report.
        fee_fraction: Trading fee as a fraction of each contract's price.
        feed: Feed to scan (defaults to the bundled :class:`FakeFeed`).

    Returns:
        ``{"min_profit", "fee_fraction", "count", "opportunities": [...]}``.
    """
    feed = feed or _default_feed()
    opps = find_arbitrage(
        feed.markets(),
        fee_fraction=fee_fraction,
        min_profit_cents=min_profit,
    )
    return {
        "min_profit": min_profit,
        "fee_fraction": fee_fraction,
        "count": len(opps),
        "opportunities": [
            {
                "kind": o.kind,
                "description": o.description,
                "yes_leg": o.yes_leg,
                "no_leg": o.no_leg,
                "cost_cents": round(o.cost_cents, 4),
                "profit_cents": round(o.profit_cents, 4),
                "roi": round(o.roi, 4),
            }
            for o in opps
        ],
    }


def compute_ev(
    venue: str,
    ticker: str,
    your_probability: float,
    fee_fraction: float = DEFAULT_FEE_FRACTION,
    feed: MarketFeed | None = None,
) -> dict[str, Any]:
    """Compute the edge of betting YES given your own probability estimate.

    Args:
        venue: Marketplace identifier.
        ticker: Contract ticker.
        your_probability: Your estimate that YES pays out, in ``[0, 1]``.
        fee_fraction: Trading fee as a fraction of the contract price.
        feed: Feed to query (defaults to the bundled :class:`FakeFeed`).

    Returns:
        Edge metrics, or ``{"error": ...}`` if the market is not found.
    """
    feed = feed or _default_feed()
    market = feed.get(venue, ticker)
    if market is None:
        return {"error": f"market not found: {venue}:{ticker}"}
    report = analytics.edge_report(your_probability, market.yes_ask, fee_fraction)
    return {
        "venue": market.venue,
        "ticker": market.ticker,
        "side": "YES",
        "entry_price_cents": market.yes_ask,
        "your_probability": round(report.your_probability, 4),
        "implied_probability": round(report.implied_probability, 4),
        "edge": round(report.edge, 4),
        "break_even_probability": round(report.break_even_probability, 4),
        "expected_value_cents": round(report.expected_value_cents, 4),
        "kelly_fraction": round(report.kelly_fraction, 4),
        "favorable": report.is_favorable(),
    }


def suggest_kelly(
    venue: str,
    ticker: str,
    your_probability: float,
    bankroll: float,
    fee_fraction: float = DEFAULT_FEE_FRACTION,
    kelly_multiplier: float = 1.0,
    feed: MarketFeed | None = None,
) -> dict[str, Any]:
    """Suggest a Kelly-sized stake for betting YES on a market.

    Args:
        venue: Marketplace identifier.
        ticker: Contract ticker.
        your_probability: Your estimate that YES pays out, in ``[0, 1]``.
        bankroll: Capital available, in account currency.
        fee_fraction: Trading fee as a fraction of the contract price.
        kelly_multiplier: Scale on full Kelly (e.g. ``0.5`` for half-Kelly).
        feed: Feed to query (defaults to the bundled :class:`FakeFeed`).

    Returns:
        Kelly fraction and recommended stake, or ``{"error": ...}``.
    """
    feed = feed or _default_feed()
    market = feed.get(venue, ticker)
    if market is None:
        return {"error": f"market not found: {venue}:{ticker}"}
    frac = analytics.kelly_fraction(your_probability, market.yes_ask, fee_fraction)
    stake = analytics.kelly_stake(
        your_probability,
        market.yes_ask,
        bankroll,
        fee_fraction=fee_fraction,
        kelly_multiplier=kelly_multiplier,
    )
    return {
        "venue": market.venue,
        "ticker": market.ticker,
        "side": "YES",
        "entry_price_cents": market.yes_ask,
        "your_probability": round(your_probability, 4),
        "bankroll": bankroll,
        "kelly_fraction": round(frac, 4),
        "kelly_multiplier": kelly_multiplier,
        "recommended_stake": round(stake, 4),
    }


#: Metadata describing every exposed tool. Used by the CLI ``tools`` command and
#: by the MCP server for registration/documentation. The ``fn`` is the callable.
TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "search_markets",
        "fn": search_markets,
        "summary": "Search prediction markets by keyword.",
        "params": "query: str",
        "returns": "Matching markets with implied probabilities.",
    },
    {
        "name": "get_odds",
        "fn": get_odds,
        "summary": "Live odds and implied probability for one market.",
        "params": "venue: str, ticker: str",
        "returns": "Bid/ask, mids, and YES/NO implied probabilities.",
    },
    {
        "name": "find_arbitrage",
        "fn": find_arbitrage_tool,
        "summary": "Fee-adjusted single- and cross-venue arbitrage scan.",
        "params": "min_profit: float = 0.0, fee_fraction: float = 0.0",
        "returns": "Locked-in opportunities sorted by profit.",
    },
    {
        "name": "compute_ev",
        "fn": compute_ev,
        "summary": "Expected value and edge of betting YES.",
        "params": "venue: str, ticker: str, your_probability: float",
        "returns": "Edge, break-even, EV (cents), and Kelly fraction.",
    },
    {
        "name": "suggest_kelly",
        "fn": suggest_kelly,
        "summary": "Kelly-criterion stake suggestion for a bankroll.",
        "params": "venue: str, ticker: str, your_probability: float, bankroll: float",
        "returns": "Kelly fraction and recommended stake.",
    },
]
