import json
from datetime import datetime

import typer

from space.core import events as events_db
from space.core import spawn


def _identity_name(agent_id: str | None) -> str | None:
    if not agent_id:
        return None
    agent = spawn.get_agent(agent_id)
    return agent.name if agent else agent_id


def events(
    source: str = typer.Option(None, help="Filter by source (bridge, memory, spawn)"),
    identity: str = typer.Option(None, help="Filter by identity"),
    errors: bool = typer.Option(False, "--errors", help="Show only error events"),
    limit: int = typer.Option(50, help="Number of events to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show recent events from append-only log."""
    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    rows = events_db.query(source=source, agent_id=agent_id, limit=1000 if errors else limit)

    if errors:
        rows = [e for e in rows if e[3] == "error"][:limit]

    if not rows:
        if not quiet_output:
            typer.echo("No events found")
        if json_output:
            typer.echo(json.dumps([]))
        return

    if json_output:
        json_rows = []
        for uuid, src, aid, event_type, data, created_at in rows:
            json_rows.append(
                {
                    "uuid": uuid,
                    "source": src,
                    "identity": _identity_name(aid),
                    "event_type": event_type,
                    "data": data,
                    "created_at": datetime.fromtimestamp(created_at).isoformat(),
                }
            )
        typer.echo(json.dumps(json_rows))
    elif not quiet_output:
        for uuid, src, aid, event_type, data, created_at in rows:
            ts = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            ident = _identity_name(aid)
            ident_str = f" [{ident}]" if ident else ""
            data_str = f" {data}" if data else ""
            typer.echo(f"[{uuid[:8]}] {ts} {src}.{event_type}{ident_str}{data_str}")
