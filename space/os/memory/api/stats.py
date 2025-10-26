"""Memory stats aggregation."""

from space.lib import store


def stats() -> dict:
    """Get memory statistics."""
    with store.ensure("memory") as conn:
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM memories WHERE archived_at IS NULL").fetchone()[
            0
        ]
        archived = total - active

        topics = conn.execute(
            "SELECT COUNT(DISTINCT topic) FROM memories WHERE archived_at IS NULL"
        ).fetchone()[0]

        mem_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM memories GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": topics,
        "mem_by_agent": [{"agent_id": row[0], "count": row[1]} for row in mem_by_agent],
    }
