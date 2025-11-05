"""Task operations: shared work ledger for multi-agent swarms."""

from datetime import datetime

from space.core.models import Task
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import resolve_id, uuid7
from space.os import spawn


def _row_to_task(row: store.Row) -> Task:
    data = dict(row)
    return from_row(data, Task)


def add_task(
    content: str,
    creator_id: str,
    project: str | None = None,
    agent_id: str | None = None,
) -> str:
    """Create a new task.

    Args:
        content: Task description
        creator_id: Agent ID of task creator
        project: Optional project/epic name
        agent_id: Optional agent to claim task immediately

    Returns:
        task_id
    """
    task_id = uuid7()
    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO tasks (task_id, creator_id, content, project, agent_id, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, creator_id, content, project, agent_id, now, "open"),
        )
    spawn.api.touch_agent(creator_id)
    return task_id


def list_tasks(
    status: str | None = None,
    project: str | None = None,
    agent_id: str | None = None,
    limit: int | None = None,
) -> list[Task]:
    """List tasks with optional filtering.

    Args:
        status: Filter by status (open, in_progress, done)
        project: Filter by project
        agent_id: Filter by claimed agent
        limit: Maximum results

    Returns:
        List of Task objects
    """
    with store.ensure() as conn:
        params = []
        query = "SELECT task_id, creator_id, agent_id, content, project, status, created_at, started_at, completed_at FROM tasks WHERE 1=1"

        if status:
            query += " AND status = ?"
            params.append(status)
        elif status is None:
            # Default: show open + in_progress
            query += " AND status IN (?, ?)"
            params.extend(["open", "in_progress"])

        if project:
            query += " AND project = ?"
            params.append(project)

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_task(row) for row in rows]


def get_task(task_id: str) -> Task | None:
    """Get task by ID (supports partial ID resolution)."""
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
    """Claim a task (mark as in_progress).

    Args:
        task_id: Task ID to claim
        agent_id: Agent claiming the task

    Raises:
        ValueError: If task not found
    """
    full_id = resolve_id("tasks", "task_id", task_id)
    task = get_task(full_id)
    if not task:
        raise ValueError(f"Task '{task_id}' not found")

    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "UPDATE tasks SET agent_id = ?, status = ?, started_at = ? WHERE task_id = ?",
            (agent_id, "in_progress", now, full_id),
        )
    spawn.api.touch_agent(agent_id)


def remove_claim(task_id: str, agent_id: str) -> None:
    """Unclaim a task (return to open).

    Args:
        task_id: Task ID to unclaim
        agent_id: Agent unclaiming (for verification)

    Raises:
        ValueError: If task not found or not claimed by agent
    """
    full_id = resolve_id("tasks", "task_id", task_id)
    task = get_task(full_id)
    if not task:
        raise ValueError(f"Task '{task_id}' not found")
    if task.agent_id != agent_id:
        raise ValueError(f"Task not claimed by {agent_id}")

    with store.ensure() as conn:
        conn.execute(
            "UPDATE tasks SET agent_id = NULL, status = ?, started_at = NULL WHERE task_id = ?",
            ("open", full_id),
        )
    spawn.api.touch_agent(agent_id)


def done_task(task_id: str, agent_id: str) -> None:
    """Mark task as complete.

    Args:
        task_id: Task ID to complete
        agent_id: Agent completing (for verification)

    Raises:
        ValueError: If task not found or not claimed by agent
    """
    full_id = resolve_id("tasks", "task_id", task_id)
    task = get_task(full_id)
    if not task:
        raise ValueError(f"Task '{task_id}' not found")
    if task.agent_id != agent_id:
        raise ValueError(f"Task not claimed by {agent_id}")

    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE task_id = ?",
            ("done", now, full_id),
        )
    spawn.api.touch_agent(agent_id)
