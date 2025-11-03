from __future__ import annotations

import logging

from space.core.models import (
    AgentStats,
    BridgeStats,
    ChatStats,
    KnowledgeStats,
    MemoryStats,
    SpaceStats,
    SpawnStats,
)
from space.lib import format as fmt
from space.lib import store

logger = logging.getLogger(__name__)


def _get_agent_identities() -> dict[str, str]:
    """Get agent_id -> identity mapping."""
    from space.os import spawn

    return spawn.api.agent_identities()


def _get_archived_agents() -> set[str]:
    """Get set of archived agent IDs."""
    from space.os import spawn

    return spawn.api.archived_agents()


def _get_memory_stats() -> dict:
    """Get memory statistics."""
    from space.os import memory

    total, active, archived = memory.api.count_memories()
    with store.ensure("memory") as conn:
        topics = conn.execute(
            "SELECT COUNT(DISTINCT topic) FROM memories WHERE archived_at IS NULL"
        ).fetchone()[0]
        by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM memories GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()
    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": topics,
        "mem_by_agent": [{"agent_id": row[0], "count": row[1]} for row in by_agent],
    }


def _get_knowledge_stats() -> dict:
    """Get knowledge statistics."""
    from space.os import knowledge

    total, active, archived = knowledge.api.count_knowledge()
    with store.ensure("knowledge") as conn:
        topics = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]
        by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM knowledge GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()
    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": topics,
        "know_by_agent": [{"agent_id": row[0], "count": row[1]} for row in by_agent],
    }


def _aggregate_events(rows: list) -> tuple[int, list[dict]]:
    """Aggregate event rows into total and per-agent stats."""
    agent_events = {}
    for agent_id, event_type, timestamp in rows:
        if agent_id not in agent_events:
            agent_events[agent_id] = {"events": 0, "spawns": 0, "last_active": None}
        agent_events[agent_id]["events"] += 1
        if event_type == "session_start":
            agent_events[agent_id]["spawns"] += 1
        agent_events[agent_id]["last_active"] = timestamp
    return len(rows), [{"agent_id": aid, **data} for aid, data in agent_events.items()]


def _get_bridge_stats() -> dict:
    """Get bridge statistics: messages, channels, and events by agent."""
    from space.os import bridge

    total_msgs, active_msgs, archived_msgs = bridge.api.messaging.count_messages()
    distinct_channels, active_channels, archived_channels = bridge.api.channels.count_channels()

    with store.ensure("bridge") as conn:
        msg_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id ORDER BY COUNT(*) DESC"
        ).fetchall()

    total_events, events_by_agent = 0, []
    try:
        with store.ensure("events") as conn:
            rows = conn.execute(
                "SELECT agent_id, event_type, timestamp FROM events ORDER BY timestamp"
            ).fetchall()
            total_events, events_by_agent = _aggregate_events(rows)
    except Exception:
        pass

    return {
        "messages": {
            "total": total_msgs,
            "active": active_msgs,
            "archived": archived_msgs,
            "by_agent": [{"agent_id": aid, "count": cnt} for aid, cnt in msg_by_agent],
        },
        "channels": {
            "total": distinct_channels,
            "active": active_channels,
            "archived": archived_channels,
        },
        "events": {"total": total_events, "by_agent": events_by_agent},
    }


def _get_spawn_stats() -> dict:
    """Get spawn statistics."""
    from space.os import spawn

    return spawn.api.stats()


def _get_chat_stats() -> dict:
    """Get chat statistics from chats primitive."""
    from space.os import chats

    return chats.api.operations.get_stats()


