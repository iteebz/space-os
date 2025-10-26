"""Memory search: unified query interface."""

from space.lib import db


def search(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search memory entries by query, optionally filtering by agent, returning structured results with references."""
    from space.core import spawn

    results = []
    with db.ensure("memory") as conn:
        sql_query = (
            "SELECT memory_id, agent_id, topic, message, timestamp, created_at FROM memories "
            "WHERE (message LIKE ? OR topic LIKE ?)"
        )
        params = [f"%{query}%", f"%{query}%"]

        if identity and not all_agents:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Agent '{identity}' not found")
            sql_query += " AND agent_id = ?"
            params.append(agent.agent_id)

        sql_query += " ORDER BY created_at ASC"

        rows = conn.execute(sql_query, params).fetchall()
        for row in rows:
            agent = spawn.get_agent(row["agent_id"])
            results.append(
                {
                    "source": "memory",
                    "memory_id": row["memory_id"],
                    "topic": row["topic"],
                    "message": row["message"],
                    "identity": agent.identity if agent else row["agent_id"],
                    "timestamp": row["created_at"],
                    "reference": f"memory:{row['memory_id']}",
                }
            )
    return results
