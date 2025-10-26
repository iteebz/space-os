"""Note operations: add, get, list."""

from space.core.models import Channel, Note
from space.lib import db
from space.lib.db import from_row
from space.lib.uuid7 import uuid7


def _row_to_note(row: db.Row) -> Note:
    return from_row(row, Note)


def _to_channel_id(channel: str | Channel) -> str:
    """Extract channel_id from Channel object or return string as-is."""
    return channel.channel_id if isinstance(channel, Channel) else channel


def add_note(channel_id: str | Channel, identity: str, content: str) -> str:
    """Add note to channel. Returns note_id."""
    from space.core import spawn

    if not identity:
        raise ValueError("Identity is required")
    if not channel_id:
        raise ValueError("Channel ID is required")

    channel_id = _to_channel_id(channel_id)

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")
    agent_id = agent.agent_id
    note_id = uuid7()

    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO notes (note_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (note_id, channel_id, agent_id, content),
        )
    return note_id


def get_notes(channel_id: str | Channel) -> list[Note]:
    """Get all notes for channel ordered by creation."""
    channel_id = _to_channel_id(channel_id)
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT note_id, channel_id, agent_id, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [_row_to_note(row) for row in cursor.fetchall()]
