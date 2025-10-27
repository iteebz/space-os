"""Rename a channel."""

from __future__ import annotations

import typer

from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def rename(
        ctx: typer.Context,
        old_channel: str = typer.Argument(..., help="Current channel name"),
        new_channel: str = typer.Argument(..., help="New channel name"),
    ):
        """Rename a channel."""
        try:
            result = ops.rename_channel(old_channel, new_channel)
            output_json(
                {
                    "status": "success" if result else "failed",
                    "old_channel": old_channel,
                    "new_channel": new_channel,
                },
                ctx,
            ) or (
                echo_if_output(f"Renamed channel: {old_channel} -> {new_channel}", ctx)
                if result
                else echo_if_output(
                    f"❌ Rename failed: {old_channel} not found or {new_channel} already exists",
                    ctx,
                )
            )
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
