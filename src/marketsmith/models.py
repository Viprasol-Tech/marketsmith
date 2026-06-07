"""Domain models for prediction markets.

Prices are quoted in **cents** (1-99) for a binary YES/NO contract, matching the
convention used by venues such as Kalshi and Polymarket. A YES contract that
settles true pays out 100 cents; a NO contract that settles true pays out 100
cents. The mid-price of a YES contract, divided by 100, is the market-implied
probability of the YES outcome.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Market(BaseModel):
    """A single binary prediction market quoted in cents.

    Attributes:
        venue: Marketplace the contract trades on (e.g. ``"kalshi"``).
        ticker: Venue-specific contract identifier.
        question: Human-readable resolution question.
        yes_bid: Best bid for the YES contract, in cents (1-99).
        yes_ask: Best ask for the YES contract, in cents (1-99).
        no_bid: Best bid for the NO contract, in cents (1-99).
        no_ask: Best ask for the NO contract, in cents (1-99).
        volume: Number of contracts traded.
    """

    model_config = {"frozen": True}

    venue: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    question: str = Field(min_length=1)
    yes_bid: int = Field(ge=1, le=99)
    yes_ask: int = Field(ge=1, le=99)
    no_bid: int = Field(ge=1, le=99)
    no_ask: int = Field(ge=1, le=99)
    volume: int = Field(ge=0, default=0)

    @model_validator(mode="after")
    def _check_spreads(self) -> Market:
        if self.yes_bid > self.yes_ask:
            raise ValueError(f"yes_bid ({self.yes_bid}) must not exceed yes_ask ({self.yes_ask})")
        if self.no_bid > self.no_ask:
            raise ValueError(f"no_bid ({self.no_bid}) must not exceed no_ask ({self.no_ask})")
        return self

    @property
    def yes_mid(self) -> float:
        """Mid-price of the YES contract, in cents."""
        return (self.yes_bid + self.yes_ask) / 2.0

    @property
    def no_mid(self) -> float:
        """Mid-price of the NO contract, in cents."""
        return (self.no_bid + self.no_ask) / 2.0

    def key(self) -> str:
        """Stable ``venue:ticker`` identifier."""
        return f"{self.venue}:{self.ticker}"
