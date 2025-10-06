"Bridge CLI - Clean command interface."

import json
from datetime import datetime

import click

from space.os import config, events
from space.apps import registry
from space.os.lib.base64 import decode_b64

from . import alerts, channels, db, messages, notes, streamer, utils
from .api import get_bridge_instructions
from .migration import MigrationError, migrate_store_db
from .renderer import Event


@click.group(invoke_without_command=True)
@click.pass_context
def bridge_group(ctx):
    db.init()
    """Bridge: AI Coordination Protocol"""
    if ctx.invoked_subcommand is None:
        # show_dashboard() # Will be handled later
        pass  # Placeholder for now


def _display_channels(all_channels: list, is_dashboard: bool = False) -> None:
    if not all_channels:
        click.echo("No channels found")
        return

    active_channels = []
    archived_channels = []

    for channel_obj in all_channels:
        if channel_obj.archived_at is not None:
            archived_channels.append(channel_obj)
        else:
            active_channels.append(channel_obj)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    if active_channels:
        click.echo("--- Active Channels ---")
        for channel_obj in active_channels:
            last_activity_str = utils.format_time_ago(channel_obj.last_activity) if channel_obj.last_activity else "never"
            click.echo(
                f"  {channel_obj.name:<20} ({channel_obj.message_count} msgs, {len(channel_obj.participants)} units, last activity: {last_activity_str})"
            )

    if archived_channels:
        click.echo("\n--- Archived Channels ---")
        for channel_obj in archived_channels:
            last_activity_str = utils.format_time_ago(channel_obj.last_activity) if channel_obj.last_activity else "never"
            click.echo(
                f"  {channel_obj.name:<20} ({channel_obj.message_count} msgs, {len(channel_obj.participants)} units, last activity: {last_activity_str})"
            )


@bridge_group.command(name="channels")
def bridge_channels():
    """List all channels."""
    all_channels = channels.fetch()
    _display_channels(all_channels)


@bridge_group.command(name="rename")
@click.argument("old_channel")
@click.argument("new_channel")
def bridge_rename(old_channel, new_channel):
    """Rename channel and preserve all coordination data."""
    success = channels.rename_channel(old_channel, new_channel)
    if success:
        click.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        click.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@bridge_group.command()
@click.argument("channels", nargs=-1, required=True)
def archive(channels):
    """Archive channels by setting creation date to 30 days ago."""
    for channel_obj in channels:
        channels.archive_channel(channel_obj)
        click.echo(f"Archived channel: {channel_obj}")


@bridge_group.command()
@click.argument("channel")
def delete(channel_obj):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    channels.delete_channel(channel_obj)
    click.echo(f"Deleted channel: {channel_obj}")


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
        channel_id = channels.resolve_channel_id(channel)
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
        )
        channel_id = channels.resolve_channel_id(channel)
        messages.create(channel_id, identity, content, priority="alert")
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
            channel_id = channels.resolve_channel_id(channel)
            notes_list = notes.fetch(channel_id)
            if not notes_list:
                click.echo(f"No notes for channel: {channel}")
                return

            click.echo(f"Notes for {channel}:")
            for note_item in notes_list:
                timestamp = utils.format_local_time(note_item["created_at"])
                click.echo(f"[{timestamp}] {note_item['author']}: {note_item['content']}")
                click.echo()
        except Exception as e:
            click.echo(f"❌ Failed to get notes: {e}")
            raise click.Abort() from e


@bridge_group.command()
def instructions():
    """Show current coordination instructions."""
    try:
        instructions_content = get_bridge_instructions()
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
        channel_id = channels.resolve_channel_id(channel)
        messages_list = messages.fetch_new(channel_id, identity) # Assuming fetch_new returns a list of messages
        for msg in messages_list:
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
        data = channels.export(channel)

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
        for note_item in data.notes:
            combined.append(("note", note_item))

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
        alert_messages = alerts.fetch(identity)
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
        messages_list = messages.fetch_sender_history(identity, limit)
        if not messages_list:
            click.echo(f"No messages from {identity}")
            return

        click.echo(f"--- Broadcast history for {identity} ({len(messages_list)} messages) ---")
        for msg in messages_list:
            timestamp = utils.format_local_time(msg.created_at)
            click.echo(f"\n[{msg.channel_id} | {timestamp}]")
            click.echo(msg.content)
    except Exception as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@bridge_group.command()
def stream():
    """Stream all bridge events in real-time."""
    streamer.stream_events()


@bridge_group.command()
@click.argument("channel")
def council(channel_name):
    """Stream bridge events for a specific channel."""
    streamer.stream_events(channel_name=channel_name)


@bridge_group.command()
def stream():
    """Stream all bridge events in real-time."""
    _stream_events()


@bridge_group.command()
@click.argument("channel")
def council(channel_name):
    """Stream bridge events for a specific channel."""
    _stream_events(channel_name=channel_name)