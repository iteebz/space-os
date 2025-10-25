"""Export command."""

import json
from dataclasses import asdict
from datetime import datetime

import typer

from space.os import events
from space.os.core import spawn
from .. import channels, export as ex

app = typer.Typer()


@app.command("export")
def export_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Export channel transcript."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")
    
    agent_id = spawn.db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit("bridge", "export_starting", agent_id, json.dumps({"channel": channel}))
        channel_id = channels.resolve_channel_id(channel)
        data = ex.get_export_data(channel_id)

        if json_output:
            export_data_dict = asdict(data)
            export_data_dict["participants"] = [
                spawn.db.get_agent_name(p) or p for p in data.participants
            ]
            for msg in export_data_dict["messages"]:
                msg["agent_id"] = spawn.db.get_agent_name(msg["agent_id"]) or msg["agent_id"]
            for note in export_data_dict["notes"]:
                note["agent_id"] = spawn.db.get_agent_name(note["agent_id"]) or note["agent_id"]
            typer.echo(json.dumps(export_data_dict, indent=2))
        elif not quiet_output:
            typer.echo(f"# {data.channel_name}")
            typer.echo()
            if data.topic:
                typer.echo(f"Topic: {data.topic}")
                typer.echo()
            participant_names = [spawn.db.get_agent_name(p) or p for p in data.participants]
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
                    sender_name = spawn.db.get_agent_name(item.agent_id) or item.agent_id
                    typer.echo(f"[{sender_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
                else:
                    author_name = spawn.db.get_agent_name(item.agent_id) or item.agent_id
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
