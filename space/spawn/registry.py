import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache

from .. import config, events
from ..lib import db, paths
from ..lib.uuid7 import uuid7

_SPAWN_SCHEMA = """
CREATE TABLE IF NOT EXISTS constitutions (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    config.spawn_dir().mkdir(parents=True, exist_ok=True)
    config.registry_db().parent.mkdir(parents=True, exist_ok=True)
    db.ensure_schema(config.registry_db(), _SPAWN_SCHEMA, spawn_migrations)


def save_constitution(constitution_hash: str, content: str):
    """Save constitution content by hash (content-addressable store)."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO constitutions (hash, content)
            VALUES (?, ?)
            """,
            (constitution_hash, content),
        )
        conn.commit()


def get_constitution(constitution_hash: str) -> str | None:
    """Retrieve constitution content by hash."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM constitutions WHERE hash = ?",
            (constitution_hash,),
        ).fetchone()
        return row["content"] if row else None


@contextmanager
def get_db():
    db_path = config.registry_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_agent_ids(name: str, include_archived: bool = False) -> list[str]:
    """Get all agent UUIDs matching name."""
    with get_db() as conn:
        archive_filter = "" if include_archived else "AND archived_at IS NULL"
        rows = conn.execute(
            f"SELECT id FROM agents WHERE name = ? {archive_filter}", (name,)
        ).fetchall()
        return [row["id"] for row in rows]


def get_agent_id(name: str) -> str | None:
    """Get first active agent UUID by name. For single-agent ops."""
    ids = get_agent_ids(name, include_archived=False)
    return ids[0] if ids else None


@lru_cache(maxsize=256)
def get_identity(agent_id: str) -> str | None:
    """Get agent identity by UUID."""
    with get_db() as conn:
        row = conn.execute("SELECT name FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return row["name"] if row else None


def clear_identity_cache():
    """Invalidate agent name cache."""
    get_identity.cache_clear()


def ensure_agent(name: str) -> str:
    """Get or create agent, return UUID."""
    # Check for active agent first
    active_agent_id = get_agent_id(name)
    if active_agent_id:
        return active_agent_id

    # If no active agent, check for archived agents with the same name
    archived_agent_ids = get_agent_ids(name, include_archived=True)
    if archived_agent_ids:
        # Restore the first archived agent found
        agent_id = archived_agent_ids[0]
        restore_agent(
            name
        )  # This will restore all agents with that name, but we only care about one for now
        return agent_id

    # If no agent (active or archived) exists, create a new one
    agent_id = uuid7()
    now_iso = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agents (id, name, created_at) VALUES (?, ?, ?)",
            (agent_id, name, now_iso),
        )
        conn.commit()
    clear_identity_cache()
    events.emit("spawn", "agent.create", agent_id, f"Agent '{name}' created")
    return agent_id


