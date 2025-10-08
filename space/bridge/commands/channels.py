from datetime import datetime, timedelta
from typing import Annotated

import typer

from .. import api

app = typer.Typer()


@app.command("channels")
def channels():
    """List all channels with metadata."""
    all_channels = api.all_channels()

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
def create(
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: Annotated[str, typer.Option(..., help="The initial topic for the channel.")] = None,
):
    """Create a new channel with an optional initial topic."""
    try:
        channel_id = api.create_channel(channel_name, topic)
        typer.echo(f"Created channel: {channel_name} (ID: {channel_id})")
    except ValueError as e:
        typer.echo(f"❌ Error creating channel: {e}")


@app.command()
def rename(
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
):
    """Rename channel and preserve all coordination data."""
    success = api.rename_channel(old_channel, new_channel)
    if success:
        typer.echo(f"Renamed channel: {old_channel} -> {new_channel}")
    else:
        typer.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@app.command()
def archive(
    channels: Annotated[list[str], typer.Argument(...)],
):
    """Archive channels by setting creation date to 30 days ago."""
    for channel in channels:
        try:
            api.archive_channel(channel)
            typer.echo(f"Archived channel: {channel}")
        except ValueError:
            typer.echo(f"❌ Channel '{channel}' not found.")


@app.command()
def delete(
    channel: str = typer.Argument(...),
):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    try:
        api.delete_channel(channel)
        typer.echo(f"Deleted channel: {channel}")
    except ValueError:
        typer.echo(f"❌ Channel '{channel}' not found.")
