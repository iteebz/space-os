"""Task operations: create, get, update, list."""

from datetime import datetime

from space.os import events
from space.os.lib import db
from space.os.lib.db.conversions import row_to_task
from space.os.lib.uuid7 import uuid7
from space.os.models import Task, TaskStatus

from .agents import get_agent_id


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
