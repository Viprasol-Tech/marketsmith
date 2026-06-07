"""Command-line interface for marketsmith.

Commands:

* ``marketsmith serve``   - start the MCP server over stdio (needs ``[server]``).
* ``marketsmith tools``   - list the exposed MCP tools and their schemas (offline).
* ``marketsmith demo``    - run each tool over the bundled FakeFeed (offline).
* ``marketsmith version`` - print the installed version.

Only ``serve`` touches the optional ``mcp`` dependency, and it imports it lazily,
so ``tools``, ``demo``, and ``version`` work with the base install alone.
"""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from marketsmith import __version__, tools

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="MCP server for prediction markets - give your AI agent an edge.",
)
console = Console()


@app.command()
def version() -> None:
    """Print the marketsmith version."""
    console.print(f"marketsmith {__version__}")


@app.command(name="tools")
def list_tools() -> None:
    """List the MCP tools this server exposes (works offline)."""
    table = Table(title="marketsmith MCP tools", header_style="bold cyan")
    table.add_column("Tool", style="bold")
    table.add_column("Parameters")
    table.add_column("Returns")
    for spec in tools.TOOL_SPECS:
        table.add_row(spec["name"], spec["params"], spec["returns"])
    console.print(table)
    console.print(
        "\nAdd to an MCP client by running [bold]marketsmith serve[/bold] "
        '(requires [bold]pip install "marketsmith\\[server]"[/bold]).'
    )


def _print_result(title: str, result: dict[str, Any]) -> None:
    body = json.dumps(result, indent=2)
    console.print(Panel(body, title=title, border_style="green", expand=False))


@app.command()
def demo() -> None:
    """Run every tool over the bundled FakeFeed and print the results (offline)."""
    console.print(
        Panel(
            "Running each marketsmith tool over the deterministic FakeFeed.\n"
            "No network access required.",
            title="marketsmith demo",
            border_style="cyan",
            expand=False,
        )
    )

    _print_result(
        "search_markets(query='election')",
        tools.search_markets("election"),
    )
    _print_result(
        "get_odds(venue='kalshi', ticker='ELECTION-2028')",
        tools.get_odds("kalshi", "ELECTION-2028"),
    )
    _print_result(
        "find_arbitrage(min_profit=1.0)",
        tools.find_arbitrage_tool(min_profit=1.0),
    )
    _print_result(
        "compute_ev(venue='kalshi', ticker='ELECTION-2028', your_probability=0.6)",
        tools.compute_ev("kalshi", "ELECTION-2028", 0.6),
    )
    _print_result(
        "suggest_kelly(venue='kalshi', ticker='ELECTION-2028', "
        "your_probability=0.6, bankroll=1000)",
        tools.suggest_kelly("kalshi", "ELECTION-2028", 0.6, 1000.0),
    )

    console.print(
        "[dim]Educational use only - not financial advice. See the README disclaimer.[/dim]"
    )


@app.command()
def serve() -> None:
    """Start the MCP server over stdio (requires the optional 'mcp' dependency)."""
    try:
        from marketsmith.server import run
    except ModuleNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print("[green]Starting marketsmith MCP server over stdio...[/green]")
    run()


if __name__ == "__main__":  # pragma: no cover
    app()
