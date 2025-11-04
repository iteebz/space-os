"""Context API: search across 5 domains (bridge, memory, knowledge, canon, sessions)."""

from space.os.context.api import bridge, canon, knowledge, memory, sessions


def collect_timeline(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Unified timeline: evolution across all sources.

    Memory is only included if --as <identity> is specified (private working memory).
    """
    _validate_search_term(query)
    seen = set()
    timeline = []

    if identity:
        for result in memory.search(query, identity, all_agents):
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

    for result in knowledge.search(query, identity, all_agents):
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

    for result in bridge.search(query, identity, all_agents):
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

    for result in sessions.search(query, identity, all_agents):
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

    for result in canon.search(query, identity, all_agents):
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
            for r in memory.search(query, identity, all_agents)
        ]

    results["knowledge"] = [
        {
            "domain": r["domain"],
            "content": r["content"],
            "contributor": r["contributor"],
            "reference": r["reference"],
        }
        for r in knowledge.search(query, identity, all_agents)
    ]

    results["bridge"] = [
        {
            "channel": r["channel_name"],
            "sender": r["sender"],
            "content": r["content"],
            "reference": r["reference"],
        }
        for r in bridge.search(query, identity, all_agents)
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
        for r in sessions.search(query, identity, all_agents)
    ]

    results["canon"] = [
        {"path": r["path"], "content": r["content"], "reference": r["reference"]}
        for r in canon.search(query, identity, all_agents)
    ]

    return results


MAX_SEARCH_LEN = 256


def _get_max_search_len() -> int:
    """Return maximum allowed search length."""
    return MAX_SEARCH_LEN


def _validate_search_term(term: str) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    max_len = _get_max_search_len()
    if len(term) > max_len:
        raise ValueError(f"Search term too long (max {max_len} chars, got {len(term)})")


__all__ = [
    "bridge",
    "memory",
    "knowledge",
    "canon",
    "sessions",
    "collect_timeline",
    "collect_current_state",
]
