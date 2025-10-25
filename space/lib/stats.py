from __future__ import annotations

import logging

from space.core import bridge, knowledge, memory, spawn
from space.lib import format as fmt
from space.lib.models import (
    AgentStats,
    BridgeStats,
    KnowledgeStats,
    LeaderboardEntry,
    MemoryStats,
    SpaceStats,
    SpawnStats,
)

logger = logging.getLogger(__name__)


def _build_leaderboard(
    agent_counts: list[dict], limit: int | None = None
) -> list[LeaderboardEntry]:
    """Build leaderboard from agent_id -> count mapping."""
    names = spawn.api.agent_identities()
    entries = [
        LeaderboardEntry(
            identity=names.get(item["agent_id"], item["agent_id"]), count=item["count"]
        )
        for item in agent_counts
    ]
    return entries[:limit] if limit else entries


def bridge_stats(limit: int = None) -> BridgeStats:
    try:
        stats_data = bridge.api.stats()

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
            notes=stats_data.get("notes", 0),
            message_leaderboard=msg_leaderboard,
        )
    except Exception as exc:
        logger.error(f"Failed to fetch bridge stats: {exc}")
        return BridgeStats(available=False)


def memory_stats(limit: int = None) -> MemoryStats:
    try:
        stats_data = memory.api.stats()

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
        stats_data = knowledge.api.stats()

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
        agent_names = spawn.api.agent_identities()
        archived_agents = spawn.api.archived_agents()

        bridge_data = bridge.api.stats()
        memory_data = memory.api.stats()
        knowledge_data = knowledge.api.stats()

        agent_map = {
            agent_id: {
                "identity": name,
                "msgs": 0,
                "mems": 0,
                "knowledge": 0,
            }
            for agent_id, name in agent_names.items()
        }

        for item in bridge_data.get("messages", {}).get("by_agent", []):
            agent_id = item["agent_id"]
            if agent_id not in agent_map:
                agent_map[agent_id] = {
                    "identity": agent_names.get(agent_id, agent_id),
                    "msgs": 0,
                    "mems": 0,
                    "knowledge": 0,
                }
            agent_map[agent_id]["msgs"] = item["count"]

        for item in memory_data.get("mem_by_agent", []):
            agent_id = item["agent_id"]
            if agent_id not in agent_map:
                agent_map[agent_id] = {
                    "identity": agent_names.get(agent_id, agent_id),
                    "msgs": 0,
                    "mems": 0,
                    "knowledge": 0,
                }
            agent_map[agent_id]["mems"] = item["count"]

        for item in knowledge_data.get("know_by_agent", []):
            agent_id = item["agent_id"]
            if agent_id not in agent_map:
                agent_map[agent_id] = {
                    "identity": agent_names.get(agent_id, agent_id),
                    "msgs": 0,
                    "mems": 0,
                    "knowledge": 0,
                }
            agent_map[agent_id]["knowledge"] = item["count"]

        events_by_agent = {
            item["agent_id"]: item for item in bridge_data.get("events", {}).get("by_agent", [])
        }

        for agent_id in events_by_agent:
            if agent_id not in agent_map:
                agent_map[agent_id] = {
                    "identity": agent_names.get(agent_id, agent_id),
                    "msgs": 0,
                    "mems": 0,
                    "knowledge": 0,
                }

        result = [
            AgentStats(
                agent_id=agent_id,
                identity=data["identity"],
                events=events_by_agent.get(agent_id, {}).get("events", 0),
                spawns=events_by_agent.get(agent_id, {}).get("spawns", 0),
                msgs=data["msgs"],
                mems=data["mems"],
                knowledge=data["knowledge"],
                channels=[],
                last_active=events_by_agent.get(agent_id, {}).get("last_active"),
                last_active_human=fmt.humanize_timestamp(
                    events_by_agent.get(agent_id, {}).get("last_active")
                )
                if events_by_agent.get(agent_id, {}).get("last_active")
                else None,
            )
            for agent_id, data in agent_map.items()
            if show_all or agent_id not in archived_agents
        ]

        result.sort(key=lambda a: a.last_active or "0", reverse=True)
        return result[:limit] if limit else result
    except Exception as exc:
        logger.error(f"Failed to fetch agent stats: {exc}")
        return None


def spawn_stats() -> SpawnStats:
    try:
        stats_data = spawn.api.stats()
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