def get_self_description(identity: str) -> str | None:
    """Get self-description for agent."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self_description FROM agents WHERE name = ? LIMIT 1",
            (identity,),
        ).fetchone()
        return row["self_description"] if row else None


def set_self_description(identity: str, description: str) -> bool:
    """Set self-description for agent. Returns True when an update occurs."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ? LIMIT 1", (identity,)).fetchone()
        if row:
            conn.execute(
                "UPDATE agents SET self_description = ? WHERE id = ?",
                (description, row["id"]),
            )
        else:
            agent_id = uuid7()
            conn.execute(
                "INSERT INTO agents (id, name, self_description) VALUES (?, ?, ?)",
                (agent_id, identity, description),
            )
        conn.commit()
        return True


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Merges histories if new_name exists."""
    old_agent_id = _resolve_agent(old_name)
    if not old_agent_id:
        return False

    with get_db() as conn:
        existing_agent = conn.execute(
            "SELECT id FROM agents WHERE name = ?", (new_name,)
        ).fetchone()
        if existing_agent:
            return False
        conn.execute("UPDATE agents SET name = ? WHERE id = ?", (new_name, old_agent_id))
        conn.commit()
    clear_identity_cache()
    return True


def _drop_canonical_id(conn):
    """Remove canonical_id column - shared names replace canonical linking."""
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agents'")
    row = cursor.fetchone()
    if not row:
        return

    schema = row[0]
    if "canonical_id" not in schema:
        return

    cursor = conn.execute("PRAGMA table_info(agents)")
    columns = [col[1] for col in cursor.fetchall() if col[1] != "canonical_id"]
    col_list = ", ".join(columns)

    conn.execute("""
        CREATE TABLE agents_new (
            id TEXT PRIMARY KEY,
            name TEXT,
            self_description TEXT,
            archived_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute(f"""
        INSERT INTO agents_new ({col_list})
        SELECT {col_list} FROM agents
    """)

    conn.execute("DROP TABLE agents")
    conn.execute("ALTER TABLE agents_new RENAME TO agents")


spawn_migrations = [
    ("drop_canonical_id", _drop_canonical_id),
]


def archive_agent(name: str) -> bool:
    """Archive an agent. Returns True if archived, False if not found."""

    agent_id = get_agent_id(name)
    if not agent_id:
        return False

    with get_db() as conn:
        conn.execute("UPDATE agents SET archived_at = ? WHERE id = ?", (int(time.time()), agent_id))
        conn.commit()
    return True


def restore_agent(name: str) -> bool:
    """Restore an archived agent. Returns True if restored, False if not found."""
    agent_ids = get_agent_ids(name, include_archived=True)
    if not agent_ids:
        return False

    with get_db() as conn:
        for agent_id in agent_ids:
            conn.execute("UPDATE agents SET archived_at = NULL WHERE id = ?", (agent_id,))
        conn.commit()
    return True


def list_all_agents() -> list[str]:
    """List all active agents."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT name FROM agents WHERE archived_at IS NULL ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]


def _resolve_agent(identifier: str) -> str | None:
    """Resolve name or UUID to UUID."""
    if len(identifier) == 36 and identifier.count("-") == 4:
        with get_db() as conn:
            row = conn.execute("SELECT id FROM agents WHERE id = ?", (identifier,)).fetchone()
            return row["id"] if row else None
    else:
        ids = get_agent_ids(identifier, include_archived=True)
        if len(ids) > 1:
            return None
        return ids[0] if ids else None


def merge_agents(from_identifier: str, to_identifier: str) -> bool:
    """Merge agent histories. Migrates all references from source to target."""

    from_id = _resolve_agent(from_identifier)
    to_id = _resolve_agent(to_identifier)

    if not from_id:
        return False
    if not to_id:
        return False
    if from_id == to_id:
        return False

    config.registry_db()
    events_db = paths.dot_space() / "events.db"
    memory_db = paths.dot_space() / "memory.db"
    knowledge_db = paths.dot_space() / "knowledge.db"
    bridge_db = paths.dot_space() / "bridge.db"

    with get_db() as conn:
        conn.execute(
            "UPDATE agents SET name = (SELECT name FROM agents WHERE id = ?) WHERE id = ?",
            (to_id, from_id),
        )
        conn.commit()

    if events_db.exists():
        conn = sqlite3.connect(events_db)
        conn.execute("UPDATE events SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()

    if memory_db.exists():
        conn = sqlite3.connect(memory_db)
        conn.execute("UPDATE memories SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()

    if knowledge_db.exists():
        conn = sqlite3.connect(knowledge_db)
        conn.execute("UPDATE knowledge SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()

    if bridge_db.exists():
        conn = sqlite3.connect(bridge_db)
        conn.execute("UPDATE messages SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()

    with get_db() as conn:
        conn.execute("DELETE FROM agents WHERE id = ?", (from_id,))
        conn.commit()

    return True


def backfill_unknown_agents() -> int:
    """Register orphaned agent IDs from bridge into registry. Returns count of new agents."""
    bridge_db = paths.dot_space() / "bridge.db"
    if not bridge_db.exists():
        return 0

    with db.connect(bridge_db) as bridge_conn:
        bridge_agent_ids = {
            row[0]
            for row in bridge_conn.execute(
                "SELECT DISTINCT agent_id FROM messages WHERE agent_id IS NOT NULL"
            )
        }

    with get_db() as reg_conn:
        registered_ids = {row[0] for row in reg_conn.execute("SELECT id FROM agents")}

    unknown_ids = bridge_agent_ids - registered_ids
    now_iso = datetime.now().isoformat()

    with get_db() as conn:
        for agent_id in unknown_ids:
            placeholder_name = f"orphaned-{agent_id[:8]}"
            conn.execute(
                "INSERT INTO agents (id, name, created_at) VALUES (?, ?, ?)",
                (agent_id, placeholder_name, now_iso),
            )
        conn.commit()

    return len(unknown_ids)
