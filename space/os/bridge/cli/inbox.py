"""Show unread channels for an agent."""

from __future__ import annotations

from dataclasses import asdict

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, format_channel_row, output_json, should_output


def register(app: typer.Typer) -> None:
    @app.command()
    def inbox(
        ctx: typer.Context,
        identity: str = typer.Option(..., "--as", help="Agent identity"),
    ):
        """Show unread channels for an agent."""
        try:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Identity '{identity}' not registered.")
            chans = ops.fetch_inbox(agent.agent_id)
            if not chans:
                output_json([], ctx) or echo_if_output("Inbox empty", ctx)
                return

            output_json([asdict(c) for c in chans], ctx) or None
            if should_output(ctx):
                echo_if_output(f"INBOX ({len(chans)}):", ctx)
                for channel in chans:
                    last_activity, description = format_channel_row(channel)
                    echo_if_output(f"  {last_activity}: {description}", ctx)
        except Exception as exc:
            output_json({"status": "error", "message": str(exc)}, ctx) or echo_if_output(
                f"❌ {exc}", ctx
            )
            raise typer.Exit(code=1) from exc
