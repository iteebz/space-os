from __future__ import annotations

import logging

from space.lib import format as fmt
from space.lib import store

from .models import (
    AgentStats,
    BridgeStats,
    KnowledgeStats,
    LeaderboardEntry,
    MemoryStats,
    SpaceStats,
    SpawnStats,
)

logger = logging.getLogger(__name__)


def _get_agent_identities() -> dict[str, str]:
    """Get agent_id -> identity mapping."""
    from space.core import db

    with db.connect() as conn:
        rows = conn.execute("SELECT agent_id, identity FROM agents").fetchall()
        return {row[0]: row[1] for row in rows}


def _get_archived_agents() -> set[str]:
    """Get set of archived agent IDs."""
    from space.core import db

    with db.connect() as conn:
        rows = conn.execute("SELECT agent_id FROM agents WHERE archived_at IS NOT NULL").fetchall()
        return {row[0] for row in rows}


def _build_leaderboard(
    agent_counts: list[dict], limit: int | None = None
) -> list[LeaderboardEntry]:
    """Build leaderboard from agent_id -> count mapping."""
    names = _get_agent_identities()
    entries = [
        LeaderboardEntry(
            identity=names.get(item["agent_id"], item["agent_id"]), count=item["count"]
        )
        for item in agent_counts
    ]
    return entries[:limit] if limit else entries


def _get_memory_stats() -> dict:
    """Get memory statistics."""
    with store.ensure("memory") as conn:
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM memories WHERE archived_at IS NULL").fetchone()[
            0
        ]
        archived = total - active

        topics = conn.execute(
            "SELECT COUNT(DISTINCT topic) FROM memories WHERE archived_at IS NULL"
        ).fetchone()[0]

        mem_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM memories GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": topics,
        "mem_by_agent": [{"agent_id": row[0], "count": row[1]} for row in mem_by_agent],
    }


def _get_knowledge_stats() -> dict:
    """Get knowledge statistics."""
    with store.ensure("knowledge") as conn:
        total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived = total - active

        domains = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]

        know_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM knowledge GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    return {
        "total": total,
        "active": active,
        "archived": archived,
        "topics": domains,
        "know_by_agent": [{"agent_id": row[0], "count": row[1]} for row in know_by_agent],
    }


def _get_bridge_stats() -> dict:
    """Get bridge statistics: messages, channels, and events by agent."""
    with store.ensure("bridge") as conn:
        total_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        archived_msgs = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel_id IN (SELECT channel_id FROM channels WHERE archived_at IS NOT NULL)"
        ).fetchone()[0]
        active_msgs = total_msgs - archived_msgs

        total_channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        active_channels = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_channels = total_channels - active_channels

        distinct_channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL"
        ).fetchone()[0]

        msg_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM messages GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    try:
        with store.ensure("events") as conn:
            rows = conn.execute(
                "SELECT agent_id, event_type, timestamp FROM events ORDER BY timestamp"
            ).fetchall()

            agent_events: dict[str, dict] = {}
            total_events = len(rows)

            for row in rows:
                agent_id = row[0]
                event_type = row[1]
                timestamp = row[2]

                if agent_id not in agent_events:
                    agent_events[agent_id] = {
                        "events": 0,
                        "spawns": 0,
                        "last_active": None,
                    }

                agent_events[agent_id]["events"] += 1
                if event_type == "session_start":
                    agent_events[agent_id]["spawns"] += 1
                agent_events[agent_id]["last_active"] = timestamp

            events_by_agent = [
                {"agent_id": agent_id, **data} for agent_id, data in agent_events.items()
            ]
    except Exception:
        total_events = 0
        events_by_agent = []

    return {
        "messages": {
            "total": total_msgs,
            "active": active_msgs,
            "archived": archived_msgs,
            "by_agent": [{"agent_id": row[0], "count": row[1]} for row in msg_by_agent],
        },
        "channels": {
            "total": distinct_channels,
            "active": active_channels,
            "archived": archived_channels,
        },
        "events": {
            "total": total_events,
            "by_agent": events_by_agent,
        },
    }


