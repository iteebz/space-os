"""Task operations: background spawn tracking.

Tasks are spawns with is_task=True. Distinction from interactive spawns:
- Tasks: Background execution, started by bridge mentions or CLI, non-interactive
- Spawns: General spawn records (both interactive and task), the data model
- Tasks API: Convenience layer for task-specific operations (create_task, start_task, fail_task)

All tasks are spawns. Not all spawns are tasks. A spawn is a task iff is_task=True.
"""

from datetime import datetime

from space.core.models import Spawn, TaskStatus
from space.lib import store
from space.lib.store import from_row

from .agents import get_agent
from .spawns import create_spawn


def create_task(
    identity: str,
    channel_id: str | None = None,
    input: str | None = None,
) -> Spawn:
    """Create a background task spawn for an agent.

    Args:
        identity: Agent identity (matches constitution)
        channel_id: Channel ID if triggered by bridge mention
        input: Task prompt/description (not persisted, used for execution)

    Returns:
        Spawn object
    """
    agent = get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")

    return create_spawn(
        agent_id=agent.agent_id,
        is_task=True,
        channel_id=channel_id,
    )


def get_task(task_id: str) -> Spawn | None:
    """Get a task spawn by ID."""
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT * FROM spawns WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return None
        return from_row(row, Spawn)


def start_task(task_id: str, pid: int | None = None) -> None:
    """Mark task as started and optionally record PID."""
    updates = ["status = ?"]
    params = [TaskStatus.RUNNING.value]
    if pid is not None:
        updates.append("pid = ?")
        params.append(pid)
    params.append(task_id)
    query = f"UPDATE spawns SET {', '.join(updates)} WHERE id = ?"
    with store.ensure() as conn:
        conn.execute(query, params)


def complete_task(task_id: str) -> None:
    """Mark task as completed."""
    now_iso = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "UPDATE spawns SET status = ?, ended_at = ? WHERE id = ?",
            (TaskStatus.COMPLETED.value, now_iso, task_id),
        )


def fail_task(task_id: str) -> None:
    """Mark task as failed."""
    now_iso = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "UPDATE spawns SET status = ?, ended_at = ? WHERE id = ?",
            (TaskStatus.FAILED.value, now_iso, task_id),
        )


def list_tasks(
    status: str | None = None,
    identity: str | None = None,
    channel_id: str | None = None,
) -> list[Spawn]:
    """List background task spawns with optional filters."""
    query = "SELECT * FROM spawns WHERE is_task = 1"
    params = []

    if status is not None:
        query += " AND status = ?"
        params.append(status)

    if identity is not None:
        agent = get_agent(identity)
        if not agent:
            return []
        query += " AND agent_id = ?"
        params.append(agent.agent_id)

    if channel_id is not None:
        query += " AND channel_id = ?"
        params.append(channel_id)

    query += " ORDER BY created_at DESC"

    with store.ensure() as conn:
        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Spawn) for row in rows]
