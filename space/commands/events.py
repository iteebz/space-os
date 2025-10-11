import json
from datetime import datetime

import typer

from .. import events


def show_events(
    source: str = typer.Option(None, help="Filter by source (bridge, memory, spawn)"),
    identity: str = typer.Option(None, help="Filter by identity"),
    limit: int = typer.Option(50, help="Number of events to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show recent events from append-only log."""
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity) if identity else None
    rows = events.query(source=source, agent_id=agent_id, limit=limit)
    if not rows:
        if not quiet_output:
            typer.echo("No events found")
        if json_output:
            typer.echo(json.dumps([]))
        return

    if json_output:
        from ..spawn import registry

        json_rows = []
        for uuid, src, aid, event_type, data, created_at in rows:
            json_rows.append(
                {
                    "uuid": uuid,
                    "source": src,
                    "identity": registry.get_agent_name(aid) or aid,
                    "event_type": event_type,
                    "data": data,
                    "created_at": datetime.fromtimestamp(created_at).isoformat(),
                }
            )
        typer.echo(json.dumps(json_rows))
    elif not quiet_output:
        from ..spawn import registry

        for uuid, src, aid, event_type, data, created_at in rows:
            ts = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            ident_str = f" [{registry.get_agent_name(aid) or aid}]" if aid else ""
            data_str = f" {data}" if data else ""
            typer.echo(f"[{uuid[:8]}] {ts} {src}.{event_type}{ident_str}{data_str}")
