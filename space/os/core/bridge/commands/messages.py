"""Message commands: send, alert, recv, wait, inbox, alerts."""

import base64
import binascii
import json
import time
from dataclasses import asdict

import typer

from space.os import events
from space.os.core import spawn
from space.os.lib.identity import constitute_identity
from .. import channels, messaging, spawning

app = typer.Typer()


@app.command("send")
def send_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 payload"),
):
    """Send message to channel."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

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

    agent_id = spawn.db.ensure_agent(identity)

    try:
        channel_id = channels.resolve_channel_id(channel)
        events.emit(
            "bridge",
            "message_sending",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        messaging.send_message(channel_id, identity, content)
        spawning.spawn_agents_from_mentions(channel_id, content)
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
            "error",
            agent_id,
            json.dumps({"command": "send", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from exc


@app.command("alert")
def alert_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
):
    """Send alert message."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)

    try:
        events.emit(
            "bridge",
            "alert_triggering",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = channels.resolve_channel_id(channel)
        agent_id = spawn.db.ensure_agent(identity)
        messaging.send_message(channel_id, identity, content, priority="alert")
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
            "error",
            agent_id,
            json.dumps({"command": "alert", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from exc


@app.command("recv")
def recv_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
):
    """Receive messages from channel."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)

    try:
        channel_id = channels.resolve_channel_id(channel)
        msgs, count, context, participants = messaging.recv_updates(channel_id, identity)

        for msg in msgs:
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
                        "messages": [asdict(msg) for msg in msgs],
                        "count": count,
                        "context": context,
                        "participants": participants,
                    }
                )
            )
        elif not quiet_output:
            for msg in msgs:
                typer.echo(f"[{spawn.db.get_agent_name(msg.agent_id)}] {msg.content}")
                typer.echo()
    except ValueError as e:
        events.emit(
            "bridge",
            "error",
            agent_id,
            json.dumps({"command": "recv", "details": str(e)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from e


@app.command("wait")
def wait_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
):
    """Block until new message arrives."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)

    try:
        channel_id = channels.resolve_channel_id(channel)
    except (ValueError, TypeError):
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from None

    try:
        while True:
            msgs, count, context, participants = messaging.recv_updates(channel_id, identity)
            other_messages = [msg for msg in msgs if msg.agent_id != agent_id]

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
                        typer.echo(f"[{spawn.db.get_agent_name(msg.agent_id)}] {msg.content}")
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


@app.command("inbox")
def inbox(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Agent identity"),
):
    """Show channels with unreads."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)

    try:
        chans = channels.inbox_channels(identity)
        if not chans:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo("Inbox empty")
            return

        if json_output:
            typer.echo(json.dumps([asdict(c) for c in chans]))
        elif not quiet_output:
            from ..lib.format import format_channel_row
            for channel in chans:
                last_activity, description = format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")
    except Exception as exc:
        events.emit(
            "bridge",
            "error",
            agent_id,
            json.dumps({"command": "inbox", "details": str(exc)}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command("alerts")
def alerts_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
):
    """Show alert messages."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    constitute_identity(identity)
    agent_id = spawn.db.ensure_agent(identity)

    try:
        alert_messages = messaging.get_alerts(agent_id)
        if not alert_messages:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo(f"No alerts for {identity}")
            return

        if json_output:
            typer.echo(json.dumps([asdict(msg) for msg in alert_messages]))
        elif not quiet_output:
            typer.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
            for msg in alert_messages:
                typer.echo(f"\n[{spawn.db.get_agent_name(msg.agent_id)} | {msg.channel_id}]")
                typer.echo(msg.content)

        for msg in alert_messages:
            messaging.set_bookmark(agent_id, msg.channel_id, msg.message_id)
    except Exception as exc:
        events.emit(
            "bridge",
            "error",
            agent_id,
            json.dumps({"command": "alerts", "details": str(exc)}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc
