"""Session tracking: spawn lifecycle management."""

from datetime import datetime

from space.lib.uuid7 import uuid7
from space.os.spawn import db


def create_session(agent_id: str) -> str:
    """Create a new session for agent spawn.

    Returns session_id.
    """
    conn = db.connect()
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
        "UPDATE agents SET spawn_count = ?, wakes_this_spawn = 0, last_active_at = ? WHERE agent_id = ?",
        (spawn_count, datetime.now().isoformat(), agent_id),
    )

    conn.commit()
    return session_id


def end_session(session_id: str) -> None:
    """End a session."""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
        (datetime.now().isoformat(), session_id),
    )
    conn.commit()


def increment_wakes(agent_id: str) -> int:
    """Increment wakes for current session. Returns new count."""
    conn = db.connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT wakes_this_spawn FROM agents WHERE agent_id = ?",
        (agent_id,),
    )
    result = cursor.fetchone()
    current = result[0] if result else 0
    new_count = current + 1

    cursor.execute(
        "UPDATE agents SET wakes_this_spawn = ? WHERE agent_id = ?",
        (new_count, agent_id),
    )
    conn.commit()
    return new_count


def get_spawn_count(agent_id: str) -> int:
    """Get total spawn count for agent."""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def get_wakes_this_spawn(agent_id: str) -> int:
    """Get wakes count for current spawn session."""
    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT wakes_this_spawn FROM agents WHERE agent_id = ?", (agent_id,))
    result = cursor.fetchone()
    return result[0] if result else 0
