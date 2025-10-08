"""Bridge CLI - Clean command interface."""

import base64
import binascii
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

import typer

from .. import protocols as old_protocols # Renamed to avoid conflict
from . import config, coordination, storage, utils
from . import events as bridge_events
from .renderer import Event, Renderer
from .storage.migration import MigrationError, migrate_store_db
from .lib import protocols # New import

app = typer.Typer(invoke_without_command=True)

# PROTOCOL_FILE definition for bridge.md
PROTOCOL_FILE = Path(__file__).parent.parent.parent / "protocols" / "bridge.md"

# Removed: if config.INSTRUCTIONS_FILE.exists(): old_protocols.track("bridge", config.INSTRUCTIONS_FILE.read_text())

@app.callback()
def main_command():
    """Bridge: AI Coordination Protocol"""
    try:
        typer.echo(protocols.load("bridge"))
    except FileNotFoundError:
        typer.echo("❌ bridge.md protocol not found")

# Removed: show_dashboard function

@app.command("channels")
def channels():
    """List all channels with metadata."""
    all_channels = coordination.all_channels()

    if not all_channels:
        typer.echo("No channels found")
        return

    active_channels = []
    archived_channels = []

    archived_threshold = datetime.now() - timedelta(days=29)

    for channel in all_channels:
        created_at_dt = datetime.fromisoformat(channel.created_at)
        if created_at_dt < archived_threshold:
            archived_channels.append(channel)
        else:
            active_channels.append(channel)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    typer.echo("--- Active Channels ---")

    for channel in active_channels:
        last_activity_dt = (
            datetime.fromisoformat(channel.last_activity) if channel.last_activity else None
        )
        last_activity = last_activity_dt.strftime("%Y-%m-%d") if last_activity_dt else "never"
        meta_parts = [
            f"{channel.message_count} msgs",
            f"{len(channel.participants)} members",
        ]
        if channel.notes_count > 0:
            meta_parts.append(f"{channel.notes_count} notes")
        meta_str = " | ".join(meta_parts)
        typer.echo(f"{last_activity}: {channel.name} - {meta_str}")

    if archived_channels:
        typer.echo("\n--- Archived Channels ---")
        for channel in archived_channels:
            last_activity_dt = (
                datetime.fromisoformat(channel.last_activity) if channel.last_activity else None
            )
            last_activity = last_activity_dt.strftime("%Y-%m-%d") if last_activity_dt else "never"
            meta_parts = [
                f"{channel.message_count} msgs",
                f"{len(channel.participants)} members",
            ]
            if channel.notes_count > 0:
                meta_parts.append(f"{channel.notes_count} notes")
            meta_str = " | ".join(meta_parts)
            typer.echo(f"{last_activity}: {channel.name} - {meta_str}")


@app.command()
def rename(
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
):
    """Rename channel and preserve all coordination data."""
    success = coordination.rename_channel(old_channel, new_channel)
    if success:
        typer.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        typer.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@app.command()
def archive(
    channels: List[str] = typer.Argument(...),
):
    """Archive channels by setting creation date to 30 days ago."""
    for channel in channels:
        coordination.archive_channel(channel)
        typer.echo(f"Archived channel: {channel}")


@app.command()
def delete(
    channel: str = typer.Argument(...),
):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    coordination.delete_channel(channel)
    typer.echo(f"Deleted channel: {channel}")


