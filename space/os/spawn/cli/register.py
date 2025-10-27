"""Register agent command."""

import typer

from space.os.spawn import api


def register(
    identity: str,
    model: str = typer.Option(
        ..., "--model", "-m", help="Model ID. Run 'spawn models' to list available models"
    ),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename (e.g., zealot.md) - optional"
    ),
):
    """Register a new agent."""
    try:
        agent_id = api.register_agent(identity, model, constitution)
        typer.echo(f"✓ Registered {identity} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e
