"""Agent operations: CRUD, merging, caching."""

import time
import uuid
from datetime import datetime
from functools import lru_cache

from space.core import events
from space.core.models import Agent
from space.lib import db


def _row_to_agent(row: db.Row) -> Agent:
    from space.lib.db import from_row

    data = dict(row)
    data["archived_at"] = int(data["archived_at"]) if data["archived_at"] else None
    if "self_description" in data:
        data["description"] = data.pop("self_description")
    if "name" in data:
        data["identity"] = data.pop("name")
    return from_row(data, Agent)


@lru_cache(maxsize=256)
def _get_agent_by_name_cached(name: str) -> Agent | None:
    """Cached agent lookup by name."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id, identity, self_description, archived_at, created_at FROM agents WHERE identity = ? AND archived_at IS NULL LIMIT 1",
            (name,),
        ).fetchone()
        return _row_to_agent(row) if row else None


def _clear_cache():
    """Invalidate agent cache."""
    _get_agent_by_name_cached.cache_clear()


def resolve_agent(identifier: str) -> Agent | None:
    """Resolve agent by name or ID. Returns Agent object or None."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id, identity, self_description, archived_at, created_at FROM agents WHERE (identity = ? OR agent_id = ?) AND archived_at IS NULL LIMIT 1",
            (identifier, identifier),
        ).fetchone()
        return _row_to_agent(row) if row else None


def ensure_agent(name: str) -> str:
    """Get agent by name, restore if archived, create if missing. Returns agent_id."""
    agent = resolve_agent(name)
    if agent:
        return agent.agent_id

    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ? LIMIT 1", (name,)
        ).fetchone()
        agent_id = row["agent_id"] if row else None

    if agent_id:
        unarchive_agent(name)
        return agent_id

    agent_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()
    with db.ensure("spawn") as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, identity, created_at) VALUES (?, ?, ?)",
            (agent_id, name, now_iso),
        )
    _clear_cache()
    events.emit("spawn", "agent.create", agent_id, f"Agent '{name}' created")
    return agent_id


def describe_self(name: str, content: str) -> None:
    """Set self-description for agent."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ? LIMIT 1", (name,)
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE agents SET self_description = ? WHERE agent_id = ?",
                (content, row["agent_id"]),
            )
        else:
            agent_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO agents (agent_id, identity, self_description) VALUES (?, ?, ?)",
                (agent_id, name, content),
            )
    _clear_cache()


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Merges histories if new_name exists."""
    old_agent = resolve_agent(old_name)
    if not old_agent:
        return False
    old_agent_id = old_agent.agent_id

    with db.ensure("spawn") as conn:
        existing_agent = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ?", (new_name,)
        ).fetchone()
        if existing_agent:
            return False
        conn.execute("UPDATE agents SET identity = ? WHERE agent_id = ?", (new_name, old_agent_id))
    _clear_cache()
    return True


def archive_agent(name: str) -> bool:
    """Archive an agent. Returns True if archived, False if not found."""
    agent = resolve_agent(name)
    if not agent:
        return False
    agent_id = agent.agent_id

    with db.ensure("spawn") as conn:
        conn.execute(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?", (int(time.time()), agent_id)
        )
    _clear_cache()
    return True


def unarchive_agent(name: str) -> bool:
    """Unarchive an agent. Returns True if unarchived, False if not found."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ? LIMIT 1", (name,)
        ).fetchone()
        agent_id = row["agent_id"] if row else None

    if not agent_id:
        return False

    with db.ensure("spawn") as conn:
        conn.execute("UPDATE agents SET archived_at = NULL WHERE agent_id = ?", (agent_id,))
    _clear_cache()
    return True


def list_agents() -> list[str]:
    """List all active agents."""
    with db.ensure("spawn") as conn:
        rows = conn.execute(
            "SELECT identity FROM agents WHERE archived_at IS NULL ORDER BY identity"
        ).fetchall()
        return [row["identity"] for row in rows]


def merge_agents(from_name: str, to_name: str) -> bool:
    """Merge agent histories. Migrates all references from source to target."""
    from_agent = resolve_agent(from_name)
    to_agent = resolve_agent(to_name)

    if not from_agent or not to_agent:
        return False
    from_id = from_agent.agent_id
    to_id = to_agent.agent_id

    if from_id == to_id:
        return False

    from space.lib import paths

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

    _clear_cache()
    return True


__all__ = [
    "resolve_agent",
    "ensure_agent",
    "describe_self",
    "rename_agent",
    "archive_agent",
    "unarchive_agent",
    "list_agents",
    "merge_agents",
]
