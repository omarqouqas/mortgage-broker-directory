"""Typer CLI entry point — wired into the `mbd` console script.

Bootstrap stub. Real scrape/clean/verify commands land in Tasks 2 and beyond.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="Canadian Mortgage Broker Directory — pipeline CLI.")


@app.callback()
def _root() -> None:  # pyright: ignore[reportUnusedFunction]  # Typer requires root callback for multi-command shape
    """Forces Typer into multi-command shape even when only one command is registered.

    Prevents single-command auto-collapse so `mbd <subcommand>` is the stable
    invocation pattern as we add `scrape`, `clean`, `verify`, etc.
    """


@app.command()
def hello() -> None:
    """Smoke command — proves the console-script entry point is wired up."""
    typer.echo("mbd: bootstrap entry point is live.")


if __name__ == "__main__":
    app()
