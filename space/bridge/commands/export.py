import json
from dataclasses import asdict
from datetime import datetime

import typer

from ... import events
from ...spawn import registry
from ...spawn.registry import get_agent_name
from .. import api

app = typer.Typer()


@app.command()
def export(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Export channel transcript with interleaved notes."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit("bridge", "export_starting", agent_id, json.dumps({"channel": channel}))
        data = api.export_channel(channel)

        if json_output:
            export_data = {
                "channel_name": data.channel_name,
                "topic": data.topic,
                "participants": data.participants,
                "message_count": data.message_count,
                "created_at": data.created_at,
                "messages": [asdict(msg) for msg in data.messages],
                "notes": [asdict(note) for note in data.notes],
            }
            typer.echo(json.dumps(export_data))
        elif not quiet_output:
            typer.echo(f"# {data.channel_name}")
            typer.echo()
            if data.topic:
                typer.echo(f"Topic: {data.topic}")
                typer.echo()
            participant_names = [get_agent_name(p) or p for p in data.participants]
            typer.echo(f"Participants: {', '.join(participant_names)}")
            typer.echo(f"Messages: {data.message_count}")

            if data.created_at:
                created = datetime.fromisoformat(data.created_at)
                typer.echo(f"Created: {created.strftime('%Y-%m-%d')}")

            typer.echo()
            typer.echo("---")
            typer.echo()

            combined = []
            for msg in data.messages:
                combined.append(("msg", msg))
            for note in data.notes:
                combined.append(("note", note))

            combined.sort(key=lambda x: x[1].created_at)

            for item_type, item in combined:
                created = datetime.fromisoformat(item.created_at)
                timestamp = created.strftime("%Y-%m-%d %H:%M:%S")

                if item_type == "msg":
                    sender_name = get_agent_name(item.sender) or item.sender
                    typer.echo(f"[{sender_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
                else:
                    author_name = get_agent_name(item.author) or item.author
                    typer.echo(f"[NOTE: {author_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
        if agent_id:
            events.emit(
                "bridge",
                "export_completed",
                agent_id,
                json.dumps({"channel": channel, "message_count": data.message_count}),
            )

    except ValueError as e:
        if agent_id:
            events.emit(
                "bridge",
                "error_occurred",
                agent_id,
                json.dumps({"command": "export", "details": str(e)}),
            )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from e
