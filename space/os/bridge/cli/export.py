"""Export channel messages and notes."""

from __future__ import annotations

import typer

from space.os.bridge import api

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def export(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Channel name or ID"),
    ):
        """Export channel messages and notes as markdown."""
        try:
            export_data = api.export_channel(channel)

            if output_json(
                {
                    "channel_id": export_data.channel_id,
                    "channel_name": export_data.channel_name,
                    "topic": export_data.topic,
                    "created_at": export_data.created_at,
                    "members": export_data.members,
                    "message_count": export_data.message_count,
                    "messages": [
                        {
                            "message_id": msg.message_id,
                            "agent_id": msg.agent_id,
                            "content": msg.content,
                            "created_at": msg.created_at,
                        }
                        for msg in export_data.messages
                    ],
                    "notes": [
                        {
                            "note_id": note.note_id,
                            "agent_id": note.agent_id,
                            "content": note.content,
                            "created_at": note.created_at,
                        }
                        for note in export_data.notes
                    ],
                },
                ctx,
            ):
                return

            echo_if_output(f"# {export_data.channel_name}", ctx)
            if export_data.topic:
                echo_if_output(f"\n**Topic:** {export_data.topic}", ctx)

            echo_if_output(f"\n## Messages ({export_data.message_count})", ctx)
            for msg in export_data.messages:
                echo_if_output(f"\n**{msg.agent_id}** ({msg.created_at}):", ctx)
                echo_if_output(msg.content, ctx)

            if export_data.notes:
                echo_if_output(f"\n## Notes ({len(export_data.notes)})", ctx)
                for note in export_data.notes:
                    echo_if_output(f"\n**{note.agent_id}** ({note.created_at}):", ctx)
                    echo_if_output(note.content, ctx)

        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
