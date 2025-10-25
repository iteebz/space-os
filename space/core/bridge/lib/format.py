"""Formatting utilities for CLI output."""

from datetime import datetime


def format_local_time(timestamp: str) -> str:
    """Format ISO timestamp as readable local time."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


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
