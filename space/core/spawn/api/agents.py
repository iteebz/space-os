"""Agent operations: CRUD, merging, caching."""

import time
import uuid
from datetime import datetime
from functools import lru_cache

from space.core import events
from space.core.models import Agent
from space.lib import store
from space.lib.store import from_row


def _row_to_agent(row: store.Row) -> Agent:
    data = dict(row)
    data["archived_at"] = int(data.get("archived_at", 0)) if data.get("archived_at") else None
    if "self_description" in data:
        data["description"] = data.pop("self_description")
    return from_row(data, Agent)


@lru_cache(maxsize=256)
def _get_agent_by_name_cached(name: str) -> Agent | None:
    """Cached agent lookup by name."""
    with store.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id, identity, constitution, base_agent, self_description, archived_at, created_at FROM agents WHERE identity = ? AND archived_at IS NULL LIMIT 1",
            (name,),
        ).fetchone()
        return _row_to_agent(row) if row else None


def _clear_cache():
    """Invalidate agent cache."""
    _get_agent_by_name_cached.cache_clear()


def get_agent(identifier: str) -> Agent | None:
    """Resolve agent by name or ID. Returns Agent object or None."""
    with store.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id, identity, constitution, base_agent, self_description, archived_at, created_at FROM agents WHERE (identity = ? OR agent_id = ?) AND archived_at IS NULL LIMIT 1",
            (identifier, identifier),
        ).fetchone()
        return _row_to_agent(row) if row else None


def register_agent(identity: str, constitution: str, base_agent: str) -> str:
    """Explicitly register an identity. Fails if identity already exists."""
    agent = get_agent(identity)
    if agent:
        raise ValueError(f"Identity '{identity}' already registered")

    agent_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()
    with store.ensure("spawn") as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, identity, constitution, base_agent, created_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, identity, constitution, base_agent, now_iso),
        )
    _clear_cache()
    events.emit("spawn", "agent.register", agent_id, f"Identity '{identity}' registered")
    return agent_id


def ensure_agent(name: str) -> str:
    """DEPRECATED: Use register_agent or get_agent."""
    raise NotImplementedError(
        "ensure_agent is deprecated. All agents must be explicitly registered via `space init` or `spawn register`."
    )


def describe_self(name: str, content: str) -> None:
    """Set self-description for agent."""
    agent = get_agent(name)
    if not agent:
        raise ValueError(f"Agent '{name}' not found.")

    with store.ensure("spawn") as conn:
        conn.execute(
            "UPDATE agents SET self_description = ? WHERE agent_id = ?",
            (content, agent.agent_id),
        )
    _clear_cache()


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Fails if new_name exists."""
    old_agent = get_agent(old_name)
    if not old_agent:
        return False

    new_agent = get_agent(new_name)
    if new_agent:
        return False

    with store.ensure("spawn") as conn:
        conn.execute(
            "UPDATE agents SET identity = ? WHERE agent_id = ?", (new_name, old_agent.agent_id)
        )
    _clear_cache()
    return True


def archive_agent(name: str) -> bool:
    """Archive an agent. Returns True if archived, False if not found."""
    agent = get_agent(name)
    if not agent:
        return False
    agent_id = agent.agent_id

    with store.ensure("spawn") as conn:
        conn.execute(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?", (int(time.time()), agent_id)
        )
    _clear_cache()
    return True


def unarchive_agent(name: str) -> bool:
    """Unarchive an agent. Returns True if unarchived, False if not found."""
    with store.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ? LIMIT 1", (name,)
        ).fetchone()
        agent_id = row["agent_id"] if row else None

    if not agent_id:
        return False

    with store.ensure("spawn") as conn:
        conn.execute("UPDATE agents SET archived_at = NULL WHERE agent_id = ?", (agent_id,))
    _clear_cache()
    return True


def list_agents() -> list[str]:
    """List all active agents."""
    with store.ensure("spawn") as conn:
        rows = conn.execute(
            "SELECT identity FROM agents WHERE archived_at IS NULL ORDER BY identity"
        ).fetchall()
        return [row["identity"] for row in rows]


def merge_agents(from_name: str, to_name: str) -> bool:
    """Merge agent histories. Migrates all references from source to target."""
    from_agent = get_agent(from_name)
    to_agent = get_agent(to_name)

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
        with store.ensure("events") as conn:
            conn.execute("UPDATE events SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if memory_db.exists():
        with store.ensure("memory") as conn:
            conn.execute("UPDATE memories SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if knowledge_db.exists():
        with store.ensure("knowledge") as conn:
            conn.execute("UPDATE knowledge SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    if bridge_db.exists():
        with store.ensure("bridge") as conn:
            conn.execute("UPDATE messages SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))

    with store.ensure("spawn") as conn:
        conn.execute("DELETE FROM agents WHERE agent_id = ?", (from_id,))

    _clear_cache()
    return True


__all__ = [
    "get_agent",
    "register_agent",
    "ensure_agent",
    "describe_self",
    "rename_agent",
    "archive_agent",
    "unarchive_agent",
    "list_agents",
    "merge_agents",
]
