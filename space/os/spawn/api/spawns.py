"""Spawn tracking: agent invocation lifecycle management."""

from datetime import datetime

from space.core.models import Spawn, SpawnStatus
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def create_spawn(
    agent_id: str,
    is_ephemeral: bool = False,
    constitution_hash: str | None = None,
    channel_id: str | None = None,
    session_id: str | None = None,
) -> Spawn:
    """Create a new spawn for agent invocation.

    Atomically increments agent.spawn_count.

    Args:
        agent_id: Agent ID
        is_ephemeral: Whether this was invoked directly (CLI, mention, or direct call), not persistent interactive session
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
            (id, agent_id, is_ephemeral, constitution_hash, channel_id, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (spawn_id, agent_id, is_ephemeral, constitution_hash, channel_id, session_id, now),
        )

        cursor.execute("SELECT * FROM spawns WHERE id = ?", (spawn_id,))
        row = cursor.fetchone()
        return from_row(row, Spawn)


def update_status(spawn_id: str, status: str) -> None:
    """Update spawn status and finalize session on terminal state.

    For terminal states (completed/failed/timeout/killed), indexes the linked session
    to populate transcripts table for context search (ingest already happened during streaming).
    """
    now = datetime.now().isoformat()
    terminal_states = ("completed", "failed", "timeout", "killed")

    with store.ensure() as conn:
        cursor = conn.cursor()
        if status in terminal_states:
            cursor.execute(
                "UPDATE spawns SET status = ?, ended_at = ? WHERE id = ?",
                (status, now, spawn_id),
            )
            conn.commit()

            # Index session for context search (ingest happened during streaming)
            spawn = get_spawn(spawn_id)
            if spawn and spawn.session_id:
                try:
                    from space.os.sessions.api import sync

                    sync.index(spawn.session_id)
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        f"Failed to index session {spawn.session_id} for spawn {spawn_id}: {e}"
                    )
        else:
            cursor.execute(
                "UPDATE spawns SET status = ? WHERE id = ?",
                (status, spawn_id),
            )
            conn.commit()


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


def get_spawns_for_agent(
    agent_id: str, limit: int | None = None, status: str | None = None
) -> list[Spawn]:
    with store.ensure() as conn:
        query = "SELECT * FROM spawns WHERE agent_id = ?"
        params = [agent_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

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


def pause_spawn(spawn_id: str) -> Spawn:
    """Pause a running spawn for mid-task steering.

    Args:
        spawn_id: Spawn ID to pause

    Returns:
        Updated Spawn object

    Raises:
        ValueError: If spawn not found or not in running state
    """
    spawn = get_spawn(spawn_id)
    if not spawn:
        raise ValueError(f"Spawn {spawn_id} not found")
    if spawn.status != SpawnStatus.RUNNING:
        raise ValueError(f"Cannot pause: spawn status is {spawn.status}, not running")

    update_status(spawn_id, SpawnStatus.PAUSED)
    return get_spawn(spawn_id)


def resume_spawn(spawn_id: str) -> Spawn:
    """Resume a paused spawn, reusing session context.

    Args:
        spawn_id: Spawn ID to resume

    Returns:
        Updated Spawn object

    Raises:
        ValueError: If spawn not found, not paused, or has no session_id
    """
    spawn = get_spawn(spawn_id)
    if not spawn:
        raise ValueError(f"Spawn {spawn_id} not found")
    if spawn.status != SpawnStatus.PAUSED:
        raise ValueError(f"Cannot resume: spawn status is {spawn.status}, not paused")
    if not spawn.session_id:
        raise ValueError("Cannot resume: spawn has no session_id")

    update_status(spawn_id, SpawnStatus.RUNNING)
    return get_spawn(spawn_id)


def get_channel_spawns(channel_id: str, status: str | None = None) -> list[Spawn]:
    """Get all spawns in a channel, optionally filtered by status.

    Args:
        channel_id: Channel ID to filter by
        status: Optional status filter (e.g., 'running', 'paused'). If None, returns all.

    Returns:
        List of Spawn objects in the channel
    """
    with store.ensure() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM spawns WHERE channel_id = ? AND status = ? ORDER BY created_at DESC",
                (channel_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM spawns WHERE channel_id = ? ORDER BY created_at DESC", (channel_id,)
            ).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_all_spawns(limit: int = 100) -> list[Spawn]:
    """Get all spawns across all agents."""
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT * FROM spawns ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [from_row(row, Spawn) for row in rows]
