"""Live bridge council - stream messages + type freely."""

import asyncio

import typer

from space.lib.council import Council

council = typer.Typer()


@council.command()
def join(channel: str = typer.Argument(..., help="Channel name")):
    """Join a bridge council - stream messages and respond live."""
    c = Council(channel)
    asyncio.run(c.run())


def main() -> None:
    """Entry point."""
    council()
