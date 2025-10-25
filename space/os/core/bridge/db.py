"""Bridge database operations re-exports.

Provides a unified interface to bridge operations from ops/ modules.
"""

from pathlib import Path

from space.os import db as _db
from space.os.lib import paths
from space.os.lib.uuid7 import uuid7

from .. import bridge as _bridge
from .ops.channels import (
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
from .ops.export import get_export_data
from .ops.messaging import (
    get_alerts,
    get_all_messages,
    get_new_messages,
    get_sender_history,
    recv_updates,
    send_message,
    set_bookmark,
)
from .ops.notes import add_note, get_notes
from .ops.polls import create_poll, dismiss_poll, get_active_polls, is_polling


def path() -> Path:
    return paths.space_data() / "bridge.db"


def schema():
    """Return bridge database schema."""
    return _bridge.SCHEMA


def fetch_messages(channel_id: str):
    return get_all_messages(channel_id)


def fetch_agent_history(agent_name: str, limit: int = 5):
    from space.os.core import spawn

    agent_id = spawn.db.get_agent_id(agent_name)
    if not agent_id:
        return []
    return get_sender_history(agent_id, limit)


def connect():
    """Get database connection for bridge."""
    return _db.ensure("bridge").__enter__()


def create_message(channel_id: str, identity: str, content: str, priority: str = "normal") -> str:
    """Create message directly without spawning agent. Returns message_id."""
    message_id = uuid7()
    with _db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content, priority) VALUES (?, ?, ?, ?, ?)",
            (message_id, channel_id, identity, content, priority),
        )
    return message_id


get_channel_topic = get_topic

__all__ = [
    "active_channels",
    "all_channels",
    "archive_channel",
    "create_channel",
    "delete_channel",
    "get_channel_id",
    "get_channel_name",
    "get_participants",
    "get_topic",
    "inbox_channels",
    "pin_channel",
    "rename_channel",
    "resolve_channel_id",
    "unpin_channel",
    "get_export_data",
    "get_alerts",
    "get_all_messages",
    "get_new_messages",
    "get_sender_history",
    "recv_updates",
    "send_message",
    "set_bookmark",
    "get_notes",
    "add_note",
    "create_poll",
    "dismiss_poll",
    "get_active_polls",
    "is_polling",
    "fetch_messages",
    "fetch_agent_history",
    "get_channel_topic",
    "schema",
    "connect",
    "create_message",
    "path",
]
