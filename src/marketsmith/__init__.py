"""marketsmith - an MCP server that gives your AI agent an edge in prediction markets.

The pure analytics, feed, arbitrage, and tool modules in this package never import
the MCP SDK, so they can be imported, scripted, and unit-tested without any optional
runtime dependency. The MCP server itself lives in :mod:`marketsmith.server`.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
