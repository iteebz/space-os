"""Update agent command."""

import typer

from space.os.spawn import api


def update(
    identity: str,
    model: str = typer.Option(None, "--model", "-m", help="Full model name"),
    constitution: str = typer.Option(None, "--constitution", "-c", help="Constitution filename"),
):
    """Update agent fields."""
    try:
        api.update_agent(identity, constitution, model)
        typer.echo(f"✓ Updated {identity}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e
