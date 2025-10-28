"""CLI output formatting and helpers."""

import json
from datetime import datetime

import typer


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
