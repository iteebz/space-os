"""Pin channels to favorites."""

from __future__ import annotations

import json

import typer

from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def pin(
        ctx: typer.Context,
        channels_arg: list[str] = typer.Argument(..., help="Channels to pin"),  # noqa: B008
    ):
        """Pin channels to favorites."""
        try:
            results = []
            for channel in channels_arg:
                try:
                    ops.pin_channel(channel)
                    results.append({"channel": channel, "status": "pinned"})
                    echo_if_output(f"Pinned channel: {channel}", ctx)
                except (ValueError, TypeError) as e:
                    results.append({"channel": channel, "status": "error", "message": str(e)})
                    echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
            if ctx.obj.get("json_output"):
                typer.echo(json.dumps(results))
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
