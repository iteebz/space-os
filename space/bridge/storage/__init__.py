"""Facade for the storage layer.

This module exposes the public functions from the various storage modules
as a single, unified interface for the business logic layer.
"""

from .alerts import get_alerts
from .bookmarks import set_bookmark
from .channels import (
    archive_channel,
    archive_topic,
    create_channel_record,
    create_topic_record,
    delete_channel,
    delete_topic,
    ensure_channel_exists,
    ensure_topic_exists,
    fetch_channels,
    get_channel_id,
    get_channel_name,
    get_context,
    get_export_data,
    get_participants,
    get_topic_id,
    rename_channel,
    rename_topic,
    set_context,
)
from .db import init_db
from .identities import active_hash, base_identity, get_senders, save_identity
from .instructions import get_topic_instructions, save_instructions
from .messages import create_message, get_all_messages, get_new_messages, get_sender_history
from .notes import create_note, get_notes

__all__ = [
    "init_db",
    "create_channel_record",
    "create_topic_record",
    "ensure_channel_exists",
    "ensure_topic_exists",
    "get_channel_id",
    "get_channel_name",
    "get_topic_id",
    "set_context",
    "get_context",
    "get_participants",
    "fetch_channels",
    "get_export_data",
    "archive_channel",
    "archive_topic",
    "delete_channel",
    "delete_topic",
    "rename_channel",
    "rename_topic",
    "create_message",
    "get_new_messages",
    "get_all_messages",
    "get_sender_history",
    "save_identity",
    "base_identity",
    "get_senders",
    "active_hash",
    "create_note",
    "get_notes",
    "save_instructions",
    "get_topic_instructions",
    "set_bookmark",
    "get_alerts",
]
