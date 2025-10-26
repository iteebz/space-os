"""Bridge search: unified query interface."""

from space.lib import store


def search(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search bridge messages by query, optionally filtering by agent, returning structured results with references."""
    from space.os import spawn

    results = []

    with store.ensure("bridge") as conn:
        sql_query = (
            "SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at, c.name as channel_name "
            "FROM messages m JOIN channels c ON m.channel_id = c.channel_id "
            "WHERE (m.content LIKE ? OR c.name LIKE ?)"
        )

        params = [f"%{query}%", f"%{query}%"]

        if identity and not all_agents:
            agent = spawn.get_agent(identity)

            if not agent:
                raise ValueError(f"Agent '{identity}' not found")

            sql_query += " AND m.agent_id = ?"

            params.append(agent.agent_id)

        sql_query += " ORDER BY m.created_at ASC"

        rows = conn.execute(sql_query, params).fetchall()

        for row in rows:
            agent = spawn.get_agent(row["agent_id"])

            results.append(
                {
                    "source": "bridge",
                    "channel_name": row["channel_name"],
                    "message_id": row["message_id"],
                    "sender": agent.identity if agent else row["agent_id"],
                    "content": row["content"],
                    "timestamp": row["created_at"],
                    "reference": f"bridge:{row['channel_name']}:{row['message_id']}",
                }
            )

    return results
