"""Database row-to-model conversion helpers."""

import sqlite3
from datetime import datetime

from space.os.models import Task


def calc_duration(started_at: str | None, completed_at: str | None) -> float | None:
    """Calculate task duration in seconds."""
    if not started_at or not completed_at:
        return None
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
        return (end - start).total_seconds()
    except (ValueError, TypeError):
        return None


def row_to_task(row: sqlite3.Row | dict) -> Task:
    """Convert database row to Task model."""
    if isinstance(row, sqlite3.Row):
        row = dict(row)

    duration = calc_duration(row.get("started_at"), row.get("completed_at"))

    return Task(
        task_id=row["task_id"],
        agent_id=row["agent_id"],
        input=row["input"],
        status=row.get("status", "pending"),
        channel_id=row.get("channel_id"),
        output=row.get("output"),
        stderr=row.get("stderr"),
        pid=row.get("pid"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        created_at=row.get("created_at"),
        duration=duration,
    )
