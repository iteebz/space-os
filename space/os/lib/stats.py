from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from space.os import db

from . import paths
from .format import humanize_timestamp


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


@dataclass
class AgentStats:
    agent_id: str
    agent_name: str
    events: int
    spawns: int
    msgs: int
    mems: int
    knowledge: int
    channels: list[str]
    last_active: str | None
    last_active_human: str | None = None


@dataclass
class BridgeStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    channels: int = 0
    active_channels: int = 0
    archived_channels: int = 0
    notes: int = 0
    message_leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class MemoryStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class KnowledgeStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class SpawnStats:
    available: bool
    total: int = 0
    agents: int = 0
    hashes: int = 0


@dataclass
class EventsStats:
    available: bool
    total: int = 0


@dataclass
class SpaceStats:
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    spawn: SpawnStats
    events: EventsStats
    agents: list[AgentStats] | None = None


def _get_agent_names_map() -> dict[str, str]:
    from ..spawn import db as spawn_db

    with spawn_db.connect() as reg_conn:
        return {row[0]: row[1] for row in reg_conn.execute("SELECT agent_id, name FROM agents")}


def _discover_all_agent_ids(registered_ids: set[str], include_archived: bool = False) -> set[str]:
    """Discover all unique agent_ids across all activity tables and spawn_db."""
    from ..spawn import db as spawn_db

    all_agent_ids = set(registered_ids)

    if include_archived:
        with spawn_db.connect() as reg_conn:
            for row in reg_conn.execute("SELECT agent_id FROM agents WHERE archived_at IS NOT NULL"):
                all_agent_ids.add(row[0])

    dbs = [
        (paths.dot_space() / "bridge.db", "messages"),
        (paths.dot_space() / "memory.db", "memories"),
        (paths.dot_space() / "knowledge.db", "knowledge"),
        (paths.dot_space() / "events.db", "events"),
    ]

    registry_map = {"bridge.db": "bridge", "memory.db": "memory", "knowledge.db": "knowledge", "events.db": "events"}
    for db_path, table in dbs:
        if db_path.exists():
            registry_name = registry_map.get(db_path.name)
            if registry_name:
                with db.ensure(registry_name) as conn:
                    for row in conn.execute(
                        f"SELECT DISTINCT agent_id FROM {table} WHERE agent_id IS NOT NULL"
                    ):
                        all_agent_ids.add(row[0])

    return all_agent_ids


def _get_common_db_stats(
    db_path: Path,
    table_name: str,
    topic_column: str | None = None,
    leaderboard_column: str | None = None,
    limit: int | None = None,
) -> tuple[int, int, int, int | None, list[LeaderboardEntry]]:
    if not db_path.exists():
        return 0, 0, 0, None, []

    registry_map = {"bridge.db": "bridge", "memory.db": "memory", "knowledge.db": "knowledge", "events.db": "events"}
    registry_name = registry_map.get(db_path.name)
    if not registry_name:
        return 0, 0, 0, None, []

    with db.ensure(registry_name) as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row["name"] for row in cursor.fetchall()]

        has_archived_at = "archived_at" in columns

        total = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        if has_archived_at:
            active = conn.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE archived_at IS NULL"
            ).fetchone()[0]
            archived = conn.execute(
                f"SELECT COUNT(*) FROM {table_name} WHERE archived_at IS NOT NULL"
            ).fetchone()[0]
        else:
            active = total
            archived = 0

        topics_or_channels = None
        if topic_column:
            topics_or_channels = conn.execute(
                f"SELECT COUNT(DISTINCT {topic_column}) FROM {table_name} WHERE archived_at IS NULL"
            ).fetchone()[0]

        leaderboard = []
        if leaderboard_column:
            query = f"SELECT {leaderboard_column}, COUNT(*) as count FROM {table_name} GROUP BY {leaderboard_column} ORDER BY count DESC"
            if limit:
                rows = conn.execute(f"{query} LIMIT ?", (limit,)).fetchall()
            else:
                rows = conn.execute(query).fetchall()

            agent_names_map = _get_agent_names_map()
            leaderboard = [
                LeaderboardEntry(identity=agent_names_map.get(row[0], row[0]), count=row[1])
                for row in rows
            ]

    return total, active, archived, topics_or_channels, leaderboard


def bridge_stats(limit: int = None) -> BridgeStats:
    db_path = paths.dot_space() / "bridge.db"
    if not db_path.exists():
        return BridgeStats(available=False)

    total, active, archived, _, message_leaderboard = _get_common_db_stats(
        db_path,
        "messages",
        leaderboard_column="agent_id",
        limit=limit,
    )

    with db.ensure("bridge") as conn:
        channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL"
        ).fetchone()[0]
        active_channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM channels WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM channels WHERE archived_at IS NOT NULL"
        ).fetchone()[0]
        notes = conn.execute("SELECT COUNT(*) FROM notes WHERE channel_id IS NOT NULL").fetchone()[
            0
        ]

    return BridgeStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        channels=channels,
        active_channels=active_channels,
        archived_channels=archived_channels,
        notes=notes,
        message_leaderboard=message_leaderboard,
    )


