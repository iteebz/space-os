"""Task operations: background spawn tracking."""

from datetime import datetime

from space.core import db
from space.core.models import Session, TaskStatus
from space.lib.store import from_row

from .agents import get_agent
from .sessions import create_session


def create_task(
    identity: str,
    channel_id: str | None = None,
    input: str | None = None,
) -> Session:
    """Create a background task session for an agent.

    Args:
        identity: Agent identity (matches constitution)
        channel_id: Channel ID if triggered by bridge mention
        input: Task prompt/description (not persisted, used for execution)

    Returns:
        Session object
    """
    agent = get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")

    return create_session(
        agent_id=agent.agent_id,
        is_task=True,
        channel_id=channel_id,
    )


def get_task(task_id: str) -> Session | None:
    """Get a task session by ID."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return None
        return from_row(row, Session)


def start_task(task_id: str, pid: int | None = None) -> None:
    """Mark task as started and optionally record PID."""
    updates = ["status = ?"]
    params = [TaskStatus.RUNNING.value]
    if pid is not None:
        updates.append("pid = ?")
        params.append(pid)
    params.append(task_id)
    query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
    with db.connect() as conn:
        conn.execute(query, params)


def complete_task(task_id: str) -> None:
    """Mark task as completed."""
    now_iso = datetime.now().isoformat()
    with db.connect() as conn:
        conn.execute(
            "UPDATE sessions SET status = ?, ended_at = ? WHERE id = ?",
            (TaskStatus.COMPLETED.value, now_iso, task_id),
        )


def fail_task(task_id: str) -> None:
    """Mark task as failed."""
    now_iso = datetime.now().isoformat()
    with db.connect() as conn:
        conn.execute(
            "UPDATE sessions SET status = ?, ended_at = ? WHERE id = ?",
            (TaskStatus.FAILED.value, now_iso, task_id),
        )


def list_tasks(
    status: str | None = None,
    identity: str | None = None,
    channel_id: str | None = None,
) -> list[Session]:
    """List background task sessions with optional filters."""
    query = "SELECT * FROM sessions WHERE is_task = 1"
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

    with db.connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [from_row(row, Session) for row in rows]
