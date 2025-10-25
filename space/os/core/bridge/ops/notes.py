"""Note operations: add, get, list."""

import sqlite3

from space.os import db
from space.os.db import from_row
from space.os.lib.uuid7 import uuid7
from space.os.models import Note


def _row_to_note(row: sqlite3.Row) -> Note:
    return from_row(row, Note)


def add_note(channel_id: str, identity: str, content: str) -> str:
    """Add note to channel. Returns note_id."""
    from space.os.core import spawn

    if not identity:
        raise ValueError("Identity is required")
    if not channel_id:
        raise ValueError("Channel ID is required")

    agent_id = spawn.db.ensure_agent(identity)
    note_id = uuid7()

    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO notes (note_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (note_id, channel_id, agent_id, content),
        )
    return note_id


def get_notes(channel_id: str) -> list[Note]:
    """Get all notes for channel ordered by creation."""
    with db.ensure("bridge") as conn:
        cursor = conn.execute(
            "SELECT note_id, channel_id, agent_id, content, created_at FROM notes WHERE channel_id = ? ORDER BY created_at ASC",
            (channel_id,),
        )
        return [_row_to_note(row) for row in cursor.fetchall()]
