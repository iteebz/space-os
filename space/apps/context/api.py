"""Context API: search across 5 domains (bridge, memory, knowledge, canon, sessions)."""

from space.os import bridge, canon, knowledge, memory, sessions


def _validate_search_term(term: str, max_len: int = 256) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    if len(term) > max_len:
        raise ValueError(f"Search term too long (max {max_len} chars, got {len(term)})")


def collect_timeline(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Unified timeline: evolution across all sources.

    Memory is only included if --as <identity> is specified (private working memory).
    """
    _validate_search_term(query, max_len=256)
    seen = set()
    timeline = []

    if identity:
        for result in memory.api.search(query, identity, all_agents):
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

    for result in knowledge.api.search(query, identity, all_agents):
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

    for result in bridge.api.search(query, identity, all_agents):
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

    for result in sessions.api.search(query, identity, all_agents):
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

    for result in canon.api.search(query, identity, all_agents):
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
    results = {"memory": [], "knowledge": [], "bridge": [], "sessions": [], "canon": []}

    if identity:
        results["memory"] = [
            {
                "identity": r["identity"],
                "topic": r["topic"],
                "message": r["message"],
                "reference": r["reference"],
            }
            for r in memory.api.search(query, identity, all_agents)
        ]

    results["knowledge"] = [
        {
            "domain": r["domain"],
            "content": r["content"],
            "contributor": r["contributor"],
            "reference": r["reference"],
        }
        for r in knowledge.api.search(query, identity, all_agents)
    ]

    results["bridge"] = [
        {
            "channel": r["channel_name"],
            "sender": r["sender"],
            "content": r["content"],
            "reference": r["reference"],
        }
        for r in bridge.api.search(query, identity, all_agents)
    ]

    results["sessions"] = [
        {
            "cli": r["cli"],
            "session_id": r["session_id"],
            "identity": r["identity"],
            "role": r["role"],
            "text": r["text"],
            "reference": r["reference"],
        }
        for r in sessions.api.search(query, identity, all_agents)
    ]

    results["canon"] = [
        {"path": r["path"], "content": r["content"], "reference": r["reference"]}
        for r in canon.api.search(query, identity, all_agents)
    ]

    return results


__all__ = [
    "collect_timeline",
    "collect_current_state",
]
