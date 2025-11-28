"""Spawn tracking: agent invocation lifecycle management."""

import logging
from collections.abc import Sequence
from datetime import datetime

from space.core.models import Spawn
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7

logger = logging.getLogger(__name__)

MAX_SPAWN_DEPTH = 3


def create_spawn(
    agent_id: str,
    constitution_hash: str | None = None,
    channel_id: str | None = None,
    session_id: str | None = None,
    parent_spawn_id: str | None = None,
) -> Spawn:
    """Create spawn and atomically increment agent.spawn_count."""
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
            (id, agent_id, constitution_hash, channel_id, session_id, parent_spawn_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spawn_id,
                agent_id,
                constitution_hash,
                channel_id,
                session_id,
                parent_spawn_id,
                now,
            ),
        )

        cursor.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE id = ?",
            (spawn_id,),
        )
        row = cursor.fetchone()
        return from_row(row, Spawn)


def update_status(spawn_id: str, status: str) -> None:
    """Update spawn status. Terminal states trigger session indexing."""
    now = datetime.now().isoformat()
    terminal_states = {"completed", "failed", "timeout", "killed"}

    with store.ensure() as conn:
        current = conn.execute("SELECT status FROM spawns WHERE id = ?", (spawn_id,)).fetchone()
        if current and current[0] == "killed":
            return

        if status in terminal_states:
            conn.execute(
                "UPDATE spawns SET status = ?, ended_at = ? WHERE id = ?",
                (status, now, spawn_id),
            )
        else:
            conn.execute(
                "UPDATE spawns SET status = ? WHERE id = ?",
                (status, spawn_id),
            )

    if status in terminal_states:
        _finalize_session(spawn_id)


def _finalize_session(spawn_id: str) -> None:
    spawn = get_spawn(spawn_id)
    if not spawn or not spawn.session_id:
        return

    try:
        from space.os.sessions.api import sync

        sync.ingest(spawn.session_id)
        sync.index(spawn.session_id)
    except Exception as e:
        logger.warning(f"Failed to finalize session {spawn.session_id} for spawn {spawn_id}: {e}")


def end_spawn(spawn_id: str) -> None:
    with store.ensure() as conn:
        conn.execute(
            "UPDATE spawns SET ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), spawn_id),
        )


def set_pid(spawn_id: str, pid: int) -> None:
    with store.ensure() as conn:
        conn.execute("UPDATE spawns SET pid = ? WHERE id = ?", (pid, spawn_id))


SPAWN_TIMEOUT_MINUTES = 10
STALL_THRESHOLD_MINUTES = 3


def cleanup_orphans() -> int:
    """Mark spawns with dead PIDs as failed. Returns count cleaned."""
    import os

    cleaned = 0
    with store.ensure() as conn:
        rows = conn.execute("SELECT id, pid FROM spawns WHERE status = 'running'").fetchall()

    for spawn_id, pid in rows:
        if pid is None:
            update_status(spawn_id, "failed")
            cleaned += 1
        else:
            try:
                os.kill(pid, 0)
            except OSError:
                update_status(spawn_id, "failed")
                cleaned += 1

    return cleaned


def detect_failures() -> dict[str, list[str]]:
    """Detect running spawns that are timed out or stalled. Returns {issue: [spawn_ids]}."""
    from datetime import datetime, timedelta

    now = datetime.now()
    timeout_cutoff = (now - timedelta(minutes=SPAWN_TIMEOUT_MINUTES)).isoformat()
    stall_cutoff = (now - timedelta(minutes=STALL_THRESHOLD_MINUTES)).isoformat()

    issues: dict[str, list[str]] = {"timeout": [], "stalled": [], "no_session": []}

    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT id, pid, session_id, created_at FROM spawns WHERE status = 'running'"
        ).fetchall()

    for spawn_id, _pid, session_id, created_at in rows:
        if created_at < timeout_cutoff:
            issues["timeout"].append(spawn_id)
        elif session_id is None and created_at < stall_cutoff:
            issues["no_session"].append(spawn_id)
        elif session_id and _session_stalled(session_id, stall_cutoff):
            issues["stalled"].append(spawn_id)

    return issues


