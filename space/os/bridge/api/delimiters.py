"""Bridge delimiter parsing: @spawn, !agent-signals, /human-control."""

import logging

from .control import process_control_commands
from .mentions import process_mentions
from .signals import process_signals

log = logging.getLogger(__name__)


async def process_delimiters(channel_id: str, content: str, agent_id: str | None = None) -> None:
    """Fire-and-forget: parse @mentions and !control commands."""
    from . import channels

    channel = channels.get_channel(channel_id)
    if not channel:
        log.error(f"Channel {channel_id} not found")
        return

    try:
        process_control_commands(channel_id, content, agent_id)
        process_signals(channel_id, content, agent_id)
        process_mentions(channel_id, content, agent_id)
    except Exception as e:
        log.error(f"Failed to process delimiters: {e}", exc_info=True)
