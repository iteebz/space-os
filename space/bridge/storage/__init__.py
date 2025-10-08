"""Facade for the storage layer.

This module exposes the public functions from the various storage modules
as a single, unified interface for the business logic layer.
"""

from .alerts import get_alerts
from .bookmarks import set_bookmark
from .channels import (
    archive_channel,
    create_channel_record,
    delete_channel,
    ensure_channel_exists,
    fetch_channels,
    get_channel_id,
    get_channel_name,
    get_context,
    get_export_data,
    get_participants,
    rename_channel,
    set_context,
)
from .db import init_db
from .messages import create_message, get_all_messages, get_new_messages, get_sender_history
from .notes import create_note, get_notes

__all__ = [
    "init_db",
    "create_channel_record",
    "ensure_channel_exists",
    "get_channel_id",
    "get_channel_name",
    "set_context",
    "get_context",
    "get_participants",
    "fetch_channels",
    "get_export_data",
    "archive_channel",
    "delete_channel",
    "rename_channel",
    "create_message",
    "get_new_messages",
    "get_all_messages",
    "get_sender_history",
    "create_note",
    "get_notes",
    "set_bookmark",
    "get_alerts",
]
