"Bridge CLI - Clean command interface."

import json
from datetime import datetime

import click

from space import config, events
from space.apps import registry
from space.apps.bridge import config as bridge_config
from space.apps.bridge import channel
from space.apps.bridge import message
from space.apps.bridge import alert
from space.apps.bridge import note
from space.apps.bridge import instructions
from space.apps.bridge import utils
from space.apps.bridge.renderer import Event
from space.lib.base64 import decode_b64

from .db import init
from .migration import MigrationError, migrate_store_db


@click.group(invoke_without_command=True)
@click.pass_context
def bridge_group(ctx):
    init()
    if config.INSTRUCTIONS_FILE.exists():
        registry.track_guide("bridge", bridge_config.INSTRUCTIONS_FILE.read_text())
    """Bridge: AI Coordination Protocol"""
    if ctx.invoked_subcommand is None:
        # show_dashboard() # Will be handled later
        pass  # Placeholder for now


def _display_channels(all_channels, is_dashboard: bool = False) -> None:
    if not all_channels:
        click.echo("No channels found")
        return

    active_channels = []
    archived_channels = []

    for channel in all_channels:
        if channel.archived_at is not None:
            archived_channels.append(channel)
        else:
            active_channels.append(channel)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    if archived_channels:
        click.echo("--- Archived Channels ---")
        for channel in archived_channels:
            last_activity_dt = (
                datetime.fromisoformat(channel.last_activity) if channel.last_activity else None
            )
            last_activity_dt.strftime("%Y-%m-%d") if last_activity_dt else "never"
            [
                f"{channel.message_count} msgs",
                f"{len(channel.participants)} units",
            ]


@bridge_group.command(name="rename")
@click.argument("old_channel")
@click.argument("new_channel")
def bridge_rename(old_channel, new_channel):
    """Rename channel and preserve all coordination data."""
    success = channel.rename_channel(old_channel, new_channel)
    if success:
        click.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        click.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@bridge_group.command()
@click.argument("channels", nargs=-1, required=True)
def archive(channels):
    """Archive channels by setting creation date to 30 days ago."""
    for channel in channels:
        channel.archive_channel(channel)
        click.echo(f"Archived channel: {channel}")


@bridge_group.command()
@click.argument("channel")
def delete(channel):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    channel.delete_channel(channel)
    click.echo(f"Deleted channel: {channel}")


@bridge_group.command(name="migrate-db")
def migrate_db_command():
    """Migrate legacy ~/.bridge/store.db to ~/.space/bridge.db."""

    try:
        result = migrate_store_db()
    except MigrationError as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc

    click.echo(result.message)
    if result.backup_path is not None and result.status == "migrated":
        click.echo(f"Backup: {result.backup_path}")


