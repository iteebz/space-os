"""Database operations for ops primitive."""

import sqlite3

from space import db
from space.db import from_row
from space.lib.uuid7 import uuid7
from space.models import Task

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    description TEXT NOT NULL,
    assigned_to TEXT,
    status TEXT DEFAULT 'open',
    handover TEXT,
    channel_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES tasks(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id);
"""

db.register("ops", "ops.db", _SCHEMA)
db.add_migrations("ops", [])


def connect():
    """Get connection to ops database."""
    return db.ensure("ops")


def _row_to_task(row: sqlite3.Row) -> Task:
    """Convert database row to Task model."""
    return from_row(row, Task)


def create_task(
    description: str,
    parent_id: str | None = None,
    channel_id: str | None = None,
    assigned_to: str | None = None,
) -> str:
    """Create a new task."""
    task_id = uuid7()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (id, description, parent_id, channel_id, assigned_to)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, description, parent_id, channel_id, assigned_to),
        )
    return task_id


def get_task(task_id: str) -> Task | None:
    """Get task by ID."""
    with connect() as conn:
        cursor = conn.execute(
            """
            SELECT id as task_id, parent_id, description, assigned_to, status,
                   handover, channel_id, created_at, completed_at
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        return _row_to_task(row) if row else None


def list_tasks(
    status: str | None = None,
    assigned_to: str | None = None,
    parent_id: str | None = None,
) -> list[Task]:
    """List tasks with optional filters."""
    with connect() as conn:
        query = """
            SELECT id as task_id, parent_id, description, assigned_to, status,
                   handover, channel_id, created_at, completed_at
            FROM tasks WHERE 1=1
        """
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)

        if parent_id is not None:
            if parent_id == "":
                query += " AND parent_id IS NULL"
            else:
                query += " AND parent_id = ?"
                params.append(parent_id)

        query += " ORDER BY created_at DESC"

        cursor = conn.execute(query, params)
        return [_row_to_task(row) for row in cursor.fetchall()]


def claim_task(task_id: str, agent_id: str) -> bool:
    """Claim a task for an agent."""
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET assigned_to = ?, status = 'claimed' WHERE id = ? AND status = 'open'",
            (agent_id, task_id),
        )
        return cursor.rowcount > 0


def complete_task(task_id: str, handover: str, agent_id: str) -> bool:
    """Mark task as complete with handover documentation."""
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE tasks
            SET status = 'complete', handover = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND assigned_to = ? AND status IN ('claimed', 'blocked')
            """,
            (handover, task_id, agent_id),
        )
        return cursor.rowcount > 0


def block_task(task_id: str, reason: str) -> bool:
    """Block a task with a reason."""
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = 'blocked', handover = ? WHERE id = ?",
            (reason, task_id),
        )
        return cursor.rowcount > 0


def get_subtasks(parent_id: str) -> list[Task]:
    """Get all subtasks for a parent task."""
    return list_tasks(parent_id=parent_id)


def get_task_tree(task_id: str) -> dict:
    """Get task and all descendants as tree structure."""
    task = get_task(task_id)
    if not task:
        return None

    subtasks = get_subtasks(task_id)
    return {
        "task": task,
        "subtasks": [get_task_tree(st.task_id) for st in subtasks],
    }
