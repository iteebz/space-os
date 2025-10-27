"""Launch guide for new space-os users."""

from pathlib import Path

import typer


def launch():
    """Display the space-os manual (instruction set for agents and humans)."""
    manual_path = Path(__file__).parent.parent.parent.parent.parent / "MANUAL.md"

    if not manual_path.exists():
        typer.echo("MANUAL.md not found", err=True)
        raise typer.Exit(code=1)

    with open(manual_path) as f:
        typer.echo(f.read())
