"""Unified context search: routes to memory, knowledge, bridge, provider chats, canon."""

import contextlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from space.apps.context.lib import canon
from space.lib import providers
from space.os import bridge, knowledge, memory

log = logging.getLogger(__name__)

_MAX_SEARCH_LEN = 256


def _validate_search_term(term: str) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    max_len = _MAX_SEARCH_LEN
    if len(term) > max_len:
        raise ValueError(f"Search term too long (max {max_len} chars, got {len(term)})")


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
        for r in _search_provider_chats(query, identity, all_agents)
    ]

    results["canon"] = [
        {
            "path": r["path"],
            "content": r["content"],
            "reference": r["reference"],
        }
        for r in canon.search(query)
    ]

    return results