def memory_stats(limit: int = None) -> MemoryStats:
    db_path = paths.dot_space() / "memory.db"
    if not db_path.exists():
        return MemoryStats(available=False)

    total, active, archived, topics, leaderboard = _get_common_db_stats(
        db_path,
        "memories",
        topic_column="topic",
        leaderboard_column="agent_id",
        limit=limit,
    )

    return MemoryStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def knowledge_stats(limit: int = None) -> KnowledgeStats:
    db_path = paths.dot_space() / "knowledge.db"
    if not db_path.exists():
        return KnowledgeStats(available=False)

    total, active, archived, topics, leaderboard = _get_common_db_stats(
        db_path,
        "knowledge",
        topic_column="domain",
        leaderboard_column="agent_id",
        limit=limit,
    )

    return KnowledgeStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def agent_stats(limit: int = None, include_archived: bool = False) -> list[AgentStats] | None:
    from ..spawn import db as spawn_db

    with spawn_db.connect() as reg_conn:
        where_clause = "" if include_archived else "WHERE archived_at IS NULL"
        agent_ids = {row[0] for row in reg_conn.execute(f"SELECT agent_id FROM agents {where_clause}")}

    agent_ids_from_all_tables = _discover_all_agent_ids(
        agent_ids, include_archived=include_archived
    )

    if not agent_ids_from_all_tables:
        return None

    agent_names_map = _get_agent_names_map()
    dot_space = paths.dot_space()

    identities = {
        agent_id: {
            "agent_name": agent_names_map.get(agent_id, agent_id),
            "events": 0,
            "msgs": 0,
            "last_active": None,
            "mems": 0,
            "knowledge": 0,
            "spawns": 0,
            "channels": [],
        }
        for agent_id in agent_ids_from_all_tables
    }

    queries = [
        (
            dot_space / "bridge.db",
            [
                ("SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id", "msgs"),
                (
                    "SELECT agent_id, GROUP_CONCAT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL GROUP BY agent_id",
                    "channels",
                ),
            ],
        ),
        (
            dot_space / "memory.db",
            [
                ("SELECT agent_id, COUNT(*) FROM memories GROUP BY agent_id", "mems"),
            ],
        ),
        (
            dot_space / "knowledge.db",
            [
                ("SELECT agent_id, COUNT(*) FROM knowledge GROUP BY agent_id", "knowledge"),
            ],
        ),
        (
            dot_space / "events.db",
            [
                ("SELECT agent_id, COUNT(*) FROM events GROUP BY agent_id", "events"),
                (
                    "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id",
                    "spawns",
                ),
                (
                    "SELECT agent_id, MAX(timestamp) FROM events WHERE agent_id IS NOT NULL GROUP BY agent_id",
                    "last_active",
                ),
            ],
        ),
    ]

    registry_map = {"bridge.db": "bridge", "memory.db": "memory", "knowledge.db": "knowledge", "events.db": "events"}
    for db_path, query_list in queries:
        if not db_path.exists():
            continue
        registry_name = registry_map.get(db_path.name)
        if not registry_name:
            continue
        with db.ensure(registry_name) as conn:
            for sql, field in query_list:
                for row in conn.execute(sql):
                    agent_id = row[0]
                    if agent_id not in identities:
                        continue
                    if field == "channels":
                        identities[agent_id][field] = row[1].split(",") if row[1] else []
                    elif field == "last_active":
                        identities[agent_id][field] = str(row[1])
                    else:
                        identities[agent_id][field] = row[1]

    agents = [
        AgentStats(
            agent_id=agent_id,
            agent_name=data["agent_name"],
            events=data["events"],
            spawns=data["spawns"],
            msgs=data["msgs"],
            mems=data["mems"],
            knowledge=data["knowledge"],
            channels=data.get("channels", []),
            last_active=data.get("last_active"),
            last_active_human=humanize_timestamp(data.get("last_active"))
            if data.get("last_active")
            else None,
        )
        for agent_id, data in identities.items()
    ]

    agents.sort(key=lambda a: a.last_active or "0", reverse=True)
    return agents[:limit] if limit else agents


def spawn_stats() -> SpawnStats:
    db_path = paths.dot_space() / "spawn.db"
    if not db_path.exists():
        return SpawnStats(available=False)

    with db.ensure("spawn") as conn:
        agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

    return SpawnStats(available=True, total=agents, agents=agents, hashes=hashes)


def events_stats() -> EventsStats:
    db_path = paths.dot_space() / "events.db"
    if not db_path.exists():
        return EventsStats(available=False)

    with db.ensure("events") as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    return EventsStats(available=True, total=total)


def collect(limit: int = None, agent_limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
        spawn=spawn_stats(),
        events=events_stats(),
        agents=agent_stats(limit=agent_limit),
    )
