"""Agent operations: CRUD, merging, caching."""

import time
import uuid
from datetime import datetime
from functools import lru_cache

from space.os import events
from space.os.lib import db, paths
from space.os.lib.db import query_builders as qb


def schema() -> str:
    """Agent schema definition."""
    return """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_agent_ids(name: str, include_archived: bool = False) -> list[str]:
    """Get all agent UUIDs matching name."""
    with db.ensure("spawn") as conn:
        return qb.agent_by_name(conn, name, include_archived=include_archived)


def get_agent_id(name: str) -> str | None:
    """Get first active agent UUID by name."""
    ids = get_agent_ids(name, include_archived=False)
    return ids[0] if ids else None


@lru_cache(maxsize=256)
def get_agent_name(agent_id: str) -> str | None:
    """Get agent name by UUID."""
    with db.ensure("spawn") as conn:
        return qb.agent_by_id(conn, agent_id)


def clear_cache():
    """Invalidate agent name cache."""
    get_agent_name.cache_clear()


def ensure_agent(name: str) -> str:
    """Get or create agent, return UUID."""
    active_agent_id = get_agent_id(name)
    if active_agent_id:
        return active_agent_id

    archived_agent_ids = get_agent_ids(name, include_archived=True)
    if archived_agent_ids:
        agent_id = archived_agent_ids[0]
        restore_agent(name)
        return agent_id

    agent_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()
    with db.ensure("spawn") as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
            (agent_id, name, now_iso),
        )
    clear_cache()
    events.emit("spawn", "agent.create", agent_id, f"Agent '{name}' created")
    return agent_id


def get_self_description(agent_name: str) -> str | None:
    """Get self-description for agent."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT self_description FROM agents WHERE name = ? LIMIT 1",
            (agent_name,),
        ).fetchone()
        return row["self_description"] if row else None


def set_self_description(agent_name: str, description: str) -> bool:
    """Set self-description for agent. Returns True when an update occurs."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE name = ? LIMIT 1", (agent_name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE agents SET self_description = ? WHERE agent_id = ?",
                (description, row["agent_id"]),
            )
        else:
            agent_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO agents (agent_id, name, self_description) VALUES (?, ?, ?)",
                (agent_id, agent_name, description),
            )
    return True


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Merges histories if new_name exists."""
    old_agent_id = _resolve_agent(old_name)
    if not old_agent_id:
        return False

    with db.ensure("spawn") as conn:
        existing_agent = conn.execute(
            "SELECT agent_id FROM agents WHERE name = ?", (new_name,)
        ).fetchone()
        if existing_agent:
            return False
        conn.execute("UPDATE agents SET name = ? WHERE agent_id = ?", (new_name, old_agent_id))
    clear_cache()
    return True


def archive_agent(name: str) -> bool:
    """Archive an agent. Returns True if archived, False if not found."""
    agent_id = get_agent_id(name)
    if not agent_id:
        return False

    with db.ensure("spawn") as conn:
        conn.execute(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?", (int(time.time()), agent_id)
        )
    clear_cache()
    return True


def restore_agent(name: str) -> bool:
    """Restore an archived agent. Returns True if restored, False if not found."""
    agent_ids = get_agent_ids(name, include_archived=True)
    if not agent_ids:
        return False

    agent_id = agent_ids[0]
    with db.ensure("spawn") as conn:
        conn.execute("UPDATE agents SET archived_at = NULL WHERE agent_id = ?", (agent_id,))
    clear_cache()
    return True


def list_all_agents() -> list[str]:
    """List all active agents."""
    with db.ensure("spawn") as conn:
        rows = conn.execute(
            "SELECT name FROM agents WHERE archived_at IS NULL ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]


def _resolve_agent(identifier: str) -> str | None:
    """Resolve name or UUID to UUID."""
    if len(identifier) == 36 and identifier.count("-") == 4:
        with db.ensure("spawn") as conn:
            row = conn.execute(
                "SELECT agent_id FROM agents WHERE agent_id = ?", (identifier,)
            ).fetchone()
            return row["agent_id"] if row else None
    else:
        ids = get_agent_ids(identifier, include_archived=True)
        if len(ids) > 1:
            return None
        return ids[0] if ids else None


def merge_agents(from_identifier: str, to_identifier: str) -> bool:
    """Merge agent histories. Migrates all references from source to target."""
    from_id = _resolve_agent(from_identifier)
    to_id = _resolve_agent(to_identifier)

    if not from_id or not to_id or from_id == to_id:
        return False

    events_db = paths.space_data() / "events.db"
    memory_db = paths.space_data() / "memory.db"
    knowledge_db = paths.space_data() / "knowledge.db"
    bridge_db = paths.space_data() / "bridge.db"

    if events_db.exists():
        with db.ensure("events") as conn:
            conn.execute("UPDATE events SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if memory_db.exists():
        with db.ensure("memory") as conn:
            conn.execute("UPDATE memories SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if knowledge_db.exists():
        with db.ensure("knowledge") as conn:
            conn.execute("UPDATE knowledge SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if bridge_db.exists():
        with db.ensure("bridge") as conn:
            conn.execute("UPDATE messages SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    with db.ensure("spawn") as conn:
        conn.execute("DELETE FROM agents WHERE agent_id = ?", (from_id,))

    clear_cache()
    return True


__all__ = [
    "get_agent_ids",
    "get_agent_id",
    "get_agent_name",
    "clear_cache",
    "ensure_agent",
    "get_self_description",
    "set_self_description",
    "rename_agent",
    "archive_agent",
    "restore_agent",
    "list_all_agents",
    "merge_agents",
    "schema",
]
