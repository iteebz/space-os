import json
from typing import Annotated

import typer

from space.os.lib import output
from space.os.spawn import db as spawn_db

from ... import events
from .. import api, utils

app = typer.Typer(invoke_without_command=True)


@app.callback()
def channels_root(
    ctx: typer.Context,
    all_channels_flag: bool = typer.Option(False, "--all", help="Include archived channels"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Bridge channel operations (defaults to listing)."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.invoked_subcommand is None:
        list_channels(
            ctx,
            all_channels_flag=all_channels_flag,
        )


@app.command("list")
def list_channels(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    all_channels_flag: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List channels (active by default, use --all for archived)."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    all_channels = (
        api.all_channels()
        if all_channels_flag
        else [c for c in api.all_channels() if not c.archived_at]
    )

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
        if active_channels:
            typer.echo(f"ACTIVE CHANNELS ({len(active_channels)}):")
            for channel in active_channels:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")

        if all_channels_flag and archived_channels:
            typer.echo(f"\nARCHIVED ({len(archived_channels)}):")
            for channel in archived_channels:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")


@app.command()
def create(
    ctx: typer.Context,
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: Annotated[str, typer.Option(..., help="The initial topic for the channel.")] = None,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Create a new channel with an optional initial topic."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    try:
        if agent_id:
            events.emit(
                "bridge", "channel_creating", agent_id, json.dumps({"channel_name": channel_name})
            )
        channel_id = api.create_channel(channel_name, topic)
        if agent_id:
            events.emit(
                "bridge",
                "channel_created",
                agent_id,
                json.dumps({"channel_name": channel_name, "channel_id": channel_id}),
            )
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
            events.emit(
                "bridge",
                "error",
                agent_id,
                json.dumps({"command": "create", "details": str(e)}),
            )
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"❌ Error creating channel: {e}")


@app.command()
def rename(
    ctx: typer.Context,
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Rename channel and preserve all coordination data."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    old_channel = old_channel.lstrip("#")
    new_channel = new_channel.lstrip("#")
    if agent_id:
        events.emit(
            "bridge",
            "channel_renaming",
            agent_id,
            json.dumps({"old_channel": old_channel, "new_channel": new_channel}),
        )
    result = api.rename_channel(old_channel, new_channel)
    if agent_id:
        status = "success" if result is True else "failed"
        events.emit(
            "bridge",
            f"channel_rename_{status}",
            agent_id,
            json.dumps({"old_channel": old_channel, "new_channel": new_channel}),
        )
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "status": "success" if result is True else "failed",
                    "old_channel": old_channel,
                    "new_channel": new_channel,
                }
            )
        )
    elif not quiet_output:
        if result is True:
            typer.echo(f"Renamed channel: {old_channel} -> {new_channel}")
        elif result == "archived":
            msg = f"❌ Rename failed: {new_channel} exists as archived channel"
            typer.echo(f"{msg} (rename the archived channel first)")
        else:
            msg = f"❌ Rename failed: {old_channel} not found or"
            typer.echo(f"{msg} {new_channel} already exists")


@app.command()
def archive(
    ctx: typer.Context,
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    prefix: bool = typer.Option(False, "--prefix", help="Treat arguments as prefixes to match."),
):
    """Archive channels by marking them inactive."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    channel_names = channels
    if prefix:
        all_channels = api.all_channels()
        active = [c.name for c in all_channels if not c.archived_at]
        matched = []
        for pattern in channels:
            matched.extend([name for name in active if name.startswith(pattern)])
        channel_names = list(set(matched))

    print(f"Channel names to archive: {channel_names}")

    results = []
    for channel_name in channel_names:
        try:
            if agent_id:
                events.emit(
                    "bridge", "channel_archiving", agent_id, json.dumps({"channel": channel_name})
                )
            api.archive_channel(channel_name)
            if agent_id:
                events.emit(
                    "bridge", "channel_archived", agent_id, json.dumps({"channel": channel_name})
                )
            if json_output:
                results.append({"channel": channel_name, "status": "archived"})
            elif not quiet_output:
                typer.echo(f"Archived channel: {channel_name}")
        except ValueError as e:
            if agent_id:
                events.emit(
                    "bridge",
                    "error",
                    agent_id,
                    json.dumps({"command": "archive", "details": str(e)}),
                )
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
def pin(
    ctx: typer.Context,
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Pin channels to wake view."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    results = []
    for channel in channels:
        try:
            if agent_id:
                events.emit("bridge", "channel_pinning", agent_id, json.dumps({"channel": channel}))
            api.pin_channel(channel)
            if agent_id:
                events.emit("bridge", "channel_pinned", agent_id, json.dumps({"channel": channel}))
            if json_output:
                results.append({"channel": channel, "status": "pinned"})
            elif not quiet_output:
                typer.echo(f"Pinned channel: {channel}")
        except (ValueError, TypeError) as e:
            if agent_id:
                events.emit(
                    "bridge",
                    "error",
                    agent_id,
                    json.dumps({"command": "pin", "details": str(e)}),
                )
            if json_output:
                results.append({"channel": channel, "status": "error", "message": str(e)})
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command()
def unpin(
    ctx: typer.Context,
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Unpin channels from wake view."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
    results = []
    for channel in channels:
        try:
            if agent_id:
                events.emit(
                    "bridge", "channel_unpinning", agent_id, json.dumps({"channel": channel})
                )
            api.unpin_channel(channel)
            if agent_id:
                events.emit(
                    "bridge", "channel_unpinned", agent_id, json.dumps({"channel": channel})
                )
            if json_output:
                results.append({"channel": channel, "status": "unpinned"})
            elif not quiet_output:
                typer.echo(f"Unpinned channel: {channel}")
        except (ValueError, TypeError) as e:
            if agent_id:
                events.emit(
                    "bridge",
                    "error",
                    agent_id,
                    json.dumps({"command": "unpin", "details": str(e)}),
                )
            if json_output:
                results.append({"channel": channel, "status": "error", "message": str(e)})
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command()
def delete(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Permanently delete channel and all messages (HUMAN ONLY)."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn_db.ensure_agent(identity) if identity and isinstance(identity, str) else None
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
            events.emit(
                "bridge",
                "error",
                agent_id,
                json.dumps({"command": "delete", "details": str(e)}),
            )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
