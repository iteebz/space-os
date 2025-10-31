"""Bridge operations: pure business logic, zero typer imports.

Functions handle all DB interactions and state management.
Callers: commands/ layer only.
"""

from .channels import (
    archive_channel,
    create_channel,
    delete_channel,
    export_channel,
    fetch_inbox,
    get_channel,
    list_channels,
    rename_channel,
    resolve_channel,
    toggle_pin_channel,
)
from .mentions import spawn_from_mentions
from .messaging import (
    get_messages,
    get_sender_history,
    recv_messages,
    send_message,
    set_bookmark,
    wait_for_message,
)

__all__ = [
    "archive_channel",
    "create_channel",
    "delete_channel",
    "export_channel",
    "get_channel",
    "get_messages",
    "get_sender_history",
    "fetch_inbox",
    "list_channels",
    "recv_messages",
    "rename_channel",
    "resolve_channel",
    "send_message",
    "set_bookmark",
    "spawn_from_mentions",
    "toggle_pin_channel",
    "wait_for_message",
]
