import json
from typing import Annotated

import typer

from ... import events
from .. import api, utils
from space.spawn import registry

app = typer.Typer(invoke_without_command=True)


@app.callback()
def channels_root(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON output"),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Bridge channel operations (defaults to listing)."""
    if ctx.invoked_subcommand is None:
        list_channels(json_output=json_output, quiet_output=quiet_output)


@app.command("list")
def list_channels(
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List all channels with metadata."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    if agent_id:
        events.emit("bridge", "channels_listing", agent_id, "")
    all_channels = api.all_channels()
    if agent_id:
        events.emit("bridge", "channels_listed", agent_id, json.dumps({"count": len(all_channels)}))

    if not all_channels:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No channels found")
        return

    if json_output:
        compact = [
            {
                "name": c.name,
                "topic": c.topic,
                "message_count": c.message_count,
                "last_activity": c.last_activity,
                "unread_count": c.unread_count,
                "archived_at": c.archived_at,
            }
            for c in all_channels
        ]
        typer.echo(json.dumps(compact, indent=2))
        return

    active_channels = []
    archived_channels = []

    for channel in all_channels:
        if channel.archived_at:
            archived_channels.append(channel)
        else:
            active_channels.append(channel)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    if not quiet_output:
        typer.echo(f"--- Active Channels ({len(active_channels)}) ---")

        for channel in active_channels:
            last_activity, description = utils.format_channel_row(channel)
            typer.echo(f"{last_activity}: {description}")

        if archived_channels:
            typer.echo(f"\n--- Archived Channels ({len(archived_channels)}) ---")
            for channel in archived_channels:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"{last_activity}: {description}")


@app.command()
def create(
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: Annotated[str, typer.Option(..., help="The initial topic for the channel.")] = None,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Create a new channel with an optional initial topic."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit("bridge", "channel_creating", agent_id, json.dumps({"channel_name": channel_name}))
        channel_id = api.create_channel(channel_name, topic)
        if agent_id:
            events.emit("bridge", "channel_created", agent_id, json.dumps({"channel_name": channel_name, "channel_id": channel_id}))
        if json_output:
            typer.echo(
                json.dumps(
                    {"status": "success", "channel_name": channel_name, "channel_id": channel_id}
                )
            )
        elif not quiet_output:
            typer.echo(f"Created channel: {channel_name} (ID: {channel_id})")
    except ValueError as e:
        if agent_id:
            events.emit("bridge", "error_occurred", agent_id, json.dumps({"command": "create", "details": str(e)}))
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"❌ Error creating channel: {e}")


@app.command()
def rename(
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Rename channel and preserve all coordination data."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    old_channel = old_channel.lstrip("#")
    new_channel = new_channel.lstrip("#")
    if agent_id:
        events.emit("bridge", "channel_renaming", agent_id, json.dumps({"old_channel": old_channel, "new_channel": new_channel}))
    success = api.rename_channel(old_channel, new_channel)
    if agent_id:
        status = "success" if success else "failed"
        events.emit("bridge", f"channel_rename_{status}", agent_id, json.dumps({"old_channel": old_channel, "new_channel": new_channel}))
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "status": "success" if success else "failed",
                    "old_channel": old_channel,
                    "new_channel": new_channel,
                }
            )
        )
    elif not quiet_output:
        if success:
            typer.echo(f"Renamed channel: {old_channel} -> {new_channel}")
        else:
            typer.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@app.command()
def archive(
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    prefix: bool = typer.Option(False, "--prefix", help="Treat arguments as prefixes to match."),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Archive channels by marking them inactive."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    channel_names = channels
    if prefix:
        all_channels = api.all_channels()
        active = [c.name for c in all_channels if not c.archived_at]
        matched = []
        for pattern in channels:
            matched.extend([name for name in active if name.startswith(pattern)])
        channel_names = list(set(matched))

    results = []
    for channel_name in channel_names:
        try:
            if agent_id:
                events.emit("bridge", "channel_archiving", agent_id, json.dumps({"channel": channel_name}))
            api.archive_channel(channel_name)
            if agent_id:
                events.emit("bridge", "channel_archived", agent_id, json.dumps({"channel": channel_name}))
            if json_output:
                results.append({"channel": channel_name, "status": "archived"})
            elif not quiet_output:
                typer.echo(f"Archived channel: {channel_name}")
        except ValueError as e:
            if agent_id:
                events.emit("bridge", "error_occurred", agent_id, json.dumps({"command": "archive", "details": str(e)}))
            if json_output:
                results.append(
                    {
                        "channel": channel_name,
                        "status": "error",
                        "message": f"Channel '{channel_name}' not found.",
                    }
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel_name}' not found. Run `bridge` to list channels.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command()
def delete(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    agent_id = registry.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit("bridge", "channel_deleting", agent_id, json.dumps({"channel": channel}))
        api.delete_channel(channel)
        if agent_id:
            events.emit("bridge", "channel_deleted", agent_id, json.dumps({"channel": channel}))
        if json_output:
            typer.echo(json.dumps({"status": "deleted", "channel": channel}))
        elif not quiet_output:
            typer.echo(f"Deleted channel: {channel}")
    except ValueError as e:
        if agent_id:
            events.emit("bridge", "error_occurred", agent_id, json.dumps({"command": "delete", "details": str(e)}))
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
