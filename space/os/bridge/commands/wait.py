import json
import time
from dataclasses import asdict

import typer

from space.os.lib.identity import constitute_identity
from space.os.spawn import registry

from ... import events
from .. import api

app = typer.Typer()


@app.command()
def wait(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
):
    """Block until new message arrives, then return."""
    constitute_identity(identity)

    agent_id = registry.ensure_agent(identity)

    try:
        channel_id = api.resolve_channel_id(channel)
    except ValueError:
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from None

    try:
        while True:
            messages, count, context, participants = api.recv_updates(channel_id, identity)

            other_messages = [msg for msg in messages if msg.agent_id != agent_id]

            if other_messages:
                for msg in other_messages:
                    events.emit(
                        "bridge",
                        "message_received",
                        agent_id,
                        json.dumps(
                            {
                                "channel": channel,
                                "identity": identity,
                                "agent_id": msg.agent_id,
                                "content": msg.content,
                            }
                        ),
                    )

                if json_output:
                    typer.echo(
                        json.dumps(
                            {
                                "messages": [asdict(msg) for msg in other_messages],
                                "count": len(other_messages),
                                "context": context,
                                "participants": participants,
                            }
                        )
                    )
                elif not quiet_output:
                    for msg in other_messages:
                        typer.echo(f"[{registry.get_identity(msg.agent_id)}] {msg.content}")
                        typer.echo()
                break

            time.sleep(poll_interval)

    except ValueError as e:
        events.emit(
            "bridge",
            "error",
            agent_id,
            json.dumps({"command": "wait", "details": str(e)}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"❌ {e}")
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        if not quiet_output:
            typer.echo("\n")
        raise typer.Exit(code=0) from None
