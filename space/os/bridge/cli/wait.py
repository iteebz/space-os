"""Block and wait for a new message in a channel."""

from __future__ import annotations

from dataclasses import asdict

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, output_json, should_output


def register(app: typer.Typer) -> None:
    @app.command()
    def wait(
        ctx: typer.Context,
        channel: str = typer.Argument(..., help="Channel to monitor"),
        identity: str = typer.Option(..., "--as", help="Receiver identity"),
        poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
    ):
        """Block and wait for a new message in a channel."""
        try:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Identity '{identity}' not registered.")
            other_messages, count, context, participants = ops.wait_for_message(
                channel, agent.agent_id, poll_interval
            )
            output_json(
                {
                    "messages": [asdict(msg) for msg in other_messages],
                    "count": count,
                    "context": context,
                    "participants": participants,
                },
                ctx,
            ) or None
            if should_output(ctx):
                for msg in other_messages:
                    sender = spawn.get_agent(msg.agent_id)
                    sender_name = sender.identity if sender else msg.agent_id[:8]
                    echo_if_output(f"[{sender_name}] {msg.content}", ctx)
                    echo_if_output("", ctx)
        except ValueError as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
        except KeyboardInterrupt:
            echo_if_output("\n", ctx)
            raise typer.Exit(code=0) from None
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
