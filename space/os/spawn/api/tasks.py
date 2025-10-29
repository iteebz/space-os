"""Task operations: create, get, update, list."""

from datetime import datetime

from space.core.models import Task, TaskStatus
from space.lib.store import from_row
from space.lib.uuid7 import uuid7
from space.os.spawn import db

from .agents import get_agent


def create_task(
    identity: str | None = None,
    input: str = "",
    channel_id: str | None = None,
    role: str | None = None,
) -> str:
    ident = role or identity
    if not ident:
        raise ValueError("Either identity or role must be provided")
    agent = get_agent(ident)
    if not agent:
        raise ValueError(f"Agent '{ident}' not found")
    agent_id = agent.agent_id
    task_id = uuid7()
    now_iso = datetime.now().isoformat()
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO tasks (task_id, agent_id, channel_id, input, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, agent_id, channel_id, input, "pending", now_iso),
        )
    return task_id


def get_task(task_id: str) -> Task | None:
    """Get task by ID."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return None
        return from_row(row, Task)


def start_task(task_id: str, pid: int | None = None):
    """Mark task as started."""
    now_iso = datetime.now().isoformat()
    updates = ["status = ?", "started_at = ?"]
    params = [TaskStatus.RUNNING.value, now_iso]
    if pid is not None:
        updates.append("pid = ?")
        params.append(pid)

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
    with db.connect() as conn:
        conn.execute(query, params)


def complete_task(task_id: str, output: str | None = None, stderr: str | None = None):
    """Mark task as completed."""
    now_iso = datetime.now().isoformat()
    updates = ["status = ?", "completed_at = ?"]
    params = [TaskStatus.COMPLETED.value, now_iso]
    if output is not None:
        updates.append("output = ?")
        params.append(output)
    if stderr is not None:
        updates.append("stderr = ?")
        params.append(stderr)

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
    with db.connect() as conn:
        conn.execute(query, params)


def fail_task(task_id: str, stderr: str | None = None):
    """Mark task as failed."""
    now_iso = datetime.now().isoformat()
    updates = ["status = ?", "completed_at = ?"]
    params = [TaskStatus.FAILED.value, now_iso]
    if stderr is not None:
        updates.append("stderr = ?")
        params.append(stderr)

    params.append(task_id)
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
    with db.connect() as conn:
        conn.execute(query, params)


def list_tasks(
    status: str | None = None,
    identity: str | None = None,
    role: str | None = None,
    channel_id: str | None = None,
) -> list[Task]:
    """List tasks with optional filters."""
    query = "SELECT * FROM tasks WHERE 1 = 1"
    params = []

    if status is not None:
        query += " AND status = ?"
        params.append(status)
    ident = role or identity
    if ident is not None:
        agent = get_agent(ident)
        if not agent:
            return []
        query += " AND agent_id = ?"
        params.append(agent.agent_id)
    if channel_id is not None:
        query += " AND channel_id = ?"
        params.append(channel_id)

    query += " ORDER BY created_at DESC"

    with db.connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Task) for row in rows]
