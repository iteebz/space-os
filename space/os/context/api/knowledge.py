"""Context search: knowledge entries."""

from space.lib import store
from space.os import spawn


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search knowledge entries by query (shared across all agents)."""
    results = []
    with store.ensure("knowledge") as conn:
        sql_query = (
            "SELECT knowledge_id, domain, agent_id, content, created_at FROM knowledge "
            "WHERE (content LIKE ? OR domain LIKE ?)"
        )
        params = [f"%{query}%", f"%{query}%"]

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
