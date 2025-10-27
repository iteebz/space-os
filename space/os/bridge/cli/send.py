"""Send a message to a channel."""

from __future__ import annotations

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def send(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Target channel"),
        content: str = typer.Argument(..., help="Message content"),
        identity: str = typer.Option("human", "--as", help="Sender identity"),
        decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 content"),
    ):
        """Send a message to a channel."""
        try:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Identity '{identity}' not registered.")
            ops.send_message(channel, identity, content, decode_base64)
            output_json(
                {"status": "success", "channel": channel, "identity": identity}, ctx
            ) or echo_if_output(
                f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}",
                ctx,
            )
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
