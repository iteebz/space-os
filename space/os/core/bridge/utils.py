from datetime import datetime


def format_local_time(timestamp: str) -> str:
    """Format ISO timestamp as readable local time."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp


def format_channel_meta(channel) -> str:
    """Create a metadata string for a channel."""
    parts = []
    msgs = channel.message_count
    members = len(channel.participants)
    notes = channel.notes_count

    if msgs == 1:
        parts.append("1 msg")
    elif msgs > 1:
        parts.append(f"{msgs} msgs")

    if members == 1:
        parts.append("1 member")
    elif members > 1:
        parts.append(f"{members} members")

    if notes == 1:
        parts.append("1 note")
    elif notes > 1:
        parts.append(f"{notes} notes")
    return " | ".join(parts)


def format_channel_row(channel) -> tuple[str, str]:
    """Formats a channel object into a tuple of (last_activity_str, channel_info_str)."""
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"
    meta_str = format_channel_meta(channel)
    channel_id_suffix = channel.channel_id[-8:] if channel.channel_id else ""
    if meta_str:
        return last_activity, f"{channel.name} ({channel_id_suffix}) - {meta_str}"
    return last_activity, f"{channel.name} ({channel_id_suffix})"
