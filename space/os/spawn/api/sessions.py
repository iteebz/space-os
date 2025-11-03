"""Session tracking: spawn lifecycle management."""

from datetime import datetime

from space.core.models import Session
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def create_session(
    agent_id: str,
    is_task: bool = False,
    constitution_hash: str | None = None,
    channel_id: str | None = None,
) -> Session:
    """Create a new session for agent spawn.

    Atomically increments agent.spawn_count.

    Args:
        agent_id: Agent ID
        is_task: Whether this is a background task spawn
        constitution_hash: Hash of the constitution file (if loaded)
        channel_id: Channel ID if triggered by bridge

    Returns:
        Session object
    """
    session_id = uuid7()
    now = datetime.now().isoformat()

    with store.ensure() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE agents SET spawn_count = spawn_count + 1, last_active_at = ? WHERE agent_id = ?",
            (now, agent_id),
        )

        cursor.execute(
            """
            INSERT INTO sessions
            (id, agent_id, is_task, constitution_hash, channel_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, agent_id, is_task, constitution_hash, channel_id, now),
        )

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return from_row(row, Session)


def end_session(session_id: str) -> None:
    """End a session."""
    with store.ensure() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), session_id),
        )


def get_spawn_count(agent_id: str) -> int:
    """Get total spawn count for agent."""
    with store.ensure() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        return result[0] if result else 0


def get_sessions_for_agent(agent_id: str, limit: int | None = None) -> list[Session]:
    """Get all sessions for an agent, ordered by most recent first.

    Args:
        agent_id: Agent ID
        limit: Maximum number of sessions to return (None for all)

    Returns:
        List of Session objects
    """
    with store.ensure() as conn:
        query = """
            SELECT * FROM sessions
            WHERE agent_id = ?
            ORDER BY created_at DESC
        """
        params = (agent_id,)

        if limit:
            query += " LIMIT ?"
            params = (agent_id, limit)

        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Session) for row in rows]


def get_session(session_id: str) -> Session | None:
    """Get a single session by ID (supports partial ID match).

    Args:
        session_id: Session ID or partial ID (will be matched with LIKE)

    Returns:
        Session object or None if not found
    """
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ? OR id LIKE ? LIMIT 1",
            (session_id, f"{session_id}%"),
        ).fetchone()
        return from_row(row, Session) if row else None
