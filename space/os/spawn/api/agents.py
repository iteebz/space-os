"""Agent operations: CRUD, merging, caching."""

import hashlib
from datetime import datetime

from space.core.models import Agent
from space.lib import paths, store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7


def _validate_identity(identity: str) -> None:
    if not identity:
        raise ValueError("Identity cannot be empty")
    if " " in identity:
        raise ValueError(
            f"Identity cannot contain spaces. Use hyphens instead: '{identity.replace(' ', '-')}'"
        )


def _row_to_agent(row: store.Row) -> Agent:
    return from_row(row, Agent)


def compute_constitution_hash(constitution_name: str | None) -> str | None:
    """Compute SHA256 hash of constitution file.

    Args:
        constitution_name: Name of constitution file (e.g., 'zealot', 'sentinel')

    Returns:
        Hex digest of SHA256 hash, or None if no constitution
    """
    if not constitution_name:
        return None
    const_path = paths.constitution(constitution_name)
    constitution_text = const_path.read_text()
    return hashlib.sha256(constitution_text.encode()).hexdigest()


def touch_agent(agent_id: str) -> None:
    with store.ensure() as conn:
        conn.execute(
            "UPDATE agents SET last_active_at = ? WHERE agent_id = ?",
            (datetime.now().isoformat(), agent_id),
        )


def get_agent(identifier: str) -> Agent | None:
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT agent_id, identity, constitution, model, role, spawn_count, archived_at, created_at FROM agents WHERE (identity = ? OR agent_id = ?) AND archived_at IS NULL LIMIT 1",
            (identifier, identifier),
        ).fetchone()
        return _row_to_agent(row) if row else None


def register_agent(
    identity: str,
    model: str | None = None,
    constitution: str | None = None,
    role: str | None = None,
) -> str:
    """Explicitly register an identity. Fails if identity already exists.

    If model is None, this is a human identity (no spawning capability).
    """
    _validate_identity(identity)
    agent = get_agent(identity)
    if agent:
        raise ValueError(f"Identity '{identity}' already registered")

    agent_id = uuid7()
    now_iso = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, identity, constitution, model, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_id, identity, constitution, model, role, now_iso),
        )
    touch_agent(agent_id)
    return agent_id


def update_agent(
    identity: str,
    constitution: str | None = None,
    model: str | None = None,
    role: str | None = None,
) -> bool:
    """Update agent fields. Only specified fields are modified.

    If model is specified, provider is inferred from it.
    """

    agent = get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")

    updates = []
    values = []
    if constitution is not None:
        updates.append("constitution = ?")
        values.append(constitution)
    if model is not None:
        updates.append("model = ?")
        values.append(model)
    if role is not None:
        updates.append("role = ?")
        values.append(role)

    if not updates:
        return True

    values.append(agent.agent_id)
    sql = f"UPDATE agents SET {', '.join(updates)} WHERE agent_id = ?"
    with store.ensure() as conn:
        conn.execute(sql, values)
    return True


def clone_agent(src_identity: str, dst_identity: str) -> str:
    _validate_identity(dst_identity)
    src_agent = get_agent(src_identity)
    if not src_agent:
        raise ValueError(f"Source agent '{src_identity}' not found")

    dst_agent = get_agent(dst_identity)
    if dst_agent:
        raise ValueError(f"Target identity '{dst_identity}' already exists")

    return register_agent(dst_identity, src_agent.model, src_agent.constitution)


def rename_agent(old_name: str, new_name: str) -> bool:
    _validate_identity(new_name)
    old_agent = get_agent(old_name)
    if not old_agent:
        return False

    new_agent = get_agent(new_name)
    if new_agent:
        return False

    with store.ensure() as conn:
        conn.execute(
            "UPDATE agents SET identity = ? WHERE agent_id = ?", (new_name, old_agent.agent_id)
        )
    return True


def archive_agent(name: str) -> bool:
    agent = get_agent(name)
    if not agent:
        return False
    agent_id = agent.agent_id

    with store.ensure() as conn:
        conn.execute(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?",
            (datetime.now().isoformat(), agent_id),
        )
    return True


def unarchive_agent(name: str) -> bool:
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ? LIMIT 1", (name,)
        ).fetchone()
        if not row:
            return False

        conn.execute("UPDATE agents SET archived_at = NULL WHERE agent_id = ?", (row["agent_id"],))
    return True


def list_agents() -> list[str]:
    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT identity FROM agents WHERE archived_at IS NULL ORDER BY identity"
        ).fetchall()
        return [row["identity"] for row in rows]


def merge_agents(from_name: str, to_name: str) -> bool:
    from_agent = get_agent(from_name)
    to_agent = get_agent(to_name)

    if not from_agent or not to_agent:
        return False
    from_id = from_agent.agent_id
    to_id = to_agent.agent_id

    if from_id == to_id:
        return False

    with store.ensure() as conn:
        conn.execute("BEGIN")
        try:
            conn.execute("UPDATE messages SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
            conn.execute("UPDATE spawns SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
            conn.execute("UPDATE knowledge SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
            conn.execute("UPDATE memories SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
            conn.execute("DELETE FROM agents WHERE agent_id = ?", (from_id,))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    return True


def agent_identities() -> dict[str, str]:
    """Get agent_id -> identity mapping."""
    with store.ensure() as conn:
        rows = conn.execute("SELECT agent_id, identity FROM agents").fetchall()
        return {row[0]: row[1] for row in rows}


def archived_agents() -> set[str]:
    """Get set of archived agent IDs."""
    with store.ensure() as conn:
        rows = conn.execute("SELECT agent_id FROM agents WHERE archived_at IS NOT NULL").fetchall()
        return {row[0] for row in rows}


def stats() -> dict:
    """Get spawn statistics."""
    with store.ensure() as conn:
        total_agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        active_agents = conn.execute(
            "SELECT COUNT(*) FROM agents WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_agents_count = total_agents - active_agents

        hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

    return {
        "total": total_agents,
        "active": active_agents,
        "archived": archived_agents_count,
        "hashes": hashes,
    }


__all__ = [
    "get_agent",
    "register_agent",
    "update_agent",
    "clone_agent",
    "rename_agent",
    "archive_agent",
    "unarchive_agent",
    "list_agents",
    "merge_agents",
    "touch_agent",
    "agent_identities",
    "archived_agents",
    "stats",
]
