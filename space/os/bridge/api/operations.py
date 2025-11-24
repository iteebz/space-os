"""Bridge operations: search."""

from space.core.models import SearchResult
from space.lib import store
from space.os import spawn


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[SearchResult]:
    results = []

    agent_id = None
    if identity and not all_agents:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Agent '{identity}' not found")
        agent_id = agent.agent_id

    with store.ensure() as conn:
        sql_query = (
            "SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at, c.name as channel_name "
            "FROM messages m JOIN channels c ON m.channel_id = c.channel_id "
            "WHERE (m.content LIKE ? OR c.name LIKE ?)"
        )
        params = [f"%{query}%", f"%{query}%"]

        if agent_id:
            sql_query += " AND m.agent_id = ?"
            params.append(agent_id)

        sql_query += " ORDER BY m.created_at ASC"
        rows = conn.execute(sql_query, params).fetchall()

        for row in rows:
            agent = spawn.get_agent(row["agent_id"])
            results.append(
                SearchResult(
                    source="bridge",
                    reference=f"bridge:{row['channel_name']}:{row['message_id']}",
                    content=row["content"],
                    timestamp=row["created_at"],
                    agent_id=row["agent_id"],
                    identity=agent.identity if agent else row["agent_id"],
                    metadata={"channel_name": row["channel_name"], "message_id": row["message_id"]},
                )
            )

    return results
