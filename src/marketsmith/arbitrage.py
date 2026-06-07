"""Arbitrage detection for prediction markets.

Two flavours are supported:

* **Single-market** - on one venue, if the YES ask plus the NO ask is below the
  100-cent payout (after fees), you can buy both sides and lock in a profit
  regardless of how the market resolves.
* **Cross-venue** - the same underlying question is cheaper to bet YES on one
  venue and NO on another; combining them for under 100 cents (after fees)
  locks in a profit.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from marketsmith.models import Market

PAYOUT_CENTS = 100.0


@dataclass(frozen=True)
class ArbitrageOpportunity:
    """A detected risk-free (after-fee) opportunity.

    ``profit_cents`` is the locked-in profit per matched YES+NO pair of contracts,
    after fees, expressed in cents.
    """

    kind: str  # "single-venue" or "cross-venue"
    description: str
    yes_leg: str  # "venue:ticker" bought as YES
    no_leg: str  # "venue:ticker" bought as NO
    cost_cents: float
    profit_cents: float

    @property
    def roi(self) -> float:
        """Return on the combined cost (profit / cost)."""
        return self.profit_cents / self.cost_cents if self.cost_cents else 0.0


def _all_in(price_cents: int, fee_fraction: float) -> float:
    return price_cents * (1.0 + fee_fraction)


def single_market_arbitrage(
    market: Market,
    fee_fraction: float = 0.0,
) -> ArbitrageOpportunity | None:
    """Detect a YES+NO < payout lock on a single market (after fees).

    Returns ``None`` when no profitable lock exists.
    """
    cost = _all_in(market.yes_ask, fee_fraction) + _all_in(market.no_ask, fee_fraction)
    profit = PAYOUT_CENTS - cost
    if profit <= 0:
        return None
    return ArbitrageOpportunity(
        kind="single-venue",
        description=(
            f"Buy YES @ {market.yes_ask}c and NO @ {market.no_ask}c on "
            f"{market.venue} '{market.ticker}' for {cost:.2f}c total"
        ),
        yes_leg=market.key(),
        no_leg=market.key(),
        cost_cents=cost,
        profit_cents=profit,
    )


def cross_venue_arbitrage(
    a: Market,
    b: Market,
    fee_fraction: float = 0.0,
) -> ArbitrageOpportunity | None:
    """Detect the cheapest cross-venue YES/NO lock between two markets.

    Considers both directions (YES on ``a`` + NO on ``b``, and YES on ``b`` +
    NO on ``a``) and returns the more profitable lock, or ``None``.
    """
    forward_cost = _all_in(a.yes_ask, fee_fraction) + _all_in(b.no_ask, fee_fraction)
    reverse_cost = _all_in(b.yes_ask, fee_fraction) + _all_in(a.no_ask, fee_fraction)

    best: ArbitrageOpportunity | None = None
    for yes_mkt, no_mkt, cost in (
        (a, b, forward_cost),
        (b, a, reverse_cost),
    ):
        profit = PAYOUT_CENTS - cost
        if profit <= 0:
            continue
        candidate = ArbitrageOpportunity(
            kind="cross-venue",
            description=(
                f"Buy YES @ {yes_mkt.yes_ask}c on {yes_mkt.venue} and "
                f"NO @ {no_mkt.no_ask}c on {no_mkt.venue} for {cost:.2f}c total"
            ),
            yes_leg=yes_mkt.key(),
            no_leg=no_mkt.key(),
            cost_cents=cost,
            profit_cents=profit,
        )
        if best is None or candidate.profit_cents > best.profit_cents:
            best = candidate
    return best


def _question_signature(question: str) -> str:
    """Normalise a question for cross-venue matching."""
    return "".join(ch.lower() for ch in question if ch.isalnum())


def find_arbitrage(
    markets: Iterable[Market],
    fee_fraction: float = 0.0,
    min_profit_cents: float = 0.0,
) -> list[ArbitrageOpportunity]:
    """Scan markets for all arbitrage opportunities above ``min_profit_cents``.

    Cross-venue matches are formed by grouping markets whose normalised question
    text is identical across different venues.

    Returns opportunities sorted by descending profit.
    """
    market_list: Sequence[Market] = list(markets)
    found: list[ArbitrageOpportunity] = []

    for market in market_list:
        single = single_market_arbitrage(market, fee_fraction)
        if single is not None and single.profit_cents >= min_profit_cents:
            found.append(single)

    by_question: dict[str, list[Market]] = {}
    for market in market_list:
        by_question.setdefault(_question_signature(market.question), []).append(market)

    for group in by_question.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.venue == b.venue:
                    continue
                opp = cross_venue_arbitrage(a, b, fee_fraction)
                if opp is not None and opp.profit_cents >= min_profit_cents:
                    found.append(opp)

    found.sort(key=lambda o: o.profit_cents, reverse=True)
    return found
