"""The marketsmith MCP server.

This is the only module that imports the optional ``mcp`` SDK. Install it with::

    pip install "marketsmith[server]"

Then point any MCP client (Claude Desktop, Cursor, ...) at ``marketsmith serve``.
The server wraps the pure functions in :mod:`marketsmith.tools` as MCP tools, so
all of the analytics live in tested, SDK-free modules.

The import is guarded so that importing this module without the SDK installed
raises a clear, actionable error rather than a bare ``ModuleNotFoundError``.
The test suite never imports this module.
"""

from __future__ import annotations

from typing import Any

from marketsmith import tools

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without mcp
    raise ModuleNotFoundError(
        "The MCP server requires the optional 'mcp' dependency. Install it with:\n"
        '    pip install "marketsmith[server]"'
    ) from exc


def build_server() -> FastMCP:
    """Create the FastMCP server with every marketsmith tool registered."""
    mcp = FastMCP("marketsmith")

    @mcp.tool()
    def search_markets(query: str) -> dict[str, Any]:
        """Search prediction markets by keyword (question, ticker, or venue)."""
        return tools.search_markets(query)

    @mcp.tool()
    def get_odds(venue: str, ticker: str) -> dict[str, Any]:
        """Live odds and implied probability for a single market."""
        return tools.get_odds(venue, ticker)

    @mcp.tool()
    def find_arbitrage(min_profit: float = 0.0, fee_fraction: float = 0.0) -> dict[str, Any]:
        """Find fee-adjusted single- and cross-venue arbitrage opportunities."""
        return tools.find_arbitrage_tool(min_profit=min_profit, fee_fraction=fee_fraction)

    @mcp.tool()
    def compute_ev(
        venue: str,
        ticker: str,
        your_probability: float,
        fee_fraction: float = 0.0,
    ) -> dict[str, Any]:
        """Expected value, edge, break-even, and Kelly for betting YES."""
        return tools.compute_ev(venue, ticker, your_probability, fee_fraction=fee_fraction)

    @mcp.tool()
    def suggest_kelly(
        venue: str,
        ticker: str,
        your_probability: float,
        bankroll: float,
        fee_fraction: float = 0.0,
        kelly_multiplier: float = 1.0,
    ) -> dict[str, Any]:
        """Kelly-criterion stake suggestion for a given bankroll."""
        return tools.suggest_kelly(
            venue,
            ticker,
            your_probability,
            bankroll,
            fee_fraction=fee_fraction,
            kelly_multiplier=kelly_multiplier,
        )

    return mcp


def run() -> None:
    """Run the MCP server over stdio (the transport MCP clients expect)."""
    build_server().run()


if __name__ == "__main__":  # pragma: no cover
    run()
