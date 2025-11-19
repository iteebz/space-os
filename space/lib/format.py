from datetime import datetime, timedelta

MINUTE = 60
HOUR = 3600
DAY = 86400
WEEK = 604800
MONTH = 2592000
YEAR = 31536000


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
        minutes = int(diff.total_seconds() / MINUTE)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() / HOUR)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if diff < timedelta(weeks=1):
        days = int(diff.total_seconds() / DAY)
        return f"{days} day{'s' if days > 1 else ''} ago"
    if diff < timedelta(days=30):
        weeks = int(diff.total_seconds() / WEEK)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if diff < timedelta(days=365):
        months = int(diff.total_seconds() / MONTH)
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = int(diff.total_seconds() / YEAR)
    return f"{years} year{'s' if years > 1 else ''} ago"


def format_duration(seconds: float) -> str:
    if seconds < MINUTE:
        return f"{int(seconds)}s"
    if seconds < HOUR:
        return f"{int(seconds / MINUTE)}m"
    if seconds < DAY:
        hours = int(seconds / HOUR)
        mins = int((seconds % HOUR) / MINUTE)
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    days = int(seconds / DAY)
    hours = int((seconds % DAY) / HOUR)
    return f"{days}d {hours}h" if hours else f"{days}d"