def _session_stalled(session_id: str, cutoff: str) -> bool:
    """Check if session file hasn't been modified since cutoff."""
    from space.lib import paths

    for provider in ("claude", "gemini", "codex"):
        session_file = paths.sessions_dir() / provider / f"{session_id}.jsonl"
        if session_file.exists():
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime).isoformat()
            return mtime < cutoff
    return False


def link_session_to_spawn(spawn_id: str, session_id: str) -> None:
    with store.ensure() as conn:
        conn.execute(
            "UPDATE spawns SET session_id = ? WHERE id = ?",
            (session_id, spawn_id),
        )


def get_spawn_count(agent_id: str) -> int:
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT spawn_count FROM agents WHERE agent_id = ?", (agent_id,)
        ).fetchone()
        return row[0] if row else 0


def get_spawns_for_agent(
    agent_id: str,
    limit: int | None = None,
    status: str | Sequence[str] | None = None,
) -> list[Spawn]:
    with store.ensure() as conn:
        query = (
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at "
            "FROM spawns WHERE agent_id = ?"
        )
        params: list[object] = [agent_id]

        if status:
            statuses: list[str]
            if isinstance(status, str):
                statuses = status.split("|") if "|" in status else [status]
            else:
                statuses = list(status)

            placeholders = ", ".join(["?"] * len(statuses))
            query += f" AND status IN ({placeholders})"
            params.extend(statuses)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_spawn(spawn_id: str) -> Spawn | None:
    """Get spawn by full or partial ID. Prefers exact matches, then unique prefix."""
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE id = ?",
            (spawn_id,),
        ).fetchone()
        if row:
            return from_row(row, Spawn)

        matches = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE id LIKE ?",
            (f"{spawn_id}%",),
        ).fetchall()
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous spawn ID '{spawn_id}': {len(matches)} matches. Provide more characters."
            )
        if len(matches) == 1:
            return from_row(matches[0], Spawn)
        return None


def get_channel_spawns(
    channel_id: str,
    status: str | None = None,
    agent_id: str | None = None,
    limit: int | None = None,
) -> list[Spawn]:
    """Get spawns in channel, optionally filtered by status or agent."""
    with store.ensure() as conn:
        query = (
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at "
            "FROM spawns WHERE channel_id = ?"
        )
        params: list[object] = [channel_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_all_spawns(limit: int = 100) -> list[Spawn]:
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_spawn_depth(spawn_id: str) -> int:
    """Count spawn depth (0 = root, 1 = first child, etc.)."""
    return len(get_spawn_lineage(spawn_id)) - 1


def get_spawn_lineage(spawn_id: str) -> list[str]:
    """Return spawn lineage from child to root: [spawn_id, parent_id, grandparent_id, ...]."""
    lineage = [spawn_id]
    current_id = spawn_id

    with store.ensure() as conn:
        while current_id:
            row = conn.execute(
                "SELECT parent_spawn_id FROM spawns WHERE id = ?", (current_id,)
            ).fetchone()
            if not row or not row[0]:
                break
            current_id = row[0]
            lineage.append(current_id)
            if len(lineage) > MAX_SPAWN_DEPTH + 5:
                raise RuntimeError(f"Spawn lineage loop detected for {spawn_id}")

    return lineage


def get_spawn_children(spawn_id: str) -> list[Spawn]:
    """Get direct children of a spawn."""
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE parent_spawn_id = ? ORDER BY created_at ASC",
            (spawn_id,),
        ).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_all_root_spawns(limit: int = 100) -> list[Spawn]:
    """Get spawns with no parent (root spawns)."""
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE parent_spawn_id IS NULL ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [from_row(row, Spawn) for row in rows]


def get_root_spawns_for_agent(agent_id: str, limit: int = 100) -> list[Spawn]:
    """Get root spawns (no parent) for a specific agent. Efficient WHERE clause filtering."""
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT id, agent_id, parent_spawn_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at FROM spawns WHERE parent_spawn_id IS NULL AND agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (agent_id, limit),
        ).fetchall()
        return [from_row(row, Spawn) for row in rows]
