"""
Business logic layer for the Bridge CLI.

This facade exposes the public functions from the domain-specific modules
in the 'coordination' package.
"""

from .channels import (
    active_channels,
    all_channels,
    archive_channel,
    create_channel,
    delete_channel,
    export_channel,
    get_channel_context,
    rename_channel,
    resolve_channel_id,
)
from .identities import load_identity, verify_sender
from .instructions import (
    channel_instructions,
    check_instructions,
    get_instructions,
    hash_instructions,
)
from .alerts import get_alerts
from .messages import (
    fetch_messages,
    fetch_sender_history,
    is_context,
    parse_context,
    recv_updates,
    send_message,
)
from .notes import add_note, get_notes

__all__ = [
    "load_identity",
    "verify_sender",
    "check_instructions",
    "get_instructions",
    "hash_instructions",
    "channel_instructions",
    "fetch_messages",
    "fetch_sender_history",
    "is_context",
    "parse_context",
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
    "get_channel_context",
    "rename_channel",
    "resolve_channel_id",
]
