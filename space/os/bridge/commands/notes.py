"""Notes command."""

import json
from datetime import datetime

import typer

from space.os import spawn

from ..api import channels
from ..api import notes as nt


def format_local_time(timestamp: str) -> str:
    """Format ISO timestamp as readable local time."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


app = typer.Typer()


@app.command("notes")
def notes_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    content: str | None = typer.Argument(None),
    identity: str | None = typer.Option(None, "--as", help="Your agent identity"),
):
    """Show notes for channel, or add note with content."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    (spawn.get_agent(identity).agent_id if identity and isinstance(identity, str) else None)
    if content is None:
        try:
            channel_id = channels.resolve_channel(channel).channel_id
            notes_list = nt.get_notes(channel_id)
            if not notes_list:
                if json_output:
                    typer.echo(json.dumps([]))
                elif not quiet_output:
                    typer.echo(f"No notes for channel: {channel}")
                return

            if json_output:
                typer.echo(
                    json.dumps(
                        [
                            note.__dict__ if hasattr(note, "__dict__") else note
                            for note in notes_list
                        ]
                    )
                )
            elif not quiet_output:
                typer.echo(f"Notes for {channel}:")
                for note in notes_list:
                    note_dict = note.__dict__ if hasattr(note, "__dict__") else note
                    timestamp = format_local_time(note_dict["created_at"])
                    agent_id_note = note_dict.get("agent_id")
                    identity_str = (
                        spawn.get_agent(agent_id_note).identity if agent_id_note else "unknown"
                    )
                    typer.echo(f"[{timestamp}] {identity_str}: {note_dict['content']}")
                    typer.echo()
        except ValueError as e:
            if json_output:
                typer.echo(
                    json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
            raise typer.Exit(code=1) from e
    else:
        if not identity:
            if json_output:
                typer.echo(
                    json.dumps(
                        {
                            "status": "error",
                            "message": "Must specify --as identity when adding notes",
                        }
                    )
                )
            elif not quiet_output:
                typer.echo("❌ Must specify --as identity when adding notes")
            raise typer.Exit(code=1)
        try:
            channel_id = channels.resolve_channel(channel).channel_id
            nt.add_note(channel_id, identity, content)
            if json_output:
                typer.echo(
                    json.dumps({"status": "success", "channel": channel, "identity": identity})
                )
            elif not quiet_output:
                typer.echo(f"Added note to {channel}")
        except ValueError as e:
            if json_output:
                typer.echo(
                    json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
            raise typer.Exit(code=1) from e