def _safe_stats(fn, *args, **kwargs):
    """Safely call stats function, logging errors."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.error(f"Failed to fetch {fn.__name__}: {exc}")
        return None


def bridge_stats() -> BridgeStats:
    stats_data = _safe_stats(_get_bridge_stats)
    if not stats_data:
        return BridgeStats(available=False)

    msg_data = stats_data.get("messages", {})
    channels_data = stats_data.get("channels", {})

    return BridgeStats(
        available=True,
        total=msg_data.get("total", 0),
        active=msg_data.get("active", 0),
        archived=msg_data.get("archived", 0),
        channels=channels_data.get("total", 0),
        active_channels=channels_data.get("active", 0),
        archived_channels=channels_data.get("archived", 0),
    )


def memory_stats() -> MemoryStats:
    stats_data = _safe_stats(_get_memory_stats)
    if not stats_data:
        return MemoryStats(available=False)

    stats_data.pop("mem_by_agent", None)
    return MemoryStats(available=True, **stats_data)


def knowledge_stats() -> KnowledgeStats:
    stats_data = _safe_stats(_get_knowledge_stats)
    if not stats_data:
        return KnowledgeStats(available=False)

    stats_data.pop("know_by_agent", None)
    return KnowledgeStats(available=True, **stats_data)


def agent_stats(limit: int = None, show_all: bool = False) -> list[AgentStats] | None:
    try:
        agent_map = {
            aid: {
                "identity": name,
                "msgs": 0,
                "mems": 0,
                "knowledge": 0,
                "events": 0,
                "spawns": 0,
                "last_active": None,
            }
            for aid, name in _get_agent_identities().items()
        }
        archived_set = _get_archived_agents()

        bridge_data = _get_bridge_stats()
        memory_data = _get_memory_stats()
        knowledge_data = _get_knowledge_stats()

        data_sources = [
            (bridge_data.get("messages", {}).get("by_agent", []), "msgs", "count"),
            (bridge_data.get("events", {}).get("by_agent", []), None, None),
            (memory_data.get("mem_by_agent", []), "mems", "count"),
            (knowledge_data.get("know_by_agent", []), "knowledge", "count"),
        ]

        for items, field, key in data_sources:
            for item in items:
                if (aid := item["agent_id"]) in agent_map:
                    if field is None:
                        agent_map[aid].update(
                            {
                                "events": item.get("events", 0),
                                "spawns": item.get("spawns", 0),
                                "last_active": item.get("last_active"),
                            }
                        )
                    else:
                        agent_map[aid][field] = item[key]

        def to_agent_stats(aid, data):
            return AgentStats(
                agent_id=aid,
                identity=data["identity"],
                events=data["events"],
                spawns=data["spawns"],
                msgs=data["msgs"],
                mems=data["mems"],
                knowledge=data["knowledge"],
                channels=[],
                last_active=data["last_active"],
                last_active_human=fmt.humanize_timestamp(data["last_active"])
                if data["last_active"]
                else None,
            )

        result = [
            to_agent_stats(aid, data)
            for aid, data in agent_map.items()
            if show_all or aid not in archived_set
        ]
        result.sort(key=lambda a: a.last_active or "0", reverse=True)
        return result[:limit] if limit else result
    except Exception as exc:
        logger.error(f"Failed to fetch agent stats: {exc}")
        return None


def spawn_stats() -> SpawnStats:
    stats_data = _safe_stats(_get_spawn_stats)
    return SpawnStats(available=True, **stats_data) if stats_data else SpawnStats(available=False)


def chat_stats() -> ChatStats:
    stats_data = _safe_stats(_get_chat_stats)
    if not stats_data:
        return ChatStats(available=False)

    return ChatStats(
        available=True,
        total_chats=stats_data["total_chats"],
        total_messages=stats_data["total_messages"],
        total_tools_used=stats_data["total_tools_used"],
        input_tokens=stats_data["total_input_tokens"],
        output_tokens=stats_data["total_output_tokens"],
        by_provider=stats_data["by_provider"],
        by_agent=stats_data["by_agent"],
    )


def collect(agent_limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(),
        memory=memory_stats(),
        knowledge=knowledge_stats(),
        spawn=spawn_stats(),
        chats=chat_stats(),
        agents=agent_stats(limit=agent_limit),
    )
