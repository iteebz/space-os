import json

import typer

from space.os.spawn import db as spawn_db

from ... import events
from .. import api, utils

app = typer.Typer()


@app.command()
def notes(
    channel: str = typer.Argument(...),
    content: str | None = typer.Argument(None),
    identity: str | None = typer.Option(
        None, "--as", help="Your agent identity (claude/gemini/codex)"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show notes for channel, or add note with content and --as identity."""
    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    if content is None:
        try:
            if agent_id:
                events.emit("bridge", "notes_viewing", agent_id, json.dumps({"channel": channel}))
            channel_id = api.resolve_channel_id(channel)
            notes = api.get_notes(channel_id)
            if agent_id:
                events.emit(
                    "bridge",
                    "notes_viewed",
                    agent_id,
                    json.dumps({"channel": channel, "count": len(notes)}),
                )
            if not notes:
                if json_output:
                    typer.echo(json.dumps([]))
                elif not quiet_output:
                    typer.echo(f"No notes for channel: {channel}")
                return

            if json_output:
                typer.echo(
                    json.dumps(
                        [note.__dict__ if hasattr(note, "__dict__") else note for note in notes]
                    )
                )
            elif not quiet_output:
                typer.echo(f"Notes for {channel}:")
                for note in notes:
                    note_dict = note.__dict__ if hasattr(note, "__dict__") else note
                    timestamp = utils.format_local_time(note_dict["created_at"])
                    agent_id = note_dict.get("agent_id")
                    identity_str = spawn_db.get_identity(agent_id) if agent_id else "unknown"
                    typer.echo(f"[{timestamp}] {identity_str}: {note_dict['content']}")
                    typer.echo()
        except ValueError as e:
            if agent_id:
                events.emit(
                    "bridge",
                    "error",
                    agent_id,
                    json.dumps({"command": "notes", "details": str(e)}),
                )
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
            events.emit(
                "bridge",
                "note_adding",
                agent_id,
                json.dumps({"channel": channel, "identity": identity}),
            )
            channel_id = api.resolve_channel_id(channel)
            api.add_note(channel_id, identity, content)
            events.emit(
                "bridge",
                "note_added",
                agent_id,
                json.dumps({"channel": channel, "identity": identity}),
            )
            if json_output:
                typer.echo(
                    json.dumps({"status": "success", "channel": channel, "identity": identity})
                )
            elif not quiet_output:
                typer.echo(f"Added note to {channel}")
        except ValueError as e:
            events.emit(
                "bridge",
                "error",
                agent_id,
                json.dumps({"command": "notes", "details": str(e)}),
            )
            if json_output:
                typer.echo(
                    json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
            raise typer.Exit(code=1) from e
