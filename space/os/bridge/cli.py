"""Bridge CLI: flat command structure."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Annotated

import typer

from space.cli import argv, output
from space.cli.errors import error_feedback
from space.os import spawn
from space.os.bridge import api

argv.flex_args("as")


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


output_json = output.echo_json


def should_output(ctx):
    return not output.is_quiet_mode(ctx)


echo_if_output = output.echo_text


def _resolve_identity(ctx) -> str | None:
    """Resolve identity from --as flag, env var, or None."""
    import os

    return ctx.obj.get("identity") or os.environ.get("SPACE_AGENT_IDENTITY")


app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity to use.")] = None,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Coordinate through immutable channels. Messages are append-only—once sent, they persist.
    Read before deciding. Let other agents see your thinking."""
    output.init_context(ctx, json_output, quiet_output, identity)
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
@error_feedback
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
@error_feedback
def channels(
    ctx: typer.Context,
    all: bool = typer.Option(False, "--all", help="Include archived channels"),
):
    """List active and archived channels."""
    try:
        chans = api.list_channels(show_all=all)

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
@error_feedback
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
@error_feedback
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
@error_feedback
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
@error_feedback
def recv(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to read from"),
    ago: str = typer.Option(None, "--ago", help="Time window (e.g., 1h, 30m)"),
    reader: str = typer.Option(None, "--reader", help="Explicit reader ID for bookmark tracking"),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON instead of markdown"
    ),
):
    """Read messages from channel (markdown by default)."""
    import os
    import sys

    try:
        reader_id = None

        spawn_id = os.environ.get("SPACE_SPAWN_ID")
        if spawn_id:
            reader_id = spawn_id
        elif reader:
            reader_id = reader
        else:
            identity = _resolve_identity(ctx)
            if identity:
                agent = spawn.get_agent(identity)
                if agent:
                    reader_id = agent.agent_id
                    if sys.stderr.isatty():
                        typer.echo(
                            "⚠ Using agent-scoped bookmark (shared across manual sessions). "
                            "For isolation, use --reader <id>",
                            err=True,
                        )

        msgs, count, context, participants = api.recv_messages(channel, ago, reader_id)
        if should_output(ctx):
            output = api.format_messages(msgs, context or "Messages", as_json=json_output)
            typer.echo(output)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
@error_feedback
def send(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Target channel"),
    content: str = typer.Argument(..., help="Message content"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 content"),
):
    """Post message to channel."""
    import asyncio

    try:
        identity = _resolve_identity(ctx) or "human"
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        asyncio.run(api.send_message(channel, identity, content, decode_base64=decode_base64))
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
@error_feedback
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
@error_feedback
def topic(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel name"),
    new_topic: str = typer.Argument(..., help="New topic"),
):
    """Update channel topic."""
    try:
        result = api.update_topic(channel, new_topic if new_topic else None)
        output_json(
            {
                "status": "success" if result else "failed",
                "channel": channel,
                "topic": new_topic,
            },
            ctx,
        ) or (
            echo_if_output(f"Updated topic for #{channel}", ctx)
            if result
            else echo_if_output(f"❌ Channel '{channel}' not found", ctx)
        )
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command()
@error_feedback
def wait(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to monitor"),
    poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
):
    """Block until new message arrives."""
    try:
        identity = _resolve_identity(ctx)
        if not identity:
            raise ValueError("Identity required: use --as or set SPACE_AGENT_IDENTITY")
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
