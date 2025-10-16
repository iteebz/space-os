from datetime import datetime, timedelta


def humanize_timestamp(timestamp_str: str) -> str:
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        return timestamp_str

    now = datetime.now()
    diff = now - timestamp

    if diff < timedelta(minutes=1):
        return "just now"
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if diff < timedelta(weeks=1):
        days = int(diff.total_seconds() / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    if diff < timedelta(days=30):
        weeks = int(diff.total_seconds() / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if diff < timedelta(days=365):
        months = int(diff.total_seconds() / 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = int(diff.total_seconds() / 31536000)
    return f"{years} year{'s' if years > 1 else ''} ago"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    days = int(seconds / 86400)
    hours = int((seconds % 86400) / 3600)
    return f"{days}d {hours}h" if hours else f"{days}d"


def format_memory_entries(entries: list, raw_output: bool = False) -> str:
    output_lines = []
    current_topic = None
    for e in entries:
        if e.topic != current_topic:
            if current_topic is not None:
                output_lines.append("")
            output_lines.append(f"# {e.topic}")
            current_topic = e.topic
        core_mark = " ★" if e.core else ""
        timestamp_display = e.timestamp if raw_output else humanize_timestamp(e.timestamp)
        output_lines.append(f"[{e.memory_id[-8:]}] [{timestamp_display}] {e.message}{core_mark}")
    return "\n".join(output_lines)
