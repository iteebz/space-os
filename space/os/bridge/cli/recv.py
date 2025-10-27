"""Receive unread messages from a channel."""

from __future__ import annotations

from dataclasses import asdict

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, output_json, should_output


def register(app: typer.Typer) -> None:
    @app.command()
    def recv(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Channel to read from"),
        identity: str = typer.Option(..., "--as", help="Receiver identity"),
    ):
        """Receive unread messages from a channel."""
        try:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Identity '{identity}' not registered.")
            msgs, count, context, participants = ops.recv_messages(channel, agent.agent_id)

            output_json(
                {
                    "messages": [asdict(msg) for msg in msgs],
                    "count": count,
                    "context": context,
                    "participants": participants,
                },
                ctx,
            ) or None
            if should_output(ctx):
                for msg in msgs:
                    sender = spawn.get_agent(msg.agent_id)
                    sender_name = sender.identity if sender else msg.agent_id[:8]
                    echo_if_output(f"[{sender_name}] {msg.content}", ctx)
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
