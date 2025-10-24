import base64
import binascii
import json
import time
from dataclasses import asdict

import typer

from space.os.lib.identity import constitute_identity

from ...events import emit
from .. import spawn
from . import api


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
        channel_id = api.resolve_channel_id(channel)
    except ValueError:
        channel_id = api.create_channel(channel)

    try:
        emit(
            "bridge",
            "message_sending",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        api.send_message(channel_id, identity, content)
        emit(
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
        emit(
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


def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    constitute_identity(identity)

    agent_id = spawn.db.ensure_agent(identity)

    try:
        emit(
            "bridge",
            "alert_triggering",
            agent_id,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = api.resolve_channel_id(channel)
        agent_id = spawn.db.ensure_agent(identity)
        api.send_message(channel_id, identity, content, priority="alert")
        emit(
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
        emit(
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


def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    constitute_identity(identity)

    agent_id = spawn.db.ensure_agent(identity)

    try:
        channel_id = api.resolve_channel_id(channel)
        messages, count, context, participants = api.recv_updates(channel_id, identity)

        for msg in messages:
            emit(
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
                        "messages": [asdict(msg) for msg in messages],
                        "count": count,
                        "context": context,
                        "participants": participants,
                    }
                )
            )
        elif not quiet_output:
            for msg in messages:
                typer.echo(f"[{spawn.db.get_agent_name(msg.agent_id)}] {msg.content}")
                typer.echo()
    except ValueError as e:
        emit(
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


def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    constitute_identity(identity)

    from . import db

    agent_id = spawn.db.ensure_agent(identity)

    try:
        alert_messages = api.get_alerts(identity)
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
            db.set_bookmark(agent_id, msg.channel_id, msg.message_id)
    except Exception as exc:
        emit(
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


def inbox(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show all channels with unreads."""
    constitute_identity(identity)

    agent_id = spawn.db.ensure_agent(identity)

    try:
        channels = api.inbox_channels(identity)
        if not channels:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo("Inbox empty")
            return

        if json_output:
            typer.echo(json.dumps([asdict(c) for c in channels]))
        elif not quiet_output:
            from . import utils

            for channel in channels:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")
    except Exception as exc:
        emit(
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

    agent_id = spawn.db.ensure_agent(identity)

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
                    emit(
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
        emit(
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
