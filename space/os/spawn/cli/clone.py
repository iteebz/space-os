"""Clone agent command."""

import typer

from space.os.spawn import api


def clone(src: str, dst: str):
    """Clone an agent with new identity."""
    try:
        agent_id = api.clone_agent(src, dst)
        typer.echo(f"✓ Cloned {src} → {dst} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e
