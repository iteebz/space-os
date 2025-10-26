"""Knowledge stats aggregation."""

from space.lib import store


def stats() -> dict:
    """Get knowledge statistics."""
    with store.ensure("knowledge") as conn:
        total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived = total - active

        domains = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]

        know_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM knowledge GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": domains,
        "know_by_agent": [{"agent_id": row[0], "count": row[1]} for row in know_by_agent],
    }
