import hashlib
from datetime import datetime, timezone


def hash_content(content: str) -> str:
    """Generates an 8-character SHA256 hash for quick display."""
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def hash_digest(content: str) -> str:
    """Generates the full SHA256 digest for integrity checks."""
    return hashlib.sha256(content.encode()).hexdigest()


def format_local_time(iso_timestamp: str, fmt: str = "%H:%M:%S") -> str:
    """Converts an ISO format UTC timestamp string to local time and formats it."""
    if not iso_timestamp:
        return ""

    dt_utc_naive = datetime.fromisoformat(iso_timestamp)
    if dt_utc_naive.tzinfo is None:
        dt_utc_aware = dt_utc_naive.replace(tzinfo=timezone.utc)
    else:
        dt_utc_aware = dt_utc_naive.astimezone(timezone.utc)

    dt_local = dt_utc_aware.astimezone()
    return dt_local.strftime(fmt)


def format_time_ago(timestamp: str) -> str:
    """Converts an ISO format timestamp string to a human-readable relative time."""
    if not timestamp:
        return "no activity"

    last_time_naive = datetime.fromisoformat(timestamp)
    last_time = last_time_naive.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - last_time

    if diff.days > 0:
        return f"{diff.days}d ago"
    if diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    if diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    return "just now"


def format_channel_meta(channel) -> str:
    """Render message/member/note counts for a channel."""
    participant_count = len(channel.participants or [])
    parts = [
        f"{channel.message_count} msgs",
        f"{participant_count} members",
    ]
    notes = getattr(channel, "notes_count", 0) or 0
    if notes:
        parts.append(f"{notes} notes")
    return " | ".join(parts)


def format_channel_row(channel) -> tuple[str, str]:
    """Formats a channel object into a tuple of (last_activity_str, channel_info_str)."""
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"

    participant_count = len(channel.participants or [])
    parts = [f"{participant_count} members"]

    if channel.unread_count > 0:
        parts.insert(0, f"{channel.unread_count} new")

    notes = getattr(channel, "notes_count", 0) or 0
    if notes:
        parts.append(f"{notes} notes")

    meta_str = " | ".join(parts)
    return last_activity, f"{channel.name} - {meta_str}"