@bridge_group.command()
@click.argument("channel")
@click.argument("content")
@click.option("--as", "identity", default="human", help="Identity (defaults to human)")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
def send(channel, content, identity, decode_base64):
    """Send a message to a channel."""
    if decode_base64:
        content = decode_b64(content)

    try:
        events.emit(
            source="bridge",
            event_type="message_sending",
            data={"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = channel.resolve_channel_id(channel)
        events.emit(
            source="bridge",
            event_type="message_sent",
            data={"channel": channel, "identity": identity},
            identity=identity,
        )
        click.echo(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
        )
    except Exception as exc:
        events.emit(
            source="bridge",
            event_type="error_occurred",
            data={"command": "send", "details": str(exc)},
            identity=identity,
        )
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@bridge_group.command()
@click.argument("channel")
@click.argument("content")
@click.option("--as", "identity", required=True, help="Identity sending alert")
def alert(channel, content, identity):
    """Send high-priority alert to a channel."""
    try:
        events.emit(
            source="bridge",
            event_type="alert_triggering",
            data={"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = coordination.resolve_channel_id(channel)
        message.send_message(channel_id, identity, content, priority="alert")
        events.emit(
            source="bridge",
            event_type="alert_triggered",
            data={"channel": channel, "identity": identity},
            identity=identity,
        )
        click.echo(f"Alert sent to {channel} as {identity}")
    except Exception as exc:
        events.emit(
            "error_occurred",
            {"command": "alert", "details": str(exc)},
            identity=identity,
        )
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@bridge_group.command()
@click.argument("channel")
@click.argument("content", required=False)
@click.option("--as", "identity", help="Your agent identity (claude/gemini/codex)")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
def notes(channel, content, identity, decode_base64):
    """Show notes for channel, or add note with content and --as identity."""
    if content is None:
        # Show notes mode
        try:
            channel_id = coordination.resolve_channel_id(channel)
            notes = note.get_notes(channel_id)
            if not notes:
                click.echo(f"No notes for channel: {channel}")
                return

            click.echo(f"Notes for {channel}:")
            for note in notes:
                timestamp = utils.format_local_time(note["created_at"])
                click.echo(f"[{timestamp}] {note['author']}: {note['content']}")
                click.echo()
        except Exception as e:
            click.echo(f"❌ Failed to get notes: {e}")
            raise click.Abort() from e


@bridge_group.command()
def instructions():
    """Show current coordination instructions."""
    try:
        instructions_content = instructions.get_instructions()
        click.echo("--- Current Coordination Instructions ---")
        click.echo(instructions_content)
    except FileNotFoundError as e:
        click.echo(f"❌ {e}")
        click.echo("Create instructions file to customize coordination protocol")


@bridge_group.command()
@click.argument("channel")
@click.option("--as", "identity", required=True, help="Agent identity to receive as")
def recv(channel, identity):
    """Receive updates from a channel."""
    try:
        events.emit(
            "messages_receiving", {"channel": channel, "identity": identity}, identity=identity
        )
        channel_id = coordination.resolve_channel_id(channel)
        messages, count, context, participants = message.recv_updates(channel_id, identity)
        for msg in messages:
            events.emit(
                "message_received",
                {
                    "channel": channel,
                    "identity": identity,
                    "sender_id": msg.sender,
                    "content": msg.content,
                },
                identity=identity,
            )
            click.echo(f"[{msg.sender}] {msg.content}")
            click.echo()
    except Exception as e:
        events.emit(
            "error_occurred",
            {"command": "recv", "details": str(e)},
            identity=identity,
        )
        click.echo(f"❌ Receive failed: {e}")
        raise click.Abort() from e


@bridge_group.command()
@click.argument("channel")
def export(channel):
    """Export channel transcript with interleaved notes."""
    try:
        data = channel.export_channel(channel)

        click.echo(f"# {data.channel_name}")
        click.echo()
        if data.context:
            click.echo(f"{data.context}")
            click.echo()
        click.echo(f"Participants: {', '.join(data.participants)}")
        click.echo(f"Messages: {data.message_count}")

        if data.created_at:
            created = datetime.fromisoformat(data.created_at)
            click.echo(f"Created: {created.strftime('%Y-%m-%d')}")

        click.echo()
        click.echo("---")
        click.echo()

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
                click.echo(f"[{item['sender']} | {timestamp}]")
                click.echo(item["content"])
                click.echo()
            else:
                click.echo(f"[NOTE: {item['author']} | {timestamp}]")
                click.echo(item["content"])
                click.echo()

    except Exception as e:
        click.echo(f"❌ Export failed: {e}")
        raise click.Abort() from e


@bridge_group.command()
@click.option("--as", "identity", required=True, help="Agent identity to check alerts for")
def alerts(identity):
    """Show all unread alerts across all channels."""
    try:
        events.emit("alerts_checking", {"identity": identity}, identity=identity)
        alert_messages = alert.get_alerts(identity)
        events.emit(
            "alerts_checked",
            {"identity": identity, "count": len(alert_messages)},
            identity=identity,
        )
        if not alert_messages:
            click.echo(f"No alerts for {identity}")
            return

        click.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
        for msg in alert_messages:
            click.echo(f"\n[{msg.sender} | {msg.channel_id}]")
            click.echo(msg.content)
    except Exception as exc:
        events.emit(
            "error_occurred",
            {"command": "alerts", "details": str(exc)},
            identity=identity,
        )
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@bridge_group.command()
@click.option("--as", "identity", required=True, help="Agent identity to fetch history for")
@click.option("--limit", type=int, help="Limit results (weighted toward recent)")
def history(identity, limit):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = message.fetch_sender_history(identity, limit)
        if not messages:
            click.echo(f"No messages from {identity}")
            return

        click.echo(f"--- Broadcast history for {identity} ({len(messages)} messages) ---")
        for msg in messages:
            timestamp = utils.format_local_time(msg.created_at)
            click.echo(f"\n[{msg.channel_id} | {timestamp}]")
            click.echo(msg.content)
    except Exception as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


def _stream_events(channel: str | None = None):
    """Helper function to stream bridge events, with optional channel filtering."""
    import time

    from space import events

    # 1. Render historic events
    all_events = events.query(source="bridge", limit=1000)  # Increased limit for history
    for event_tuple in reversed(all_events):
        event = {
            "uuid": event_tuple[0],
            "source": event_tuple[1],
            "identity": event_tuple[2],
            "data": json.loads(event_tuple[4])
            if isinstance(event_tuple[4], str)
            else event_tuple[4],
            "created_at": event_tuple[5],
        }
        if channel is None or (
            event.get("data") and event.get("data", {}).get("channel") == channel
        ):
            event_type = event.get("event_type")
            data = event.get("data", {})
            identity = event.get("identity")
            if event_type == "message_sent":
                click.echo(f"→ Sent to {data.get('channel')} as {identity}: {data.get('content')}")
            elif event_type == "message_received":
                click.echo(
                    f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}"
                )

    # 2. Start live stream
    renderer = renderer.Renderer()

    def event_stream():
        last_event_uuid = all_events[0][0] if all_events else None
        while True:
            try:
                all_events_live = events.query(source="bridge", limit=100)
                new_events = []
                if last_event_uuid:
                    for i, event in enumerate(all_events_live):
                        if event[0] == last_event_uuid:
                            new_events = all_events_live[:i]
                            break
                else:
                    new_events = all_events_live

                if new_events:
                    for event_tuple in reversed(new_events):
                        event_data = {
                            "uuid": event_tuple[0],
                            "source": event_tuple[1],
                            "identity": event_tuple[2],
                            "event_type": event_tuple[3],
                            "data": json.loads(event_tuple[4])
                            if isinstance(event_tuple[4], str)
                            else event_tuple[4],
                            "created_at": event_tuple[5],
                        }
                        if channel is None or (
                            event_data.get("data")
                            and event_data.get("data", {}).get("channel") == channel
                        ):
                            event_type = event_data.get("event_type")
                            data = event_data.get("data", {})
                            if event_type == "message_sent":
                                yield renderer.Event(
                                    type="token",
                                    content=f"→ Sent to {data.get('channel')} as {event_data.get('identity')}: {data.get('content')}\n",
                                )
                            elif event_type == "message_received":
                                yield renderer.Event(
                                    type="token",
                                    content=f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}\n",
                                )
                            else:
                                yield renderer.Event(type="status", content=f"Event: {event_type}")

                    last_event_uuid = new_events[0][0]

                time.sleep(1)
            except KeyboardInterrupt:
                yield Event(type="done")
                break

    renderer.render(event_stream())


@bridge_group.command()
def stream():
    """Stream all bridge events in real-time."""
    _stream_events()


@bridge_group.command()
@click.argument("channel")
def council(channel):
    """Stream bridge events for a specific channel."""
    _stream_events(channel=channel)
