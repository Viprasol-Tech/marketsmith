"""Render the ``marketsmith demo`` output to a colored SVG for the README hero.

This reuses the real CLI demo logic by swapping the CLI module's ``console`` for
a recording :class:`rich.console.Console`, so the image matches actual output.

Run with the package importable, e.g.::

    PYTHONPATH=src python docs/make_demo.py
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from marketsmith import cli

OUTPUT = Path(__file__).resolve().parent / "assets" / "demo.svg"


def main() -> None:
    console = Console(record=True, width=100)
    # Reuse the real demo rendering by injecting the recording console.
    cli.console = console
    cli.demo()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(OUTPUT), title="marketsmith demo")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
