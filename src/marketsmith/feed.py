"""Market data feeds.

:class:`MarketFeed` is the protocol the rest of the package depends on. Two
implementations ship with marketsmith:

* :class:`FakeFeed` - a deterministic set of synthetic markets used for the demo
  and the test suite. It deliberately includes a genuine cross-venue arbitrage
  and a couple of mispriced markets so the analytics have something to find.
* :class:`LiveFeed` - a documented stub that would talk to a real venue's REST
  API. It performs no network I/O until :meth:`LiveFeed.markets` is called, so it
  is safe to import and construct in tests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from marketsmith.models import Market


@runtime_checkable
class MarketFeed(Protocol):
    """Source of prediction-market quotes."""

    def markets(self) -> list[Market]:
        """Return the current set of markets."""
        ...

    def get(self, venue: str, ticker: str) -> Market | None:
        """Return a single market by venue and ticker, or ``None``."""
        ...


def _index(markets: list[Market]) -> dict[str, Market]:
    return {m.key(): m for m in markets}


class FakeFeed:
    """Deterministic in-memory feed of synthetic markets.

    The same nine markets are returned on every call in a stable order, which
    makes the demo reproducible and the tests assertable. Highlights:

    * ``ELECTION-2028`` exists on both ``kalshi`` and ``polymarket`` with a real
      cross-venue arbitrage (buy YES on kalshi @ 47c, NO on polymarket @ 49c =
      96c for a guaranteed 100c payout).
    * ``FED-CUT-MAR`` is a single-venue lock (YES 48c + NO 49c = 97c).
    * The remaining markets are ordinary, mispriced relative to a "fair" view.
    """

    def __init__(self) -> None:
        self._markets: list[Market] = _build_synthetic_markets()
        self._by_key = _index(self._markets)

    def markets(self) -> list[Market]:
        return list(self._markets)

    def get(self, venue: str, ticker: str) -> Market | None:
        return self._by_key.get(f"{venue}:{ticker}")


class LiveFeed:
    """Stub for a real venue feed (no network I/O until :meth:`markets`).

    This is intentionally not wired to a live API in the open-source build. To
    implement it, fetch the venue order book in :meth:`markets` and map each
    contract onto :class:`~marketsmith.models.Market`, converting prices to cents.

    Example skeleton::

        import httpx

        class LiveFeed:
            def __init__(self, base_url: str, api_key: str) -> None:
                self.base_url = base_url
                self.api_key = api_key

            def markets(self) -> list[Market]:
                resp = httpx.get(f"{self.base_url}/markets",
                                 headers={"Authorization": f"Bearer {self.api_key}"})
                resp.raise_for_status()
                return [_parse(row) for row in resp.json()["markets"]]
    """

    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        self.base_url = base_url
        self.api_key = api_key

    def markets(self) -> list[Market]:  # pragma: no cover - network stub
        raise NotImplementedError(
            "LiveFeed is a stub in the open-source build. Implement markets() to "
            "fetch quotes from a real venue, or use FakeFeed for offline demos."
        )

    def get(self, venue: str, ticker: str) -> Market | None:  # pragma: no cover
        for market in self.markets():
            if market.venue == venue and market.ticker == ticker:
                return market
        return None


def _build_synthetic_markets() -> list[Market]:
    return [
        # --- Real cross-venue arbitrage on the same question -----------------
        Market(
            venue="kalshi",
            ticker="ELECTION-2028",
            question="Will the incumbent party win the 2028 election?",
            yes_bid=45,
            yes_ask=47,
            no_bid=53,
            no_ask=55,
            volume=182_340,
        ),
        Market(
            venue="polymarket",
            ticker="ELECTION-2028",
            question="Will the incumbent party win the 2028 election?",
            yes_bid=49,
            yes_ask=51,
            no_bid=47,
            no_ask=49,
            volume=240_115,
        ),
        # --- Single-venue lock: YES 48 + NO 49 = 97c < 100c ------------------
        Market(
            venue="kalshi",
            ticker="FED-CUT-MAR",
            question="Will the Fed cut rates in March?",
            yes_bid=46,
            yes_ask=48,
            no_bid=47,
            no_ask=49,
            volume=98_220,
        ),
        # --- Ordinary, no-arb markets (some mispriced vs a fair view) --------
        Market(
            venue="kalshi",
            ticker="CPI-ABOVE-3",
            question="Will annual CPI be above 3% next print?",
            yes_bid=61,
            yes_ask=63,
            no_bid=37,
            no_ask=39,
            volume=54_900,
        ),
        Market(
            venue="polymarket",
            ticker="BTC-100K-EOY",
            question="Will Bitcoin close above $100k this year?",
            yes_bid=70,
            yes_ask=72,
            no_bid=28,
            no_ask=30,
            volume=311_500,
        ),
        Market(
            venue="kalshi",
            ticker="SUPERBOWL-AFC",
            question="Will an AFC team win the Super Bowl?",
            yes_bid=52,
            yes_ask=54,
            no_bid=46,
            no_ask=48,
            volume=129_870,
        ),
        Market(
            venue="polymarket",
            ticker="OSCARS-BESTPIC-A24",
            question="Will an A24 film win Best Picture?",
            yes_bid=18,
            yes_ask=20,
            no_bid=80,
            no_ask=82,
            volume=22_410,
        ),
        Market(
            venue="kalshi",
            ticker="GDP-RECESSION",
            question="Will the US enter a recession this year?",
            yes_bid=33,
            yes_ask=35,
            no_bid=65,
            no_ask=67,
            volume=76_640,
        ),
        Market(
            venue="polymarket",
            ticker="ETH-FLIP-BTC",
            question="Will Ethereum flip Bitcoin in market cap this year?",
            yes_bid=8,
            yes_ask=10,
            no_bid=90,
            no_ask=92,
            volume=41_330,
        ),
    ]
