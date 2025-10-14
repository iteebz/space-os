from datetime import datetime, timedelta


def humanize_timestamp(timestamp_str: str) -> str:
    """
    Converts an ISO format timestamp string to a human-readable "X time ago" format.
    """
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        return timestamp_str  # Return original if parsing fails

    now = datetime.now()
    diff = now - timestamp

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(weeks=1):
        days = int(diff.total_seconds() / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < timedelta(days=30):  # Approximately a month
        weeks = int(diff.total_seconds() / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff < timedelta(days=365):  # Approximately a year
        months = int(diff.total_seconds() / 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(diff.total_seconds() / 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"
