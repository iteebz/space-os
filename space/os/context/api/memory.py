"""Context search: memory entries."""

from space.lib import store
from space.os import spawn


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search memory entries by query, filtering by agent if identity provided."""
    results = []
    with store.ensure("memory") as conn:
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
