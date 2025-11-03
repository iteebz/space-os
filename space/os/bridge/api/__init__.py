"""Bridge operations: channels, messages, agent spawning.

Channel operations: create, list, archive, delete, rename, pin.
Message operations: send, recv, get all, get sender history.
Mention spawning: detect @identity in messages, spawn agents inline.
"""

from .channels import (
    archive_channel,
    create_channel,
    delete_channel,
    get_channel,
    list_channels,
    rename_channel,
    restore_channel,
    toggle_pin_channel,
)
from .mentions import spawn_from_mentions
from .messaging import (
    format_messages,
    get_messages,
    get_sender_history,
    recv_messages,
    send_message,
    wait_for_message,
)

__all__ = [
    "archive_channel",
    "create_channel",
    "delete_channel",
    "format_messages",
    "get_channel",
    "get_messages",
    "get_sender_history",
    "list_channels",
    "recv_messages",
    "rename_channel",
    "restore_channel",
    "send_message",
    "spawn_from_mentions",
    "toggle_pin_channel",
    "wait_for_message",
]
