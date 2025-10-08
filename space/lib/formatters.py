from datetime import datetime
from typing import Any

from ..bridge import utils as bridge_utils


def format_channel_row(channel: Any) -> tuple[str, str]:
    """
    Formats a channel object into a tuple of (last_activity_str, channel_info_str).
    """
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"
    meta_str = bridge_utils.format_channel_meta(channel)
    return last_activity, f"{channel.name} - {meta_str}"
