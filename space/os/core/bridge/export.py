import json
from dataclasses import asdict
from datetime import datetime

import typer

from space.os import events
from space.os.core.spawn import db as spawn_db

from . import api


def export(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Export channel transcript with interleaved notes."""
    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit("bridge", "export_starting", agent_id, json.dumps({"channel": channel}))
        data = api.export_channel(channel)

        if json_output:
            export_data_dict = asdict(data)
            export_data_dict["participants"] = [
                spawn_db.get_identity(p) or p for p in data.participants
            ]
            for msg in export_data_dict["messages"]:
                msg["agent_id"] = spawn_db.get_identity(msg["agent_id"]) or msg["agent_id"]
            for note in export_data_dict["notes"]:
                note["agent_id"] = spawn_db.get_identity(note["agent_id"]) or note["agent_id"]
            typer.echo(json.dumps(export_data_dict, indent=2))
        elif not quiet_output:
            typer.echo(f"# {data.channel_name}")
            typer.echo()
            if data.topic:
                typer.echo(f"Topic: {data.topic}")
                typer.echo()
            participant_names = [spawn_db.get_identity(p) or p for p in data.participants]
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
                    sender_name = spawn_db.get_identity(item.agent_id) or item.agent_id
                    typer.echo(f"[{sender_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
                else:
                    author_name = spawn_db.get_identity(item.agent_id) or item.agent_id
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
                "error",
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