def _get_spawn_stats() -> dict:
    """Get spawn statistics."""
    from space.core import db

    with db.connect() as conn:
        total_agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        active_agents = conn.execute(
            "SELECT COUNT(*) FROM agents WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_agents = total_agents - active_agents

        hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

    return {
        "total": total_agents,
        "active": active_agents,
        "archived": archived_agents,
        "hashes": hashes,
    }


def bridge_stats(limit: int = None) -> BridgeStats:
    try:
        stats_data = _get_bridge_stats()

        msg_data = stats_data.get("messages", {})
        msg_leaderboard = _build_leaderboard(msg_data.get("by_agent", []), limit=limit)

        channels_data = stats_data.get("channels", {})

        return BridgeStats(
            available=True,
            total=msg_data.get("total", 0),
            active=msg_data.get("active", 0),
            archived=msg_data.get("archived", 0),
            channels=channels_data.get("total", 0),
            active_channels=channels_data.get("active", 0),
            archived_channels=channels_data.get("archived", 0),
            message_leaderboard=msg_leaderboard,
        )
    except Exception as exc:
        logger.error(f"Failed to fetch bridge stats: {exc}")
        return BridgeStats(available=False)


def memory_stats(limit: int = None) -> MemoryStats:
    try:
        stats_data = _get_memory_stats()

        leaderboard = _build_leaderboard(stats_data.pop("mem_by_agent", []), limit=limit)

        return MemoryStats(
            available=True,
            leaderboard=leaderboard,
            **stats_data,
        )
    except Exception as exc:
        logger.error(f"Failed to fetch memory stats: {exc}")
        return MemoryStats(available=False)


def knowledge_stats(limit: int = None) -> KnowledgeStats:
    try:
        stats_data = _get_knowledge_stats()

        leaderboard = _build_leaderboard(stats_data.pop("know_by_agent", []), limit=limit)

        return KnowledgeStats(
            available=True,
            leaderboard=leaderboard,
            **stats_data,
        )
    except Exception as exc:
        logger.error(f"Failed to fetch knowledge stats: {exc}")
        return KnowledgeStats(available=False)


def agent_stats(limit: int = None, show_all: bool = False) -> list[AgentStats] | None:
    try:
        agent_identities_map = _get_agent_identities()
        archived_set = _get_archived_agents()

        agent_map = {
            agent_id: {
                "identity": identity,
                "msgs": 0,
                "mems": 0,
                "knowledge": 0,
                "events": 0,
                "spawns": 0,
                "last_active": None,
            }
            for agent_id, identity in agent_identities_map.items()
        }

        bridge_data = _get_bridge_stats()
        memory_data = _get_memory_stats()
        knowledge_data = _get_knowledge_stats()

        for item in bridge_data.get("messages", {}).get("by_agent", []):
            agent_id = item["agent_id"]
            if agent_id in agent_map:
                agent_map[agent_id]["msgs"] = item["count"]

        for item in bridge_data.get("events", {}).get("by_agent", []):
            agent_id = item["agent_id"]
            if agent_id in agent_map:
                agent_map[agent_id]["events"] = item.get("events", 0)
                agent_map[agent_id]["spawns"] = item.get("spawns", 0)
                agent_map[agent_id]["last_active"] = item.get("last_active")

        for item in memory_data.get("mem_by_agent", []):
            agent_id = item["agent_id"]
            if agent_id in agent_map:
                agent_map[agent_id]["mems"] = item["count"]

        for item in knowledge_data.get("know_by_agent", []):
            agent_id = item["agent_id"]
            if agent_id in agent_map:
                agent_map[agent_id]["knowledge"] = item["count"]

        result = [
            AgentStats(
                agent_id=agent_id,
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
            for agent_id, data in agent_map.items()
            if show_all or agent_id not in archived_set
        ]

        result.sort(key=lambda a: a.last_active or "0", reverse=True)
        return result[:limit] if limit else result
    except Exception as exc:
        logger.error(f"Failed to fetch agent stats: {exc}")
        return None


def spawn_stats() -> SpawnStats:
    try:
        stats_data = _get_spawn_stats()
        return SpawnStats(available=True, **stats_data)
    except Exception as exc:
        logger.error(f"Failed to fetch spawn stats: {exc}")
        return SpawnStats(available=False)


def collect(limit: int = None, agent_limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
        spawn=spawn_stats(),
        agents=agent_stats(limit=agent_limit),
    )
