"""Bridge operations: channels, messages, agent spawning.

Channel operations: create, list, archive, delete, rename, pin.
Message operations: send, recv, get all, get sender history.
Mention spawning: detect @identity in messages, spawn agents inline.
"""

from .channels import (
    archive_channel,
    count_channels,
    create_channel,
    delete_channel,
    get_channel,
    list_channels,
    rename_channel,
    restore_channel,
    toggle_pin_channel,
)
from .delimiters import process_delimiters
from .messaging import (
    count_messages,
    delete_message,
    format_messages,
    get_messages,
    get_messages_before,
    get_sender_history,
    recv_messages,
    send_message,
    wait_for_message,
)
from .operations import search

__all__ = [
    "archive_channel",
    "count_channels",
    "count_messages",
    "create_channel",
    "delete_channel",
    "delete_message",
    "format_messages",
    "get_channel",
    "get_messages",
    "get_messages_before",
    "get_sender_history",
    "list_channels",
    "recv_messages",
    "rename_channel",
    "restore_channel",
    "search",
    "send_message",
    "process_delimiters",
    "toggle_pin_channel",
    "wait_for_message",
]
