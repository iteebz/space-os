"""Message commands: send, alert, recv, wait, inbox, alerts."""

import base64
import binascii
import json
import time
from dataclasses import asdict

import typer

from space.core import spawn

from ..api import channels, mentions, messaging

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

    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            if json_output:
                typer.echo(json.dumps({"status": "error", "message": "Invalid base64 payload"}))
            else:
                raise typer.BadParameter("Invalid base64 payload", param_hint="content") from exc

    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.Exit(f"Identity '{identity}' not registered.")
        channel_id = channels.resolve_channel(channel).channel_id
        messaging.send_message(channel_id, identity, content)
        mentions.spawn_from_mentions(channel_id, content)
        if json_output:
            typer.echo(json.dumps({"status": "success", "channel": channel, "identity": identity}))
        elif not quiet_output:
            typer.echo(
                f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
            )
    except ValueError as exc:
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

    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.Exit(f"Identity '{identity}' not registered.")
        channel_id = channels.resolve_channel(channel).channel_id
        msgs, count, context, participants = messaging.recv_messages(channel_id, identity)

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
                sender = spawn.get_agent(msg.agent_id)
                sender_name = sender.identity if sender else msg.agent_id[:8]
                typer.echo(f"[{sender_name}] {msg.content}")
                typer.echo()
    except ValueError as e:
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

    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.Exit(f"Identity '{identity}' not registered.")
        agent_id = agent.agent_id
        channel_id = channels.resolve_channel(channel).channel_id
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
            msgs, count, context, participants = messaging.recv_messages(channel_id, identity)
            other_messages = [msg for msg in msgs if msg.agent_id != agent_id]

            if other_messages:
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
                        sender = spawn.get_agent(msg.agent_id)
                        sender_name = sender.identity if sender else msg.agent_id[:8]
                        typer.echo(f"[{sender_name}] {msg.content}")
                        typer.echo()
                break

            time.sleep(poll_interval)

    except ValueError as e:
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

    agent_id = None
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.Exit(f"Identity '{identity}' not registered.")
        agent_id = agent.agent_id
        chans = channels.fetch_inbox(agent_id)
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
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc
