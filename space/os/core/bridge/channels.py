import json
from typing import Annotated

import typer

from space.os import events
from space.os.core import spawn
from space.os.lib import output

from . import db, utils

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
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.invoked_subcommand is None:
        list_channels(ctx, all_channels_flag=all_channels_flag)


@app.command("list")
def list_channels(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    all_channels_flag: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    if identity:
        spawn.db.ensure_agent(identity)

    all_chans = (
        db.all_channels()
        if all_channels_flag
        else [c for c in db.all_channels() if not c.archived_at]
    )

    if not all_chans:
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
            for c in all_chans
        ]
        typer.echo(json.dumps(compact, indent=2))
        return

    active = [c for c in all_chans if not c.archived_at]
    archived = [c for c in all_chans if c.archived_at]
    active.sort(key=lambda t: t.name)
    archived.sort(key=lambda t: t.name)

    if not quiet_output:
        if active:
            typer.echo(f"ACTIVE CHANNELS ({len(active)}):")
            for channel in active:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")

        if all_channels_flag and archived:
            typer.echo(f"\nARCHIVED ({len(archived)}):")
            for channel in archived:
                last_activity, description = utils.format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")


@app.command()
def create(
    ctx: typer.Context,
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: Annotated[str, typer.Option(..., help="The initial topic for the channel.")] = None,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    try:
        if agent_id:
            events.emit(
                "bridge", "channel_creating", agent_id, json.dumps({"channel_name": channel_name})
            )
        channel_id = db.create_channel(channel_name, topic)
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
                "bridge", "error", agent_id, json.dumps({"command": "create", "details": str(e)})
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
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    old_channel = old_channel.lstrip("#")
    new_channel = new_channel.lstrip("#")
    if agent_id:
        events.emit(
            "bridge",
            "channel_renaming",
            agent_id,
            json.dumps({"old_channel": old_channel, "new_channel": new_channel}),
        )
    result = db.rename_channel(old_channel, new_channel)
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
        else:
            typer.echo(f"❌ Rename failed: {old_channel} not found or {new_channel} already exists")


@app.command()
def archive(
    ctx: typer.Context,
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    prefix: bool = typer.Option(False, "--prefix", help="Treat arguments as prefixes to match."),
):
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    names = channels
    if prefix:
        all_chans = db.all_channels()
        active = [c.name for c in all_chans if not c.archived_at]
        matched = []
        for pattern in channels:
            matched.extend([name for name in active if name.startswith(pattern)])
        names = list(set(matched))

    results = []
    for name in names:
        try:
            if agent_id:
                events.emit("bridge", "channel_archiving", agent_id, json.dumps({"channel": name}))
            db.archive_channel(name)
            if agent_id:
                events.emit("bridge", "channel_archived", agent_id, json.dumps({"channel": name}))
            if json_output:
                results.append({"channel": name, "status": "archived"})
            elif not quiet_output:
                typer.echo(f"Archived channel: {name}")
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
                    {"channel": name, "status": "error", "message": f"Channel '{name}' not found."}
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{name}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command()
def pin(
    ctx: typer.Context,
    channels: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    results = []
    for channel in channels:
        try:
            if agent_id:
                events.emit("bridge", "channel_pinning", agent_id, json.dumps({"channel": channel}))
            db.pin_channel(channel)
            if agent_id:
                events.emit("bridge", "channel_pinned", agent_id, json.dumps({"channel": channel}))
            if json_output:
                results.append({"channel": channel, "status": "pinned"})
            elif not quiet_output:
                typer.echo(f"Pinned channel: {channel}")
        except (ValueError, TypeError) as e:
            if agent_id:
                events.emit(
                    "bridge", "error", agent_id, json.dumps({"command": "pin", "details": str(e)})
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
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    results = []
    for channel in channels:
        try:
            if agent_id:
                events.emit(
                    "bridge", "channel_unpinning", agent_id, json.dumps({"channel": channel})
                )
            db.unpin_channel(channel)
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
                    "bridge", "error", agent_id, json.dumps({"command": "unpin", "details": str(e)})
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
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent_id = spawn.db.ensure_agent(identity) if identity else None
    try:
        if agent_id:
            events.emit("bridge", "channel_deleting", agent_id, json.dumps({"channel": channel}))
        db.delete_channel(channel)
        if agent_id:
            events.emit("bridge", "channel_deleted", agent_id, json.dumps({"channel": channel}))
        if json_output:
            typer.echo(json.dumps({"status": "deleted", "channel": channel}))
        elif not quiet_output:
            typer.echo(f"Deleted channel: {channel}")
    except ValueError as e:
        if agent_id:
            events.emit(
                "bridge", "error", agent_id, json.dumps({"command": "delete", "details": str(e)})
            )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
