"""
Business logic layer for the Bridge CLI.

This facade exposes the public functions from the domain-specific modules
in the 'api' package.
"""

from .alerts import get_alerts
from .channels import (
    active_channels,
    all_channels,
    archive_channel,
    create_channel,
    delete_channel,
    export_channel,
    get_channel_topic,
    rename_channel,
    resolve_channel_id,
)
from .messages import (
    fetch_messages,
    fetch_sender_history,
    recv_updates,
    send_message,
)
from .notes import add_note, get_notes

__all__ = [
    "fetch_messages",
    "fetch_sender_history",
    "recv_updates",
    "send_message",
    "add_note",
    "get_notes",
    "get_alerts",
    "active_channels",
    "all_channels",
    "archive_channel",
    "create_channel",
    "delete_channel",
    "export_channel",
    "get_channel_topic",
    "rename_channel",
    "resolve_channel_id",
]
