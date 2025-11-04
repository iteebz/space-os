"""Spawn tracking: agent invocation lifecycle management."""

from datetime import datetime

from space.core.models import Spawn
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def create_spawn(
    agent_id: str,
    is_task: bool = False,
    constitution_hash: str | None = None,
    channel_id: str | None = None,
    session_id: str | None = None,
) -> Spawn:
    """Create a new spawn for agent invocation.

    Atomically increments agent.spawn_count.

    Args:
        agent_id: Agent ID
        is_task: Whether this is a background task spawn (headless)
        constitution_hash: Hash of the constitution file (if loaded)
        channel_id: Channel ID if triggered by bridge
        session_id: Session ID if already linked to provider session. Can be set later.

    Returns:
        Spawn object
    """
    spawn_id = uuid7()
    now = datetime.now().isoformat()

    with store.ensure() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE agents SET spawn_count = spawn_count + 1, last_active_at = ? WHERE agent_id = ?",
            (now, agent_id),
        )

        cursor.execute(
            """
            INSERT INTO spawns
            (id, agent_id, is_task, constitution_hash, channel_id, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (spawn_id, agent_id, is_task, constitution_hash, channel_id, session_id, now),
        )

        cursor.execute("SELECT * FROM spawns WHERE id = ?", (spawn_id,))
        row = cursor.fetchone()
        return from_row(row, Spawn)


def end_spawn(spawn_id: str) -> None:
    """End a spawn."""
    with store.ensure() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE spawns SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), spawn_id),
        )


def link_session_to_spawn(spawn_id: str, session_id: str) -> None:
    """Link a spawn to a provider session (for interactive spawns discovered later)."""
    with store.ensure() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE spawns SET session_id = ? WHERE id = ?",
            (session_id, spawn_id),
        )


def get_spawn_count(agent_id: str) -> int:
    """Get total spawn count for agent."""
    with store.ensure() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,))
        result = cursor.fetchone()
        return result[0] if result else 0


def get_spawns_for_agent(agent_id: str, limit: int | None = None) -> list[Spawn]:
    """Get all spawns for an agent, ordered by most recent first.

    Args:
        agent_id: Agent ID
        limit: Maximum number of spawns to return (None for all)

    Returns:
        List of Spawn objects
    """
    with store.ensure() as conn:
        query = """
            SELECT * FROM spawns
            WHERE agent_id = ?
            ORDER BY created_at DESC
        """
        params = (agent_id,)

        if limit:
            query += " LIMIT ?"
            params = (agent_id, limit)

        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_spawn(spawn_id: str) -> Spawn | None:
    """Get a single spawn by ID (supports partial ID match).

    Args:
        spawn_id: Spawn ID or partial ID (will be matched with LIKE)

    Returns:
        Spawn object or None if not found
    """
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT * FROM spawns WHERE id = ? OR id LIKE ? LIMIT 1",
            (spawn_id, f"{spawn_id}%"),
        ).fetchone()
        return from_row(row, Spawn) if row else None
