"""Task operations: shared work ledger for multi-agent swarms."""

from datetime import datetime

from space.core.models import Task
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import resolve_id, uuid7
from space.os import spawn


def _row_to_task(row: store.Row) -> Task:
    return from_row(row, Task)


def add_task(
    content: str,
    creator_id: str,
    project: str | None = None,
    agent_id: str | None = None,
) -> str:
    task_id = uuid7()
    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, creator_id, content, project, agent_id, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, creator_id, content, project, agent_id, now, "open"),
        )
    spawn.touch_agent(creator_id)
    return task_id


def list_tasks(
    status: str | None = None,
    project: str | None = None,
    agent_id: str | None = None,
    limit: int | None = None,
) -> list[Task]:
    """List tasks. Default: open + in_progress only."""
    with store.ensure() as conn:
        base = "SELECT task_id, creator_id, agent_id, content, project, status, created_at, started_at, completed_at FROM tasks WHERE"

        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        else:
            conditions.append("status IN (?, ?)")
            params.extend(["open", "in_progress"])

        if project:
            conditions.append("project = ?")
            params.append(project)

        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)

        query = f"{base} {' AND '.join(conditions)} ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        return [_row_to_task(row) for row in conn.execute(query, params).fetchall()]


def get_task(task_id: str) -> Task | None:
    try:
        full_id = resolve_id("tasks", "task_id", task_id)
    except ValueError:
        return None

    with store.ensure() as conn:
        row = conn.execute(
            "SELECT task_id, creator_id, agent_id, content, project, status, created_at, started_at, completed_at FROM tasks WHERE task_id = ?",
            (full_id,),
        ).fetchone()

    return _row_to_task(row) if row else None


def start_task(task_id: str, agent_id: str) -> None:
    full_id = resolve_id("tasks", "task_id", task_id)

    now = datetime.now().isoformat()
    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET agent_id = ?, status = ?, started_at = ? WHERE task_id = ?",
            (agent_id, "in_progress", now, full_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(f"Task '{task_id}' not found")

    spawn.touch_agent(agent_id)


def remove_claim(task_id: str, agent_id: str) -> None:
    full_id = resolve_id("tasks", "task_id", task_id)

    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET agent_id = NULL, status = ?, started_at = NULL WHERE task_id = ? AND agent_id = ?",
            ("open", full_id, agent_id),
        )
        if cursor.rowcount == 0:
            task = get_task(full_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")
            raise ValueError(f"Task not claimed by {agent_id}")
    spawn.touch_agent(agent_id)


def done_task(task_id: str, agent_id: str) -> None:
    full_id = resolve_id("tasks", "task_id", task_id)

    now = datetime.now().isoformat()
    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ? AND agent_id = ?",
            ("done", now, full_id, agent_id),
        )
        if cursor.rowcount == 0:
            task = get_task(full_id)
            if not task:
                raise ValueError(f"Task '{task_id}' not found")
            raise ValueError(f"Task not claimed by {agent_id}")
    spawn.touch_agent(agent_id)
