import json
from dataclasses import asdict

import typer

from space.lib.identity import constitute_identity

from ... import events
from .. import api, utils

app = typer.Typer()


@app.command()
def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    constitute_identity(identity)

    from space.spawn import registry

    agent_id = registry.ensure_agent(identity)

    try:
        channel_id = api.resolve_channel_id(channel)
        messages, count, context, participants = api.recv_updates(channel_id, identity)

        for msg in messages:
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
                        "messages": [asdict(msg) for msg in messages],
                        "count": count,
                        "context": context,
                        "participants": participants,
                    }
                )
            )
        elif not quiet_output:
            for msg in messages:
                typer.echo(f"[{registry.get_identity(msg.agent_id)}] {msg.content}")
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


@app.command()
def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    constitute_identity(identity)

    from space.spawn import registry

    from .. import db

    agent_id = registry.ensure_agent(identity)

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
                typer.echo(f"\n[{registry.get_identity(msg.agent_id)} | {msg.channel_id}]")
                typer.echo(msg.content)

        for msg in alert_messages:
            db.set_bookmark(agent_id, msg.channel_id, msg.message_id)
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


@app.command()
def inbox(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show all channels with unreads."""
    constitute_identity(identity)

    from space.spawn import registry

    agent_id = registry.ensure_agent(identity)

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
            for channel in channels:
                last_activity, description = utils.format_channel_row(channel)
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
