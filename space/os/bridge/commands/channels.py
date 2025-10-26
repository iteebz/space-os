"""Channel commands: list, create, rename, archive, pin, unpin, delete."""

import json
from datetime import datetime
from typing import Annotated

import typer

from space.os import spawn

from ..api import channels as ch


def format_channel_row(channel) -> tuple[str, str]:
    """Format channel for display. Returns (last_activity, description)."""
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"

    parts = []
    if channel.message_count:
        parts.append(f"{channel.message_count} msgs")
    if channel.participants:
        parts.append(f"{len(channel.participants)} members")
    if channel.notes_count:
        parts.append(f"{channel.notes_count} notes")

    meta_str = " | ".join(parts)
    channel_id_suffix = channel.channel_id[-8:] if channel.channel_id else ""

    if meta_str:
        return last_activity, f"{channel.name} ({channel_id_suffix}) - {meta_str}"
    return last_activity, f"{channel.name} ({channel_id_suffix})"


app = typer.Typer()


def format_local_time(timestamp: str) -> str:
    """Format ISO timestamp as readable local time."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


@app.command("list")
def list_channels_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    all: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List channels."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    if identity:
        spawn.get_agent(identity)

    chans = ch.list_channels(all=all)

    if not chans:
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
            for c in chans
        ]
        typer.echo(json.dumps(compact, indent=2))
        return

    active = [c for c in chans if not c.archived_at]
    archived = [c for c in chans if c.archived_at]
    active.sort(key=lambda t: t.name)
    archived.sort(key=lambda t: t.name)

    if not quiet_output:
        if active:
            typer.echo(f"ACTIVE CHANNELS ({len(active)}):")
            for channel in active:
                last_activity, description = format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")

        if all and archived:
            typer.echo(f"\nARCHIVED ({len(archived)}):")
            for channel in archived:
                last_activity, description = format_channel_row(channel)
                typer.echo(f"  {last_activity}: {description}")


@app.command("create")
def create_channel_cmd(
    ctx: typer.Context,
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: str = typer.Option(None, help="The initial topic for the channel."),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    try:
        if agent_id:
            pass
        channel_id = ch.create_channel(channel_name, topic)
        if agent_id:
            pass
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
            pass
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"❌ Error creating channel: {e}")


@app.command("rename")
def rename_channel_cmd(
    ctx: typer.Context,
    old_channel: str = typer.Argument(...),
    new_channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Rename channel."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    old_channel = old_channel.lstrip("#")
    new_channel = new_channel.lstrip("#")
    if agent_id:
        pass
    result = ch.rename_channel(old_channel, new_channel)
    if agent_id:
        pass
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


@app.command("archive")
def archive_channel_cmd(
    ctx: typer.Context,
    channels_arg: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    prefix: bool = typer.Option(False, "--prefix", help="Treat arguments as prefixes to match."),
):
    """Archive channels."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    names = channels_arg
    if prefix:
        chans = ch.list_channels()
        active = [c.name for c in chans if not c.archived_at]
        matched = []
        for pattern in channels_arg:
            matched.extend([name for name in active if name.startswith(pattern)])
        names = list(set(matched))

    results = []
    for name in names:
        try:
            if agent_id:
                pass
            ch.archive_channel(name)
            if agent_id:
                pass
            if json_output:
                results.append({"channel": name, "status": "archived"})
            elif not quiet_output:
                typer.echo(f"Archived channel: {name}")
        except ValueError:
            if agent_id:
                pass
            if json_output:
                results.append(
                    {"channel": name, "status": "error", "message": f"Channel '{name}' not found."}
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{name}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command("pin")
def pin_channel_cmd(
    ctx: typer.Context,
    channels_arg: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Pin channels."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    results = []
    for channel in channels_arg:
        try:
            if agent_id:
                pass
            ch.pin_channel(channel)
            if agent_id:
                pass
            if json_output:
                results.append({"channel": channel, "status": "pinned"})
            elif not quiet_output:
                typer.echo(f"Pinned channel: {channel}")
        except (ValueError, TypeError) as e:
            if agent_id:
                pass
            if json_output:
                results.append({"channel": channel, "status": "error", "message": str(e)})
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command("unpin")
def unpin_channel_cmd(
    ctx: typer.Context,
    channels_arg: Annotated[list[str], typer.Argument(...)],
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Unpin channels."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    results = []
    for channel in channels_arg:
        try:
            if agent_id:
                pass
            ch.unpin_channel(channel)
            if agent_id:
                pass
            if json_output:
                results.append({"channel": channel, "status": "unpinned"})
            elif not quiet_output:
                typer.echo(f"Unpinned channel: {channel}")
        except (ValueError, TypeError) as e:
            if agent_id:
                pass
            if json_output:
                results.append({"channel": channel, "status": "error", "message": str(e)})
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@app.command("delete")
def delete_channel_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(...),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Delete channel."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agent = spawn.get_agent(identity) if identity else None
    agent_id = agent.agent_id if agent else None
    try:
        if agent_id:
            pass
        ch.delete_channel(channel)
        if agent_id:
            pass
        if json_output:
            typer.echo(json.dumps({"status": "deleted", "channel": channel}))
        elif not quiet_output:
            typer.echo(f"Deleted channel: {channel}")
    except ValueError:
        if agent_id:
            pass
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
