"""Channel subcommand app: list, create, rename, archive, pin, unpin, delete."""

import json

import typer

from space.os.bridge import ops

from .format import echo_if_output, format_channel_row, output_json, should_output

app = typer.Typer(help="Manage channels")


@app.command("list")
def list_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    all: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List all channels with activity metadata."""
    try:
        chans = ops.list_channels(all=all)

        if not chans:
            output_json([], ctx) or echo_if_output("No channels found", ctx)
            return

        if output_json(
            [
                {
                    "name": c.name,
                    "topic": c.topic,
                    "message_count": c.message_count,
                    "last_activity": c.last_activity,
                    "unread_count": c.unread_count,
                    "archived_at": c.archived_at,
                }
                for c in chans
            ],
            ctx,
        ):
            return

        active = [c for c in chans if not c.archived_at]
        archived = [c for c in chans if c.archived_at]
        active.sort(key=lambda t: t.name)
        archived.sort(key=lambda t: t.name)

        if not should_output(ctx):
            return

        if active:
            echo_if_output(f"ACTIVE CHANNELS ({len(active)}):", ctx)
            for channel in active:
                last_activity, description = format_channel_row(channel)
                echo_if_output(f"  {last_activity}: {description}", ctx)

        if all and archived:
            echo_if_output(f"\nARCHIVED ({len(archived)}):", ctx)
            for channel in archived:
                last_activity, description = format_channel_row(channel)
                echo_if_output(f"  {last_activity}: {description}", ctx)
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("create")
def create_cmd(
    ctx: typer.Context,
    channel_name: str = typer.Argument(..., help="Channel name"),
    topic: str = typer.Option(None, help="Initial channel topic"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Create a new channel."""
    try:
        channel_id = ops.create_channel(channel_name, topic)
        output_json(
            {"status": "success", "channel_name": channel_name, "channel_id": channel_id}, ctx
        ) or echo_if_output(f"Created channel: {channel_name} (ID: {channel_id})", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
            f"❌ Error creating channel: {e}", ctx
        )
        raise typer.Exit(code=1) from e


@app.command("rename")
def rename_cmd(
    ctx: typer.Context,
    old_channel: str = typer.Argument(..., help="Current channel name"),
    new_channel: str = typer.Argument(..., help="New channel name"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Rename an existing channel."""
    try:
        result = ops.rename_channel(old_channel, new_channel)
        output_json(
            {
                "status": "success" if result else "failed",
                "old_channel": old_channel,
                "new_channel": new_channel,
            },
            ctx,
        ) or (
            echo_if_output(f"Renamed channel: {old_channel} -> {new_channel}", ctx)
            if result
            else echo_if_output(
                f"❌ Rename failed: {old_channel} not found or {new_channel} already exists", ctx
            )
        )
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("archive")
def archive_cmd(
    ctx: typer.Context,
    channels_arg: list[str] = typer.Argument(..., help="Channels to archive"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    prefix: bool = typer.Option(False, "--prefix", help="Match channels by prefix"),
):
    """Archive one or more channels."""
    try:
        names = channels_arg
        if prefix:
            chans = ops.list_channels()
            active = [c.name for c in chans if not c.archived_at]
            matched = []
            for pattern in channels_arg:
                matched.extend([name for name in active if name.startswith(pattern)])
            names = list(set(matched))

        results = []
        for name in names:
            try:
                ops.archive_channel(name)
                results.append({"channel": name, "status": "archived"})
                echo_if_output(f"Archived channel: {name}", ctx)
            except ValueError:
                results.append(
                    {"channel": name, "status": "error", "message": f"Channel '{name}' not found."}
                )
                echo_if_output(f"❌ Channel '{name}' not found.", ctx)
        if ctx.obj.get("json_output"):
            typer.echo(json.dumps(results))
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("pin")
def pin_cmd(
    ctx: typer.Context,
    channels_arg: list[str] = typer.Argument(..., help="Channels to pin"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Pin channels to favorites."""
    try:
        results = []
        for channel in channels_arg:
            try:
                ops.pin_channel(channel)
                results.append({"channel": channel, "status": "pinned"})
                echo_if_output(f"Pinned channel: {channel}", ctx)
            except (ValueError, TypeError) as e:
                results.append({"channel": channel, "status": "error", "message": str(e)})
                echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
        if ctx.obj.get("json_output"):
            typer.echo(json.dumps(results))
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("unpin")
def unpin_cmd(
    ctx: typer.Context,
    channels_arg: list[str] = typer.Argument(..., help="Channels to unpin"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Unpin channels from favorites."""
    try:
        results = []
        for channel in channels_arg:
            try:
                ops.unpin_channel(channel)
                results.append({"channel": channel, "status": "unpinned"})
                echo_if_output(f"Unpinned channel: {channel}", ctx)
            except (ValueError, TypeError) as e:
                results.append({"channel": channel, "status": "error", "message": str(e)})
                echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
        if ctx.obj.get("json_output"):
            typer.echo(json.dumps(results))
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("delete")
def delete_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to delete"),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
):
    """Delete a channel permanently."""
    try:
        ops.delete_channel(channel)
        output_json({"status": "deleted", "channel": channel}, ctx) or echo_if_output(
            f"Deleted channel: {channel}", ctx
        )
    except ValueError:
        output_json(
            {"status": "error", "message": f"Channel '{channel}' not found."}, ctx
        ) or echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
        raise typer.Exit(code=1)
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
