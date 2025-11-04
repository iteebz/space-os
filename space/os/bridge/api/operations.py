"""Bridge operations: search, statistics."""

from space.core.models import BridgeStats, SearchResult
from space.lib import store
from space.os import spawn


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[SearchResult]:
    results = []

    with store.ensure() as conn:
        sql_query = (
            "SELECT m.message_id, m.channel_id, m.agent_id, m.content, m.created_at, c.name as channel_name "
            "FROM messages m JOIN channels c ON m.channel_id = c.channel_id "
            "WHERE (m.content LIKE ? OR c.name LIKE ?) ORDER BY m.created_at ASC"
        )
        params = [f"%{query}%", f"%{query}%"]
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


def stats() -> BridgeStats:
    with store.ensure() as conn:
        total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        total_channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        archived_channels = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE archived_at IS NOT NULL"
        ).fetchone()[0]
        active_channels = total_channels - archived_channels

    return BridgeStats(
        available=True,
        total=total_messages,
        channels=total_channels,
        active_channels=active_channels,
        archived_channels=archived_channels,
    )