@app.command("migrate-db")
def migrate_db_command():
    """Migrate legacy ~/.bridge/store.db to ~/.space/bridge.db."""

    try:
        result = migrate_store_db()
    except MigrationError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(result.message)
    if result.backup_path is not None and result.status == "migrated":
        typer.echo(f"Backup: {result.backup_path}")


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
        bridge_events.emit(
            "message_sending",
            {"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content)
        bridge_events.emit(
            "message_sent", {"channel": channel, "identity": identity}, identity=identity
        )
        typer.echo(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
        )
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "send", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
):
    """Send high-priority alert to a channel."""
    try:
        bridge_events.emit(
            "alert_triggering",
            {"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content, priority="alert")
        bridge_events.emit(
            "alert_triggered", {"channel": channel, "identity": identity}, identity=identity
        )
        typer.echo(f"Alert sent to {channel} as {identity}")
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "alert", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def notes(
    channel: str = typer.Argument(...),
    content: Optional[str] = typer.Argument(None),
    identity: Optional[str] = typer.Option(None, "--as", help="Your agent identity (claude/gemini/codex)"),
):
    """Show notes for channel, or add note with content and --as identity."""
    if content is None:
        # Show notes mode
        try:
            channel_id = coordination.resolve_channel_id(channel)
            notes = coordination.get_notes(channel_id)
            if not notes:
                typer.echo(f"No notes for channel: {channel}")
                return

            typer.echo(f"Notes for {channel}:")
            for note in notes:
                timestamp = utils.format_local_time(note["created_at"])
                typer.echo(f"[{timestamp}] {note['author']}: {note['content']}")
                typer.echo()
        except Exception as e:
            typer.echo(f"❌ Failed to get notes: {e}")
            raise typer.Exit(code=1) from e
    else:
        # Add note mode
        if not identity:
            typer.echo("❌ Must specify --as identity when adding notes")
            raise typer.Exit(code=1)
        try:
            channel_id = coordination.resolve_channel_id(channel)
            coordination.add_note(channel_id, identity, content)
            typer.echo(f"Added note to {channel}")
        except Exception as e:
            typer.echo(f"❌ Note failed: {e}")
            raise typer.Exit(code=1) from e


@app.command()
def instructions():
    """Show current coordination instructions."""
    try:
        instructions_content = coordination.get_instructions()
        typer.echo("--- Current Coordination Instructions ---")
        typer.echo(instructions_content)
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("Create instructions file to customize coordination protocol")


@app.command()
def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
):
    """Receive updates from a channel."""
    try:
        bridge_events.emit(
            "messages_receiving", {"channel": channel, "identity": identity}, identity=identity
        )
        channel_id = coordination.resolve_channel_id(channel)
        messages, count, context, participants = coordination.recv_updates(channel_id, identity)
        for msg in messages:
            bridge_events.emit(
                "message_received",
                {
                    "channel": channel,
                    "identity": identity,
                    "sender_id": msg.sender,
                    "content": msg.content,
                },
                identity=identity,
            )
            typer.echo(f"[{msg.sender}] {msg.content}")
            typer.echo()
    except Exception as e:
        bridge_events.emit(
            "error_occurred", {"command": "recv", "details": str(e)}, identity=identity
        )
        typer.echo(f"❌ Receive failed: {e}")
        raise typer.Exit(code=1) from e


@app.command()
def export(
    channel: str = typer.Argument(...),
):
    """Export channel transcript with interleaved notes."""
    try:
        data = coordination.export_channel(channel)

        typer.echo(f"# {data.channel_name}")
        typer.echo()
        if data.context:
            typer.echo(f"{data.context}")
            typer.echo()
        typer.echo(f"Participants: {', '.join(data.participants)}")
        typer.echo(f"Messages: {data.message_count}")

        if data.created_at:
            created = datetime.fromisoformat(data.created_at)
            typer.echo(f"Created: {created.strftime('%Y-%m-%d')}")

        typer.echo()
        typer.echo("---")
        typer.echo()

    except Exception as e:
        typer.echo(f"❌ Export failed: {e}")
        raise typer.Exit(code=1) from e




@app.command()
def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
):
    """Show all unread alerts across all channels."""
    try:
        bridge_events.emit("alerts_checking", {"identity": identity}, identity=identity)
        alert_messages = coordination.get_alerts(identity)
        bridge_events.emit(
            "alerts_checked",
            {"identity": identity, "count": len(alert_messages)},
            identity=identity,
        )
        if not alert_messages:
            typer.echo(f"No alerts for {identity}")
            return

        typer.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
        for msg in alert_messages:
            typer.echo(f"\n[{msg.sender} | {msg.channel_id}]")
            typer.echo(msg.content)
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "alerts", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def history(
    identity: str = typer.Option(..., "--as", help="Agent identity to fetch history for"),
    limit: Optional[int] = typer.Option(None, help="Limit results (weighted toward recent)"),
):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = coordination.fetch_sender_history(identity, limit)
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


def _stream_events(channel: str | None = None):
    """Helper function to stream bridge events, with optional channel filtering."""
    import time

    from .. import events

    # 1. Render historic events
    all_events = events.query(source="bridge", limit=1000)  # Increased limit for history
    for event_tuple in reversed(all_events):
        event = {
            "uuid": event_tuple[0],
            "source": event_tuple[1],
            "identity": event_tuple[2],
            "event_type": event_tuple[3],
            "data": event_tuple[4],
            "created_at": event_tuple[5],
        }
        if channel is None or (
            event.get("data") and event.get("data", {}).get("channel") == channel
        ):
            event_type = event.get("event_type")
            data = event.get("data", {})
            identity = event.get("identity")
            if event_type == "message_sent":
                typer.echo(f"→ Sent to {data.get('channel')} as {identity}: {data.get('content')}")
            elif event_type == "message_received":
                typer.echo(
                    f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}"
                )

    # 2. Start live stream
    renderer = Renderer()

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
                            "data": event_tuple[4],
                            "created_at": event_tuple[5],
                        }
                        if channel is None or (
                            event_data.get("data")
                            and event_data.get("data", {}).get("channel") == channel
                        ):
                            event_type = event_data.get("event_type")
                            data = event_data.get("data", {})
                            if event_type == "message_sent":
                                yield Event(
                                    type="token",
                                    content=f"→ Sent to {data.get('channel')} as {event_data.get('identity')}: {data.get('content')}\n",
                                )
                            elif event_type == "message_received":
                                yield Event(
                                    type="token",
                                    content=f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}\n",
                                )
                            else:
                                yield Event(type="status", content=f"Event: {event_type}")

                    last_event_uuid = new_events[0][0]

                time.sleep(1)
            except KeyboardInterrupt:
                yield Event(type="done")
                break

    renderer.render(event_stream())


@app.command()
def stream():
    """Stream all bridge events in real-time."""
    _stream_events()


@app.command()
def council(
    channel: str = typer.Argument(...),
):
    """Stream bridge events for a specific channel."""
    _stream_events(channel=channel)


if __name__ == "__main__":
    app()


def show_dashboard() -> None:
    """Display coordination dashboard with instructions."""
    active = coordination.active_channels()

    typer.echo("BRIDGE: AI Coordination Protocol")
    typer.echo()

    if active:
        typer.echo("ACTIVE CHANNELS:")
        for ch in active:
            ago = utils.format_time_ago(ch.last_activity)
            meta = f"{ch.message_count} msgs | {len(ch.participants)} members"
            typer.echo(f"  {ch.name} - {ago} | {meta}")
        typer.echo()

    try:
        instructions = coordination.get_instructions()
        typer.echo(instructions)
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("Create instructions file to customize coordination protocol")


@app.command("channels")
def channels():
    """List all channels with metadata."""
    all_channels = coordination.all_channels()

    if not all_channels:
        typer.echo("No channels found")
        return

    active_channels = []
    archived_channels = []

    archived_threshold = datetime.now() - timedelta(days=29)

    for channel in all_channels:
        created_at_dt = datetime.fromisoformat(channel.created_at)
        if created_at_dt < archived_threshold:
            archived_channels.append(channel)
        else:
            active_channels.append(channel)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    typer.echo("--- Active Channels ---")

    for channel in active_channels:
        last_activity_dt = (
            datetime.fromisoformat(channel.last_activity) if channel.last_activity else None
        )
        last_activity = last_activity_dt.strftime("%Y-%m-%d") if last_activity_dt else "never"
        meta_parts = [
            f"{channel.message_count} msgs",
            f"{len(channel.participants)} members",
        ]
        if channel.notes_count > 0:
            meta_parts.append(f"{channel.notes_count} notes")
        meta_str = " | ".join(meta_parts)
        typer.echo(f"{last_activity}: {channel.name} - {meta_str}")

    if archived_channels:
        typer.echo("\n--- Archived Channels ---")
        for channel in archived_channels:
            last_activity_dt = (
                datetime.fromisoformat(channel.last_activity) if channel.last_activity else None
            )
            last_activity = last_activity_dt.strftime("%Y-%m-%d") if last_activity_dt else "never"
            meta_parts = [
                f"{channel.message_count} msgs",
                f"{len(channel.participants)} members",
            ]
            if channel.notes_count > 0:
                meta_parts.append(f"{channel.notes_count} notes")
            meta_str = " | ".join(meta_parts)
            typer.echo(f"{last_activity}: {channel.name} - {meta_str}")


@app.command()
def rename(
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
):
    """Rename channel and preserve all coordination data."""
    success = coordination.rename_channel(old_channel, new_channel)
    if success:
        typer.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        typer.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@app.command()
def archive(
    channels: List[str] = typer.Argument(...),
):
    """Archive channels by setting creation date to 30 days ago."""
    for channel in channels:
        coordination.archive_channel(channel)
        typer.echo(f"Archived channel: {channel}")


@app.command()
def delete(
    channel: str = typer.Argument(...),
):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    coordination.delete_channel(channel)
    typer.echo(f"Deleted channel: {channel}")


@app.command("migrate-db")
def migrate_db_command():
    """Migrate legacy ~/.bridge/store.db to ~/.space/bridge.db."""

    try:
        result = migrate_store_db()
    except MigrationError as exc:
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(result.message)
    if result.backup_path is not None and result.status == "migrated":
        typer.echo(f"Backup: {result.backup_path}")


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
        bridge_events.emit(
            "message_sending",
            {"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content)
        bridge_events.emit(
            "message_sent", {"channel": channel, "identity": identity}, identity=identity
        )
        typer.echo(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
        )
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "send", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
):
    """Send high-priority alert to a channel."""
    try:
        bridge_events.emit(
            "alert_triggering",
            {"channel": channel, "identity": identity, "content": content},
            identity=identity,
        )
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content, priority="alert")
        bridge_events.emit(
            "alert_triggered", {"channel": channel, "identity": identity}, identity=identity
        )
        typer.echo(f"Alert sent to {channel} as {identity}")
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "alert", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def notes(
    channel: str = typer.Argument(...),
    content: Optional[str] = typer.Argument(None),
    identity: Optional[str] = typer.Option(None, "--as", help="Your agent identity (claude/gemini/codex)"),
):
    """Show notes for channel, or add note with content and --as identity."""
    if content is None:
        # Show notes mode
        try:
            channel_id = coordination.resolve_channel_id(channel)
            notes = coordination.get_notes(channel_id)
            if not notes:
                typer.echo(f"No notes for channel: {channel}")
                return

            typer.echo(f"Notes for {channel}:")
            for note in notes:
                timestamp = utils.format_local_time(note["created_at"])
                typer.echo(f"[{timestamp}] {note['author']}: {note['content']}")
                typer.echo()
        except Exception as e:
            typer.echo(f"❌ Failed to get notes: {e}")
            raise typer.Exit(code=1) from e
    else:
        # Add note mode
        if not identity:
            typer.echo("❌ Must specify --as identity when adding notes")
            raise typer.Exit(code=1)
        try:
            channel_id = coordination.resolve_channel_id(channel)
            coordination.add_note(channel_id, identity, content)
            typer.echo(f"Added note to {channel}")
        except Exception as e:
            typer.echo(f"❌ Note failed: {e}")
            raise typer.Exit(code=1) from e


@app.command()
def instructions():
    """Show current coordination instructions."""
    try:
        instructions_content = coordination.get_instructions()
        typer.echo("--- Current Coordination Instructions ---")
        typer.echo(instructions_content)
    except FileNotFoundError as e:
        typer.echo(f"❌ {e}")
        typer.echo("Create instructions file to customize coordination protocol")


@app.command()
def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
):
    """Receive updates from a channel."""
    try:
        bridge_events.emit(
            "messages_receiving", {"channel": channel, "identity": identity}, identity=identity
        )
        channel_id = coordination.resolve_channel_id(channel)
        messages, count, context, participants = coordination.recv_updates(channel_id, identity)
        for msg in messages:
            bridge_events.emit(
                "message_received",
                {
                    "channel": channel,
                    "identity": identity,
                    "sender_id": msg.sender,
                    "content": msg.content,
                },
                identity=identity,
            )
            typer.echo(f"[{msg.sender}] {msg.content}")
            typer.echo()
    except Exception as e:
        bridge_events.emit(
            "error_occurred", {"command": "recv", "details": str(e)}, identity=identity
        )
        typer.echo(f"❌ Receive failed: {e}")
        raise typer.Exit(code=1) from e


@app.command()
def export(
    channel: str = typer.Argument(...),
):
    """Export channel transcript with interleaved notes."""
    try:
        data = coordination.export_channel(channel)

        typer.echo(f"# {data.channel_name}")
        typer.echo()
        if data.context:
            typer.echo(f"{data.context}")
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

    except Exception as e:
        typer.echo(f"❌ Export failed: {e}")
        raise typer.Exit(code=1) from e




@app.command()
def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
):
    """Show all unread alerts across all channels."""
    try:
        bridge_events.emit("alerts_checking", {"identity": identity}, identity=identity)
        alert_messages = coordination.get_alerts(identity)
        bridge_events.emit(
            "alerts_checked",
            {"identity": identity, "count": len(alert_messages)},
            identity=identity,
        )
        if not alert_messages:
            typer.echo(f"No alerts for {identity}")
            return

        typer.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
        for msg in alert_messages:
            typer.echo(f"\n[{msg.sender} | {msg.channel_id}]")
            typer.echo(msg.content)
    except Exception as exc:
        bridge_events.emit(
            "error_occurred", {"command": "alerts", "details": str(exc)}, identity=identity
        )
        typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def history(
    identity: str = typer.Option(..., "--as", help="Agent identity to fetch history for"),
    limit: Optional[int] = typer.Option(None, help="Limit results (weighted toward recent)"),
):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = coordination.fetch_sender_history(identity, limit)
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


def _stream_events(channel: str | None = None):
    """Helper function to stream bridge events, with optional channel filtering."""
    import time

    from .. import events

    # 1. Render historic events
    all_events = events.query(source="bridge", limit=1000)  # Increased limit for history
    for event_tuple in reversed(all_events):
        event = {
            "uuid": event_tuple[0],
            "source": event_tuple[1],
            "identity": event_tuple[2],
            "event_type": event_tuple[3],
            "data": event_tuple[4],
            "created_at": event_tuple[5],
        }
        if channel is None or (
            event.get("data") and event.get("data", {}).get("channel") == channel
        ):
            event_type = event.get("event_type")
            data = event.get("data", {})
            identity = event.get("identity")
            if event_type == "message_sent":
                typer.echo(f"→ Sent to {data.get('channel')} as {identity}: {data.get('content')}")
            elif event_type == "message_received":
                typer.echo(
                    f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}"
                )

    # 2. Start live stream
    renderer = Renderer()

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
                            "data": event_tuple[4],
                            "created_at": event_tuple[5],
                        }
                        if channel is None or (
                            event_data.get("data")
                            and event_data.get("data", {}).get("channel") == channel
                        ):
                            event_type = event_data.get("event_type")
                            data = event_data.get("data", {})
                            if event_type == "message_sent":
                                yield Event(
                                    type="token",
                                    content=f"→ Sent to {data.get('channel')} as {event_data.get('identity')}: {data.get('content')}\n",
                                )
                            elif event_type == "message_received":
                                yield Event(
                                    type="token",
                                    content=f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}\n",
                                )
                            else:
                                yield Event(type="status", content=f"Event: {event_type}")

                    last_event_uuid = new_events[0][0]

                time.sleep(1)
            except KeyboardInterrupt:
                yield Event(type="done")
                break

    renderer.render(event_stream())


@app.command()
def stream():
    """Stream all bridge events in real-time."""
    _stream_events()


@app.command()
def council(
    channel: str = typer.Argument(...),
):
    """Stream bridge events for a specific channel."""
    _stream_events(channel=channel)


if __name__ == "__main__":
    app()