"""Bridge CLI: flat command structure."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

import typer

from space.lib import output
from space.os import spawn
from space.os.bridge import api


def format_channel_row(channel) -> tuple[str, str]:
    """Format channel for display. Returns (last_activity, description)."""
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"

    parts = []
    if channel.message_count:
        parts.append(f"{channel.message_count} msgs")
    if channel.members:
        parts.append(f"{len(channel.members)} members")
    meta_str = " | ".join(parts)
    channel_id_suffix = channel.channel_id[-8:] if channel.channel_id else ""

    if meta_str:
        return last_activity, f"{channel.name} ({channel_id_suffix}) - {meta_str}"
    return last_activity, f"{channel.name} ({channel_id_suffix})"


def format_local_time(timestamp: str) -> str:
    """Format ISO timestamp as readable local time."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


def output_json(data, ctx: typer.Context):
    """Output data as JSON if requested. Returns True if output, False otherwise."""
    if ctx.obj.get("json_output"):
        typer.echo(json.dumps(data, indent=2))
        return True
    return False


def should_output(ctx: typer.Context) -> bool:
    """Check if output should be printed (not quiet mode)."""
    return not ctx.obj.get("quiet_output")


def echo_if_output(msg: str, ctx: typer.Context):
    """Echo message only if not in quiet mode."""
    if should_output(ctx):
        typer.echo(msg)


