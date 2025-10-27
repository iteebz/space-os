"""Create a channel."""

from __future__ import annotations

import typer

from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def create(
        ctx: typer.Context,
        channel_name: str = typer.Argument(..., help="Channel name"),
        topic: str = typer.Option(None, help="Channel topic"),
    ):
        """Create a channel."""
        try:
            channel_id = ops.create_channel(channel_name, topic)
            output_json(
                {"status": "success", "channel_name": channel_name, "channel_id": channel_id}, ctx
            ) or echo_if_output(f"Created channel: {channel_name} (ID: {channel_id})", ctx)
        except ValueError as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ Error creating channel: {e}", ctx
            )
            raise typer.Exit(code=1) from e
