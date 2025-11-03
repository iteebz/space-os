"""Session tracking: spawn lifecycle management."""

from datetime import datetime

from space.core import db
from space.core.models import Session
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def create_session(
    agent_id: str,
    is_task: bool = False,
    constitution_hash: str | None = None,
    channel_id: str | None = None,
) -> Session:
    """Create a new session for agent spawn.

    Args:
        agent_id: Agent ID
        is_task: Whether this is a background task spawn
        constitution_hash: Hash of the constitution file (if loaded)
        channel_id: Channel ID if triggered by bridge

    Returns:
        Session object
    """
    with db.connect() as conn:
        cursor = conn.cursor()

        session_id = uuid7()

        cursor.execute("SELECT spawns FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        spawn_count = (result[0] if result else 0) + 1

        cursor.execute(
            """
            INSERT INTO sessions
            (id, agent_id, spawn_number, is_task, constitution_hash, channel_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, agent_id, spawn_count, is_task, constitution_hash, channel_id),
        )

        cursor.execute(
            "UPDATE agents SET spawns = ?, last_active_at = ? WHERE agent_id = ?",
            (spawn_count, datetime.now().isoformat(), agent_id),
        )

        cursor.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        return from_row(row, Session)


def end_session(session_id: str) -> None:
    """End a session."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), session_id),
        )


def get_spawn_count(agent_id: str) -> int:
    """Get total spawn count for agent."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT spawns FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
