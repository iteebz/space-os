"""Session tracking: spawn lifecycle management."""

from datetime import datetime

from space.core import db
from space.lib.uuid7 import uuid7


def create_session(agent_id: str) -> str:
    """Create a new session for agent spawn.

    Returns session_id.
    """
    with db.connect() as conn:
        cursor = conn.cursor()

        session_id = uuid7()

        cursor.execute("SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        spawn_count = (result[0] if result else 0) + 1

        cursor.execute(
            """
            INSERT INTO sessions (session_id, agent_id, spawn_number, wakes)
            VALUES (?, ?, ?, 0)
            """,
            (session_id, agent_id, spawn_count),
        )

        cursor.execute(
            "UPDATE agents SET spawn_count = ?, last_active_at = ? WHERE agent_id = ?",
            (spawn_count, datetime.now().isoformat(), agent_id),
        )

        return session_id


def end_session(session_id: str) -> None:
    """End a session."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
            (datetime.now().isoformat(), session_id),
        )


def get_spawn_count(agent_id: str) -> int:
    """Get total spawn count for agent."""
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
