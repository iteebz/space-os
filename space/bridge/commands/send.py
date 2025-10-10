import base64
import binascii
import json

import typer

from ... import events
from .. import api
from space.spawn import registry

app = typer.Typer()


@app.command()
def send(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 payload"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Send a message to a channel."""
    from ..constitute import constitute_identity

    if identity != "human":
        constitute_identity(identity)

    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            if json_output:
                typer.echo(json.dumps({"status": "error", "message": "Invalid base64 payload"}))
            else:
                raise typer.BadParameter("Invalid base64 payload", param_hint="content") from exc

    agent_id = registry.ensure_agent(identity)

    try:
        events.emit(
            "bridge",
            "message_sending",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = api.resolve_channel_id(channel)
        agent_id = registry.ensure_agent(identity)
        api.send_message(channel_id, agent_id, content)
        events.emit(
            "bridge",
            "message_sent",
            agent_id,
            json.dumps({"channel": channel, "identity": identity}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "success", "channel": channel, "identity": identity}))
        elif not quiet_output:
            typer.echo(
                f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
            )
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            agent_id,
            json.dumps({"command": "send", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc


@app.command()
def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Send high-priority alert to a channel."""
    from ..constitute import constitute_identity

    constitute_identity(identity)

    agent_id = registry.ensure_agent(identity)

    try:
        events.emit(
            "bridge",
            "alert_triggering",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = api.resolve_channel_id(channel)
        agent_id = registry.ensure_agent(identity)
        api.send_message(channel_id, agent_id, content, priority="alert")
        events.emit(
            "bridge",
            "alert_triggered",
            agent_id,
            json.dumps({"channel": channel, "identity": identity}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "success", "channel": channel, "identity": identity}))
        elif not quiet_output:
            typer.echo(f"Alert sent to {channel} as {identity}")
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            agent_id,
            json.dumps({"command": "alert", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc
