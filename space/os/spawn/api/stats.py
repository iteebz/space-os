"""Spawn stats aggregation."""

from space.os.spawn import db


def stats() -> dict:
    """Get spawn statistics."""
    with db.connect() as conn:
        total_agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        active_agents = conn.execute(
            "SELECT COUNT(*) FROM agents WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_agents = total_agents - active_agents

        hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

    return {
        "total": total_agents,
        "active": active_agents,
        "archived": archived_agents,
        "hashes": hashes,
    }


def agent_identities() -> dict[str, str]:
    """Get agent_id -> identity mapping."""
    with db.connect() as conn:
        rows = conn.execute("SELECT agent_id, identity FROM agents").fetchall()
        return {row[0]: row[1] for row in rows}


def archived_agents() -> set[str]:
    """Get set of archived agent IDs."""
    with db.connect() as conn:
        rows = conn.execute("SELECT agent_id FROM agents WHERE archived_at IS NOT NULL").fetchall()
        return {row[0] for row in rows}


def agent_stats(agent_id: str) -> dict:
    """Get task stats for a specific agent."""
    with db.connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id = ?", (agent_id,)
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id = ? AND status = ?", (agent_id, "pending")
        ).fetchone()[0]
        running = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id = ? AND status = ?", (agent_id, "running")
        ).fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE agent_id = ? AND status = ?", (agent_id, "completed")
        ).fetchone()[0]

        last_row = conn.execute(
            "SELECT completed_at, created_at FROM tasks WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        last_activity = None
        if last_row:
            last_activity = last_row[0] or last_row[1]

    return {
        "task_count": total,
        "pending": pending,
        "running": running,
        "completed": completed,
        "last_activity": last_activity,
    }
