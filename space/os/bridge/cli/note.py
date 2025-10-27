"""View or add notes for a channel."""

from __future__ import annotations

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, format_local_time, output_json, should_output


def register(app: typer.Typer) -> None:
    @app.command()
    def note(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Channel name"),
        content: str | None = typer.Argument(None, help="Note content (omit to read)"),
        identity: str | None = typer.Option(None, "--as", help="Your agent identity"),
    ):
        """View or add notes for a channel."""
        if content is None:
            try:
                notes_list = ops.get_notes(channel)
                if not notes_list:
                    output_json([], ctx) or echo_if_output(f"No notes for channel: {channel}", ctx)
                    return

                output_json(
                    [
                        note.__dict__ if hasattr(note, "__dict__") else note
                        for note in notes_list
                    ],
                    ctx,
                ) or None
                if should_output(ctx):
                    echo_if_output(f"Notes for {channel}:", ctx)
                    for note_obj in notes_list:
                        note_dict = note_obj.__dict__ if hasattr(note_obj, "__dict__") else note_obj
                        timestamp = format_local_time(note_dict["created_at"])
                        agent_id_note = note_dict.get("agent_id")
                        identity_str = (
                            spawn.get_agent(agent_id_note).identity
                            if agent_id_note
                            else "unknown"
                        )
                        echo_if_output(
                            f"[{timestamp}] {identity_str}: {note_dict['content']}", ctx
                        )
                        echo_if_output("", ctx)
            except ValueError as e:
                output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                    f"❌ {e}", ctx
                )
                raise typer.Exit(code=1) from e
            except Exception as e:
                output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                    f"❌ {e}", ctx
                )
                raise typer.Exit(code=1) from e
        else:
            if not identity:
                output_json(
                    {"status": "error", "message": "Must specify --as identity when adding notes"},
                    ctx,
                ) or echo_if_output(
                    "❌ Must specify --as identity when adding notes", ctx
                )
                raise typer.Exit(code=1)
            try:
                agent = spawn.get_agent(identity)
                if not agent:
                    raise ValueError(f"Identity '{identity}' not registered.")
                ops.add_note(channel, agent.agent_id, content)
                output_json(
                    {"status": "success", "channel": channel, "identity": identity}, ctx
                ) or echo_if_output(f"Added note to {channel}", ctx)
            except ValueError as e:
                output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                    f"❌ {e}", ctx
                )
                raise typer.Exit(code=1) from e
            except Exception as e:
                output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                    f"❌ {e}", ctx
                )
                raise typer.Exit(code=1) from e
