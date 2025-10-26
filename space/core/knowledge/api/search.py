"""Knowledge search: unified query interface."""

from space.lib import db


def search(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search knowledge entries by query, optionally filtering by agent, returning structured results with references."""
    from space.core import spawn

    results = []
    with db.ensure("knowledge") as conn:
        sql_query = (
            "SELECT knowledge_id, domain, agent_id, content, created_at FROM knowledge "
            "WHERE (content LIKE ? OR domain LIKE ?)"
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
                    "source": "knowledge",
                    "domain": row["domain"],
                    "knowledge_id": row["knowledge_id"],
                    "contributor": agent.name if agent else row["agent_id"],
                    "content": row["content"],
                    "timestamp": row["created_at"],
                    "reference": f"knowledge:{row['knowledge_id']}",
                }
            )
    return results
