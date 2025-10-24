import typer

from space.os import events


def errors(
    limit: int = typer.Option(20, help="Number of errors to show"),
    identity: str = typer.Option(None, "--as", help="Filter by identity"),
):
    """Show recent errors from events log."""
    from space.os.spawn import db as spawn_db

    agent_id = spawn_db.get_agent_id(identity) if identity else None

    error_events = events.query(source=None, agent_id=agent_id, limit=1000)
    errors_only = [e for e in error_events if e[3] == "error"][:limit]

    if not errors_only:
        typer.echo("No errors logged")
        return

    typer.echo(f"Last {len(errors_only)} errors:\n")
    for event in errors_only:
        event_id, source, event_agent_id, event_type, data, timestamp = event
        agent_name = spawn_db.get_identity(event_agent_id) if event_agent_id else "system"
        typer.echo(f"[{source}] {agent_name}: {data}")
