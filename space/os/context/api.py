"""Context API: search across 5 domains (bridge, memory, knowledge, canon, sessions)."""

from space.lib import store
from space.lib.paths import canon_path
from space.os import sessions, spawn

MAX_SEARCH_LEN = 256
MAX_CANON_CONTENT_LENGTH = 500
TIMELINE_LIMIT = 10


def _validate_search_term(term: str) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    if len(term) > MAX_SEARCH_LEN:
        raise ValueError(f"Search term too long (max {MAX_SEARCH_LEN} chars, got {len(term)})")


def _search_bridge(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search bridge messages by query (shared channels)."""
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


def _search_canon(
    query: str, identity: str | None = None, all_agents: bool = False
) -> list[dict]:
    """Search canon documents by query."""
    if not query:
        return []

    canon_root = canon_path()
    if not canon_root.exists():
        return []

    matches: list[dict] = []
    for md_file in canon_root.rglob("*.md"):
        try:
            content = md_file.read_text()
        except Exception:
            continue

        if query.lower() not in content.lower():
            continue

        relative_path = md_file.relative_to(canon_root)
        truncated_content = content[:MAX_CANON_CONTENT_LENGTH]
        if len(content) > MAX_CANON_CONTENT_LENGTH:
            truncated_content += "..."

        matches.append(
            {
                "source": "canon",
                "path": str(relative_path),
                "content": truncated_content,
                "reference": f"canon:{relative_path}",
            }
        )

    return matches


def _search_knowledge(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search knowledge entries by query (shared across all agents)."""
    results = []
    with store.ensure() as conn:
        sql_query = (
            "SELECT knowledge_id, domain, agent_id, content, created_at FROM knowledge "
            "WHERE (content LIKE ? OR domain LIKE ?) AND archived_at IS NULL ORDER BY created_at ASC"
        )
        params = [f"%{query}%", f"%{query}%"]
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


def _search_memory(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search memory entries by query, filtering by agent if identity provided."""
    results = []
    with store.ensure() as conn:
        sql_query = (
            "SELECT memory_id, agent_id, topic, message, created_at FROM memories "
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


def _search_sessions(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search provider session logs directly (stateless, ephemeral discovery)."""
    return sessions.api.operations.search(query, identity, all_agents)


def _add_to_timeline(timeline: list[dict], seen: set, source: str, key: tuple, result: dict, mapping: dict) -> None:
    """Add result to timeline if not already seen, using mapping to normalize fields."""
    if key not in seen:
        seen.add(key)
        timeline.append({
            "source": source,
            "type": result[mapping["type"]],
            "identity": result.get(mapping["identity"]),
            "data": result[mapping["data"]],
            "timestamp": result[mapping["timestamp"]],
            "reference": result["reference"],
        })


def collect_timeline(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Unified timeline: evolution across all sources.

    Memory is only included if --as <identity> is specified (private working memory).
    """
    _validate_search_term(query)
    seen = set()
    timeline = []

    if identity:
        for result in _search_memory(query, identity, all_agents):
            _add_to_timeline(timeline, seen, "memory", (result["source"], result.get("memory_id")), result, {
                "type": "topic",
                "identity": "identity",
                "data": "message",
                "timestamp": "timestamp",
            })

    for result in _search_knowledge(query, identity, all_agents):
        _add_to_timeline(timeline, seen, "knowledge", (result["source"], result.get("knowledge_id")), result, {
            "type": "domain",
            "identity": "contributor",
            "data": "content",
            "timestamp": "timestamp",
        })

    for result in _search_bridge(query, identity, all_agents):
        _add_to_timeline(timeline, seen, "bridge", (result["source"], result.get("message_id")), result, {
            "type": "channel_name",
            "identity": "sender",
            "data": "content",
            "timestamp": "timestamp",
        })

    for result in _search_sessions(query, identity, all_agents):
        _add_to_timeline(timeline, seen, "sessions", (result["source"], result.get("session_id")), result, {
            "type": "cli",
            "identity": "identity",
            "data": "text",
            "timestamp": "timestamp",
        })

    for result in _search_canon(query, identity, all_agents):
        if (result["source"], result.get("path")) not in seen:
            timeline.append({
                "source": result["source"],
                "type": "documentation",
                "identity": None,
                "data": result["content"],
                "timestamp": 0,
                "reference": result["reference"],
            })

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline[-TIMELINE_LIMIT:]


def collect_current_state(query: str, identity: str | None, all_agents: bool) -> dict:
    """Unified state: current entries across all sources.

    Memory is only included if --as <identity> is specified (private working memory).
    """
    results = {"memory": [], "knowledge": [], "bridge": [], "provider_chats": [], "canon": []}

    if identity:
        results["memory"] = [
            {
                "identity": r["identity"],
                "topic": r["topic"],
                "message": r["message"],
                "reference": r["reference"],
            }
            for r in _search_memory(query, identity, all_agents)
        ]

    results["knowledge"] = [
        {
            "domain": r["domain"],
            "content": r["content"],
            "contributor": r["contributor"],
            "reference": r["reference"],
        }
        for r in _search_knowledge(query, identity, all_agents)
    ]

    results["bridge"] = [
        {
            "channel": r["channel_name"],
            "sender": r["sender"],
            "content": r["content"],
            "reference": r["reference"],
        }
        for r in _search_bridge(query, identity, all_agents)
    ]

    results["provider_chats"] = [
        {
            "cli": r["cli"],
            "session_id": r["session_id"],
            "identity": r["identity"],
            "role": r["role"],
            "text": r["text"],
            "reference": r["reference"],
        }
        for r in _search_sessions(query, identity, all_agents)
    ]

    results["canon"] = [
        {"path": r["path"], "content": r["content"], "reference": r["reference"]}
        for r in _search_canon(query, identity, all_agents)
    ]

    return results


__all__ = [
    "collect_timeline",
    "collect_current_state",
]
