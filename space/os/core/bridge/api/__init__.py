"""Bridge operations: pure business logic, zero typer imports.

Functions handle all DB interactions and state management.
Callers: commands/ layer only.
"""

from .channels import (
    active_channels,
    all_channels,
    archive_channel,
    create_channel,
    delete_channel,
    get_channel_id,
    get_channel_name,
    get_participants,
    get_topic,
    inbox_channels,
    pin_channel,
    rename_channel,
    resolve_channel_id,
    unpin_channel,
)
from .export import get_export_data
from .messaging import (
    get_alerts,
    get_all_messages,
    get_new_messages,
    get_sender_history,
    recv_updates,
    send_message,
    set_bookmark,
)
from .notes import add_note, get_notes
from .spawning import spawn_agents_from_mentions

__all__ = [
    "active_channels",
    "add_note",
    "all_channels",
    "archive_channel",
    "create_channel",
    "delete_channel",
    "get_alerts",
    "get_all_messages",
    "get_channel_id",
    "get_channel_name",
    "get_export_data",
    "get_new_messages",
    "get_notes",
    "get_participants",
    "get_sender_history",
    "get_topic",
    "inbox_channels",
    "pin_channel",
    "recv_updates",
    "rename_channel",
    "resolve_channel_id",
    "send_message",
    "set_bookmark",
    "spawn_agents_from_mentions",
    "unpin_channel",
]
