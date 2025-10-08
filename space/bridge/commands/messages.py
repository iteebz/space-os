import base64
import binascii
import json

import typer

from ... import events
from .. import api, utils

app = typer.Typer()


@app.command()
def send(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 payload"),
):
    """Send a message to a channel."""
    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise typer.BadParameter("Invalid base64 payload", param_hint="content") from exc

    try:
        events.emit(
            "bridge",
            "message_sending",
            identity,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = api.resolve_channel_id(channel)
        api.send_message(channel_id, identity, content)
        events.emit(
            "bridge",
            "message_sent",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        typer.echo(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
        )
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "send", "details": str(exc)}),
        )
        typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc


@app.command()
def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
):
    """Send high-priority alert to a channel."""
    try:
        events.emit(
            "bridge",
            "alert_triggering",
            identity,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        channel_id = api.resolve_channel_id(channel)
        api.send_message(channel_id, identity, content, priority="alert")
        events.emit(
            "bridge",
            "alert_triggered",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        typer.echo(f"Alert sent to {channel} as {identity}")
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "alert", "details": str(exc)}),
        )
        typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc


@app.command()
def notes(
    channel: str = typer.Argument(...),
    content: str | None = typer.Argument(None),
    identity: str | None = typer.Option(
        None, "--as", help="Your agent identity (claude/gemini/codex)"
    ),
):
    """Show notes for channel, or add note with content and --as identity."""
    if content is None:
        try:
            channel_id = api.resolve_channel_id(channel)
            notes = api.get_notes(channel_id)
            if not notes:
                typer.echo(f"No notes for channel: {channel}")
                return

            typer.echo(f"Notes for {channel}:")
            for note in notes:
                timestamp = utils.format_local_time(note["created_at"])
                typer.echo(f"[{timestamp}] {note['author']}: {note['content']}")
                typer.echo()
        except ValueError as e:
            typer.echo(f"❌ Channel '{channel}' not found.")
            raise typer.Exit(code=1) from e
    else:
        if not identity:
            typer.echo("❌ Must specify --as identity when adding notes")
            raise typer.Exit(code=1)
        try:
            channel_id = api.resolve_channel_id(channel)
            api.add_note(channel_id, identity, content)
            typer.echo(f"Added note to {channel}")
        except ValueError as e:
            typer.echo(f"❌ Channel '{channel}' not found.")
            raise typer.Exit(code=1) from e


@app.command()
def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
):
    """Receive updates from a channel."""
    try:
        events.emit(
            "bridge",
            "messages_receiving",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        channel_id = api.resolve_channel_id(channel)
        messages, count, context, participants = api.recv_updates(channel_id, identity)
        for msg in messages:
            events.emit(
                "bridge",
                "message_received",
                identity,
                json.dumps(
                    {
                        "channel": channel,
                        "identity": identity,
                        "sender_id": msg.sender,
                        "content": msg.content,
                    }
                ),
            )
            typer.echo(f"[{msg.sender}] {msg.content}")
            typer.echo()
    except ValueError as e:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "recv", "details": str(e)}),
        )
        typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from e


@app.command()
def export(
    channel: str = typer.Argument(...),
):
    """Export channel transcript with interleaved notes."""
    from datetime import datetime

    try:
        data = api.export_channel(channel)

        typer.echo(f"# {data.channel_name}")
        typer.echo()
        if data.topic:
            typer.echo(f"Topic: {data.topic}")
            typer.echo()
        typer.echo(f"Participants: {', '.join(data.participants)}")
        typer.echo(f"Messages: {data.message_count}")

        if data.created_at:
            created = datetime.fromisoformat(data.created_at)
            typer.echo(f"Created: {created.strftime('%Y-%m-%d')}")

        typer.echo()
        typer.echo("---")
        typer.echo()

        combined = []
        for msg in data.messages:
            combined.append(("msg", msg))
        for note in data.notes:
            combined.append(("note", note))

        combined.sort(key=lambda x: x[1]["created_at"])

        for item_type, item in combined:
            created = datetime.fromisoformat(item["created_at"])
            timestamp = created.strftime("%Y-%m-%d %H:%M:%S")

            if item_type == "msg":
                typer.echo(f"[{item['sender']} | {timestamp}]")
                typer.echo(item["content"])
                typer.echo()
            else:
                typer.echo(f"[NOTE: {item['author']} | {timestamp}]")
                typer.echo(item["content"])
                typer.echo()

    except ValueError as e:
        typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from e


@app.command()
def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
):
    """Show all unread alerts across all channels."""
    try:
        events.emit("bridge", "alerts_checking", identity, json.dumps({"identity": identity}))
        alert_messages = api.get_alerts(identity)
        events.emit(
            "bridge",
            "alerts_checked",
            identity,
            json.dumps({"identity": identity, "count": len(alert_messages)}),
        )
        if not alert_messages:
            typer.echo(f"No alerts for {identity}")
            return

        typer.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
        for msg in alert_messages:
            typer.echo(f"\n[{msg.sender} | {msg.channel_id}]")
            typer.echo(msg.content)
    except Exception as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "alerts", "details": str(exc)}),
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def history(
    identity: str = typer.Option(..., "--as", help="Agent identity to fetch history for"),
    limit: int | None = typer.Option(None, help="Limit results (weighted toward recent)"),
):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = api.fetch_sender_history(identity, limit)
        if not messages:
            typer.echo(f"No messages from {identity}")
            return

        typer.echo(f"--- Broadcast history for {identity} ({len(messages)} messages) ---")
        for msg in messages:
            timestamp = utils.format_local_time(msg.created_at)
            typer.echo(f"\n[{msg.channel_id} | {timestamp}]")
            typer.echo(msg.content)
    except Exception as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc
