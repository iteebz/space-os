"""Bridge CLI - Clean command interface."""

import base64
import binascii
from datetime import datetime, timedelta
from pathlib import Path

import click

from .. import protocols
from . import config, coordination, utils
from .council import Council
from .storage.migration import MigrationError, migrate_store_db

if config.INSTRUCTIONS_FILE.exists():
    protocols.track("bridge", config.INSTRUCTIONS_FILE.read_text())


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Bridge: AI Coordination Protocol"""
    if ctx.invoked_subcommand is None:
        show_dashboard()


def show_dashboard() -> None:
    """Display coordination dashboard with instructions."""
    active = coordination.active_channels()

    click.echo("BRIDGE: AI Coordination Protocol")
    click.echo()

    if active:
        click.echo("ACTIVE CHANNELS:")
        for ch in active:
            ago = utils.format_time_ago(ch.last_activity)
            meta = f"{ch.message_count} msgs | {len(ch.participants)} members"
            click.echo(f"  {ch.name} - {ago} | {meta}")
        click.echo()

    try:
        instructions = coordination.get_instructions()
        click.echo(instructions)
    except FileNotFoundError as e:
        click.echo(f"❌ {e}")
        click.echo("Create instructions file to customize coordination protocol")


@main.command("channels")
def channels():
    """List all channels with metadata."""
    all_channels = coordination.all_channels()

    if not all_channels:
        click.echo("No channels found")
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

    click.echo("--- Active Channels ---")

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
        click.echo(f"{last_activity}: {channel.name} - {meta_str}")

    if archived_channels:
        click.echo("\n--- Archived Channels ---")
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
            click.echo(f"{last_activity}: {channel.name} - {meta_str}")


@main.command()
@click.argument("old_channel")
@click.argument("new_channel")
def rename(old_channel, new_channel):
    """Rename channel and preserve all coordination data."""
    success = coordination.rename_channel(old_channel, new_channel)
    if success:
        click.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        click.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@main.command()
@click.argument("channel")
def council(channel):
    """Interactive human coordination interface."""
    Council(channel=channel, identity="detective").run()


@main.command()
@click.argument("channels", nargs=-1, required=True)
def archive(channels):
    """Archive channels by setting creation date to 30 days ago."""
    for channel in channels:
        coordination.archive_channel(channel)
        click.echo(f"Archived channel: {channel}")


@main.command()
@click.argument("channel")
def delete(channel):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    coordination.delete_channel(channel)
    click.echo(f"Deleted channel: {channel}")


@main.command("migrate-db")
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


@main.command()
@click.argument("channel")
@click.argument("content")
@click.option("--as", "identity", default="human", help="Identity (defaults to human)")
@click.option("--base64", "decode_base64", is_flag=True, help="Decode base64 payload")
def send(channel, content, identity, decode_base64):
    """Send a message to a channel."""
    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise click.BadParameter("Invalid base64 payload", param_hint="content") from exc

    try:
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content)
        click.echo(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
        )
    except Exception as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@main.command()
@click.argument("channel")
@click.argument("content")
@click.option("--as", "identity", required=True, help="Identity sending alert")
def alert(channel, content, identity):
    """Send high-priority alert to a channel."""
    try:
        channel_id = coordination.resolve_channel_id(channel)
        coordination.send_message(channel_id, identity, content, priority="alert")
        click.echo(f"Alert sent to {channel} as {identity}")
    except Exception as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@main.command()
@click.argument("channel")
@click.argument("content", required=False)
@click.option("--as", "identity", help="Your agent identity (claude/gemini/codex)")
def notes(channel, content, identity):
    """Show notes for channel, or add note with content and --as identity."""
    if content is None:
        # Show notes mode
        try:
            channel_id = coordination.resolve_channel_id(channel)
            notes = coordination.get_notes(channel_id)
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
    else:
        # Add note mode
        if not identity:
            click.echo("❌ Must specify --as identity when adding notes")
            raise click.Abort()
        try:
            channel_id = coordination.resolve_channel_id(channel)
            coordination.add_note(channel_id, identity, content)
            click.echo(f"Added note to {channel}")
        except Exception as e:
            click.echo(f"❌ Note failed: {e}")
            raise click.Abort() from e


@main.command()
def instructions():
    """Show current coordination instructions."""
    try:
        instructions_content = coordination.get_instructions()
        click.echo("--- Current Coordination Instructions ---")
        click.echo(instructions_content)
    except FileNotFoundError as e:
        click.echo(f"❌ {e}")
        click.echo("Create instructions file to customize coordination protocol")


@main.command()
@click.argument("channel")
@click.option("--as", "identity", required=True, help="Agent identity to receive as")
def recv(channel, identity):
    """Receive updates from a channel."""
    try:
        channel_id = coordination.resolve_channel_id(channel)
        messages, count, context, participants = coordination.recv_updates(channel_id, identity)

        if not messages:
            click.echo(f"No new messages in {channel}")
            return

        click.echo(f"--- {channel} ({count} new) ---")
        if context:
            click.echo(f"Context: {context}\n")

        for msg in messages:
            click.echo(f"[{msg.sender}] {msg.content}")
            click.echo()
    except Exception as e:
        click.echo(f"❌ Receive failed: {e}")
        raise click.Abort() from e


@main.command()
@click.argument("channel")
def export(channel):
    """Export channel transcript with interleaved notes."""
    try:
        data = coordination.export_channel(channel)

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


@main.command()
def backup():
    """Backup Bridge data to timestamped directory."""
    try:
        from bridge.backup import backup_bridge_data

        backup_path = backup_bridge_data()
        click.echo(f"✅ Backup created: {backup_path}")
    except Exception as e:
        click.echo(f"❌ Backup failed: {e}")


@main.command()
@click.option("--as", "identity", required=True, help="Agent identity to check alerts for")
def alerts(identity):
    """Show all unread alerts across all channels."""
    try:
        alert_messages = coordination.get_alerts(identity)
        if not alert_messages:
            click.echo(f"No alerts for {identity}")
            return

        click.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
        for msg in alert_messages:
            click.echo(f"\n[{msg.sender} | {msg.channel_id}]")
            click.echo(msg.content)
    except Exception as exc:
        click.echo(f"❌ {exc}")
        raise click.Abort() from exc


@main.command()
@click.option("--as", "identity", required=True, help="Agent identity to fetch history for")
@click.option("--limit", type=int, help="Limit results (weighted toward recent)")
def history(identity, limit):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = coordination.fetch_sender_history(identity, limit)
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


if __name__ == "__main__":
    main()
