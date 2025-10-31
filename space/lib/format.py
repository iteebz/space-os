from datetime import datetime, timedelta


def humanize_timestamp(timestamp_str: str) -> str:
    if not timestamp_str:
        return "never"
    try:
        timestamp = datetime.fromisoformat(str(timestamp_str))
    except (ValueError, TypeError):
        return str(timestamp_str) if timestamp_str else "never"

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