app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Coordinate through immutable channels. Messages are append-only—once sent, they persist.
    Read before deciding. Let other agents see your thinking."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def archive(
    ctx: typer.Context,
    channels_arg: list[str] = typer.Argument(...),
    restore: bool = typer.Option(False, "--restore", help="Restore archived channel"),
):
    """Archive or restore channel (--restore to undo)."""
    try:
        names = channels_arg
        results = []
        for name in names:
            try:
                if restore:
                    api.restore_channel(name)
                    status = "restored"
                else:
                    api.archive_channel(name)
                    status = "archived"
                results.append({"channel": name, "status": status})
                echo_if_output(f"{status.capitalize()} channel: {name}", ctx)
            except ValueError as e:
                results.append(
                    {
                        "channel": name,
                        "status": "error",
                        "message": str(e),
                    }
                )
                echo_if_output(f"❌ {e}", ctx)
        if ctx.obj.get("json_output"):
            typer.echo(json.dumps(results))
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def channels(
    ctx: typer.Context,
    all: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List active and archived channels."""
    try:
        chans = api.list_channels(all=all)

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


@app.command()
def create(
    ctx: typer.Context,
    channel_name: str = typer.Argument(..., help="Channel name"),
    topic: str = typer.Option(None, help="Channel topic"),
):
    """Create new channel."""
    try:
        channel_obj = api.create_channel(channel_name, topic)
        channel_id = channel_obj.channel_id
        output_json(
            {"status": "success", "channel_name": channel_name, "channel_id": channel_id}, ctx
        ) or echo_if_output(f"Created channel: {channel_name} (ID: {channel_id})", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
            f"❌ Error creating channel: {e}", ctx
        )
        raise typer.Exit(code=1) from e


@app.command("delete")
def delete(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to delete"),
):
    """Remove channel permanently."""
    try:
        api.delete_channel(channel)
        output_json({"status": "deleted", "channel": channel}, ctx) or echo_if_output(
            f"Deleted channel: {channel}", ctx
        )
    except ValueError as e:
        output_json(
            {"status": "error", "message": f"Channel '{channel}' not found."}, ctx
        ) or echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def export(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel name or ID"),
):
    """Dump channel as markdown."""
    try:
        export_data = api.export_channel(channel)

        if output_json(
            {
                "channel_id": export_data.channel_id,
                "channel_name": export_data.channel_name,
                "topic": export_data.topic,
                "created_at": export_data.created_at,
                "members": export_data.members,
                "message_count": export_data.message_count,
                "messages": [
                    {
                        "message_id": msg.message_id,
                        "agent_id": msg.agent_id,
                        "content": msg.content,
                        "created_at": msg.created_at,
                    }
                    for msg in export_data.messages
                ],
            },
            ctx,
        ):
            return

        echo_if_output(f"# {export_data.channel_name}", ctx)
        if export_data.topic:
            echo_if_output(f"\n**Topic:** {export_data.topic}", ctx)

        echo_if_output(f"\n## Messages ({export_data.message_count})", ctx)
        for msg in export_data.messages:
            echo_if_output(f"\n**{msg.agent_id}** ({msg.created_at}):", ctx)
            echo_if_output(msg.content, ctx)

    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def inbox(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Agent identity"),
):
    """List unread channels for agent."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        chans = api.fetch_inbox(agent.agent_id)
        if not chans:
            output_json([], ctx) or echo_if_output("Inbox empty", ctx)
            return

        output_json([asdict(c) for c in chans], ctx) or None
        if should_output(ctx):
            echo_if_output(f"INBOX ({len(chans)}):", ctx)
            for channel in chans:
                last_activity, description = format_channel_row(channel)
                echo_if_output(f"  {last_activity}: {description}", ctx)
    except Exception as exc:
        output_json({"status": "error", "message": str(exc)}, ctx) or echo_if_output(
            f"❌ {exc}", ctx
        )
        raise typer.Exit(code=1) from exc


@app.command()
def pin(
    ctx: typer.Context,
    channels_arg: list[str] = typer.Argument(...),
):
    """Pin or unpin channels."""
    try:
        results = []
        for channel in channels_arg:
            try:
                is_pinned = api.toggle_pin_channel(channel)
                status = "pinned" if is_pinned else "unpinned"
                results.append({"channel": channel, "status": status})
                echo_if_output(f"{status.capitalize()} channel: {channel}", ctx)
            except (ValueError, TypeError) as e:
                results.append({"channel": channel, "status": "error", "message": str(e)})
                echo_if_output(f"❌ Channel '{channel}' not found.", ctx)
        if ctx.obj.get("json_output"):
            typer.echo(json.dumps(results))
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def recv(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to read from"),
    identity: str = typer.Option(..., "--as", help="Receiver identity"),
):
    """Read unread messages from channel."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        msgs, count, context, participants = api.recv_messages(channel, identity)

        output_json(
            {
                "messages": [asdict(msg) for msg in msgs],
                "count": count,
                "context": context,
                "participants": participants,
            },
            ctx,
        ) or None
        if should_output(ctx):
            for msg in msgs:
                sender = spawn.get_agent(msg.agent_id)
                sender_name = sender.identity if sender else msg.agent_id[:8]
                echo_if_output(f"[{sender_name}] {msg.content}", ctx)
                echo_if_output("", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def send(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Target channel"),
    content: str = typer.Argument(..., help="Message content"),
    identity: str = typer.Option("human", "--as", help="Sender identity"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 content"),
):
    """Post message to channel."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        api.send_message(channel, identity, content, decode_base64_flag=decode_base64)
        output_json(
            {"status": "success", "channel": channel, "identity": identity}, ctx
        ) or echo_if_output(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}",
            ctx,
        )
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def rename(
    ctx: typer.Context,
    old_channel: str = typer.Argument(..., help="Current channel name"),
    new_channel: str = typer.Argument(..., help="New channel name"),
):
    """Change channel name."""
    try:
        result = api.rename_channel(old_channel, new_channel)
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
                f"❌ Rename failed: {old_channel} not found or {new_channel} already exists",
                ctx,
            )
        )
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
def wait(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to monitor"),
    identity: str = typer.Option(..., "--as", help="Receiver identity"),
    poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
):
    """Block until new message arrives."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        other_messages, count, context, participants = api.wait_for_message(
            channel, identity, poll_interval
        )
        output_json(
            {
                "messages": [asdict(msg) for msg in other_messages],
                "count": count,
                "context": context,
                "participants": participants,
            },
            ctx,
        ) or None
        if should_output(ctx):
            for msg in other_messages:
                sender = spawn.get_agent(msg.agent_id)
                sender_name = sender.identity if sender else msg.agent_id[:8]
                echo_if_output(f"[{sender_name}] {msg.content}", ctx)
                echo_if_output("", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        echo_if_output("\n", ctx)
        raise typer.Exit(code=0) from None
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main"]
