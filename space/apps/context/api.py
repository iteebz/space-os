"""Unified context search: routes to memory, knowledge, bridge, provider chats, canon."""

import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from space.apps import canon
from space.lib import providers, store
from space.os import spawn

log = logging.getLogger(__name__)

MAX_SEARCH_LEN = 256


def _get_max_search_len() -> int:
    """Return maximum allowed search length."""
    return MAX_SEARCH_LEN


def _validate_search_term(term: str) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    max_len = _get_max_search_len()
    if len(term) > max_len:
        raise ValueError(f"Search term too long (max {max_len} chars, got {len(term)})")


def _search_memory(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search memory entries by query, optionally filtering by agent."""
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


def _search_knowledge(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search knowledge entries by query, optionally filtering by agent."""
    results = []
    with store.ensure("knowledge") as conn:
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


def _search_bridge(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search bridge messages by query, optionally filtering by agent."""
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


def _search_provider_chats(
    query: str, identity: str | None = None, all_agents: bool = False
) -> list[dict]:
    """Search provider chat logs directly (stateless, ephemeral discovery)."""
    results = []
    query_lower = query.lower()

    def _discover_and_search_provider(cli_name: str) -> list[dict]:
        """Discover and search a single provider's chats."""
        provider_results = []
        try:
            provider = getattr(providers, cli_name)()
            sessions = provider.discover_sessions()

            for session in sessions:
                try:
                    file_path = Path(session["file_path"])
                    if not file_path.exists():
                        continue

                    session_id = session["session_id"]
                    messages = provider.parse_messages(file_path)

                    for msg in messages:
                        content = msg.get("content", "")
                        if query_lower in content.lower():
                            provider_results.append(
                                {
                                    "source": "provider-chats",
                                    "cli": cli_name,
                                    "session_id": session_id,
                                    "identity": None,
                                    "role": msg.get("role"),
                                    "text": content,
                                    "timestamp": msg.get("timestamp"),
                                    "reference": f"provider-chats:{cli_name}:{session_id}",
                                }
                            )
                except Exception:
                    pass

        except Exception:
            pass

        return provider_results

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_discover_and_search_provider, cli): cli
            for cli in ("claude", "codex", "gemini")
        }
        for future in as_completed(futures):
            with contextlib.suppress(Exception):
                results.extend(future.result())

    return results


def collect_timeline(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Unified timeline: evolution across all sources."""
    _validate_search_term(query)
    seen = set()
    timeline = []

    for result in _search_memory(query, identity, all_agents):
        key = (result["source"], result.get("memory_id"))
        if key not in seen:
            seen.add(key)
            timeline.append(
                {
                    "source": result["source"],
                    "type": result["topic"],
                    "identity": result["identity"],
                    "data": result["message"],
                    "timestamp": result["timestamp"],
                    "reference": result["reference"],
                }
            )

    for result in _search_knowledge(query, identity, all_agents):
        key = (result["source"], result.get("knowledge_id"))
        if key not in seen:
            seen.add(key)
            timeline.append(
                {
                    "source": result["source"],
                    "type": result["domain"],
                    "identity": result["contributor"],
                    "data": result["content"],
                    "timestamp": result["timestamp"],
                    "reference": result["reference"],
                }
            )

    for result in _search_bridge(query, identity, all_agents):
        key = (result["source"], result.get("message_id"))
        if key not in seen:
            seen.add(key)
            timeline.append(
                {
                    "source": result["source"],
                    "type": result["channel_name"],
                    "identity": result["sender"],
                    "data": result["content"],
                    "timestamp": result["timestamp"],
                    "reference": result["reference"],
                }
            )

    for result in _search_provider_chats(query, identity, all_agents):
        key = (result["source"], result.get("session_id"))
        if key not in seen:
            seen.add(key)
            timeline.append(
                {
                    "source": result["source"],
                    "type": result["cli"],
                    "identity": result["identity"],
                    "data": result["text"],
                    "timestamp": result["timestamp"],
                    "reference": result["reference"],
                }
            )

    for result in canon.search(query):
        key = (result["source"], result.get("path"))
        if key not in seen:
            seen.add(key)
            timeline.append(
                {
                    "source": result["source"],
                    "type": "documentation",
                    "identity": None,
                    "data": result["content"],
                    "timestamp": 0,
                    "reference": result["reference"],
                }
            )

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline[-10:]


def collect_current_state(query: str, identity: str | None, all_agents: bool) -> dict:
    """Unified state: current entries across all sources."""
    results = {"memory": [], "knowledge": [], "bridge": [], "provider_chats": [], "canon": []}

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
        for r in _search_provider_chats(query, identity, all_agents)
    ]

    results["canon"] = [
        {"path": r["path"], "content": r["content"], "reference": r["reference"]}
        for r in canon.search(query)
    ]

    return results
