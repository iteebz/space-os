"""Delete a channel."""

from __future__ import annotations

import typer

from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def delete(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Channel to delete"),
    ):
        """Delete a channel."""
        try:
            ops.delete_channel(channel)
            output_json({"status": "deleted", "channel": channel}, ctx) or echo_if_output(
                f"Deleted channel: {channel}", ctx
            )
        except ValueError as e:
            output_json(
                {"status": "error", "message": f"Channel '{channel}' not found."}, ctx
            ) or echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
            raise typer.Exit(code=1) from e
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
