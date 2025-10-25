import time
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from space.os import db, events
from space.os.db import query_builders as qb
from space.os.db.conversions import row_to_task
from space.os.lib import paths
from space.os.lib.uuid7 import uuid7
from space.os.models import Task, TaskStatus

from . import migrations


def schema() -> str:
    """Spawn database schema."""
    return """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel_id TEXT,
    input TEXT NOT NULL,
    output TEXT,
    stderr TEXT,
    status TEXT DEFAULT 'pending',
    pid INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id);
"""


def _register():
    db.register("spawn", "spawn.db", schema())
    db.add_migrations("spawn", migrations.MIGRATIONS)


_register()


def path() -> Path:
    return paths.space_data() / "spawn.db"


def connect():
    """Return connection to spawn database via central registry."""
    return db.ensure("spawn")


def get_agent_ids(name: str, include_archived: bool = False) -> list[str]:
    """Get all agent UUIDs matching name."""
    with db.ensure("spawn") as conn:
        return qb.agent_by_name(conn, name, include_archived=include_archived)


def get_agent_id(name: str) -> str | None:
    """Get first active agent UUID by name. For single-agent ops."""
    ids = get_agent_ids(name, include_archived=False)
    return ids[0] if ids else None


@lru_cache(maxsize=256)
def get_agent_name(agent_id: str) -> str | None:
    """Get agent name by UUID."""
    with db.ensure("spawn") as conn:
        return qb.agent_by_id(conn, agent_id)


def clear_role_cache():
    """Invalidate agent name cache."""
    get_agent_name.cache_clear()


get_role = get_agent_name


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
    clear_role_cache()
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
    clear_role_cache()
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
    clear_role_cache()
    return True


def restore_agent(name: str) -> bool:
    """Restore an archived agent. Returns True if restored, False if not found."""
    agent_ids = get_agent_ids(name, include_archived=True)
    if not agent_ids:
        return False

    agent_id = agent_ids[0]
    with db.ensure("spawn") as conn:
        conn.execute("UPDATE agents SET archived_at = NULL WHERE agent_id = ?", (agent_id,))
    clear_role_cache()
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

    if not from_id:
        return False
    if not to_id:
        return False
    if from_id == to_id:
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

    clear_role_cache()
    return True


def backfill_unknown_agents() -> int:
    """Register orphaned agent IDs from bridge into registry. Returns count of new agents."""
    bridge_db = paths.space_data() / "bridge.db"
    if not bridge_db.exists():
        return 0

    with db.ensure("bridge") as bridge_conn:
        bridge_agent_ids = {
            row[0]
            for row in bridge_conn.execute(
                "SELECT DISTINCT agent_id FROM messages WHERE agent_id IS NOT NULL"
            )
        }

    with connect() as reg_conn:
        registered_ids = {row[0] for row in reg_conn.execute("SELECT agent_id FROM agents")}

    unknown_ids = bridge_agent_ids - registered_ids
    now_iso = datetime.now().isoformat()

    with db.ensure("spawn") as conn:
        for agent_id in unknown_ids:
            placeholder_name = f"orphaned-{agent_id[:8]}"
            conn.execute(
                "INSERT INTO agents (agent_id, name, created_at) VALUES (?, ?, ?)",
                (agent_id, placeholder_name, now_iso),
            )

    return len(unknown_ids)


def create_task(role: str, input: str, channel_id: str | None = None) -> str:
    """Create task record. Returns task_id."""
    agent_id = get_agent_id(role)
    if not agent_id:
        raise ValueError(f"Agent '{role}' not found")
    task_id = uuid7()
    now_iso = datetime.now().isoformat()
    with db.ensure("spawn") as conn:
        conn.execute(
            """
            INSERT INTO tasks (task_id, agent_id, channel_id, input, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, agent_id, channel_id, input, "pending", now_iso),
        )
    events.emit("spawn", "task.create", agent_id, f"Task created for {role}")
    return task_id


def get_task(task_id: str) -> Task | None:
    """Get task by ID."""
    with db.ensure("spawn") as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return None
        return row_to_task(row)


def update_task(
    task_id: str,
    status: TaskStatus | str | None = None,
    output: str | None = None,
    stderr: str | None = None,
    pid: int | None = None,
    mark_started: bool = False,
    mark_completed: bool = False,
):
    """Update task fields."""
    now_iso = datetime.now().isoformat()
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(str(status))
    if output is not None:
        updates.append("output = ?")
        params.append(output)
    if stderr is not None:
        updates.append("stderr = ?")
        params.append(stderr)
    if pid is not None:
        updates.append("pid = ?")
        params.append(pid)
    if mark_started:
        updates.append("started_at = ?")
        params.append(now_iso)
    if mark_completed:
        updates.append("completed_at = ?")
        params.append(now_iso)

    if not updates:
        return

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"

    with db.ensure("spawn") as conn:
        conn.execute(query, params)


def list_tasks(status: str | None = None, role: str | None = None) -> list[Task]:
    """List tasks with optional filters."""
    query = "SELECT * FROM tasks WHERE 1 = 1"
    params = []

    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if role is not None:
        agent_id = get_agent_id(role)
        if not agent_id:
            return []
        query += " AND agent_id = ?"
        params.append(agent_id)

    query += " ORDER BY created_at DESC"

    with db.ensure("spawn") as conn:
        rows = conn.execute(query, params).fetchall()
        return [row_to_task(row) for row in rows]
