from __future__ import annotations

from dataclasses import dataclass

from . import db, paths
from .display import humanize_timestamp


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


@dataclass
class AgentStats:
    agent_id: str
    agent_name: str
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
class SpaceStats:
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    spawn: SpawnStats
    agents: list[AgentStats] | None = None


def _get_agent_names_map() -> dict[str, str]:
    from ..spawn import registry

    with registry.get_db() as reg_conn:
        return {row[0]: row[1] for row in reg_conn.execute("SELECT id, name FROM agents")}


def _get_common_db_stats(
    db_path: Path,
    table_name: str,
    topic_column: str | None = None,
    leaderboard_column: str | None = None,
    limit: int | None = None,
) -> tuple[int, int, int, int | None, list[LeaderboardEntry]]:
    if not db_path.exists():
        return 0, 0, 0, None, []

    with db.connect(db_path) as conn:
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

    with db.connect(db_path) as conn:
        channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL"
        ).fetchone()[0]
        active_channels = conn.execute(
            "SELECT COUNT(DISTINCT id) FROM channels WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_channels = conn.execute(
            "SELECT COUNT(DISTINCT id) FROM channels WHERE archived_at IS NOT NULL"
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


def agent_stats(limit: int = None) -> list[AgentStats] | None:
    agent_names_map = _get_agent_names_map()

    bridge_db = paths.dot_space() / "bridge.db"
    mem_db = paths.dot_space() / "memory.db"
    know_db = paths.dot_space() / "knowledge.db"

    if not bridge_db.exists():
        return None

    identities = {}

    with db.connect(bridge_db) as conn:
        for agent_uuid, msgs_count in conn.execute(
            "SELECT agent_id, COUNT(*) as msgs FROM messages GROUP BY agent_id"
        ):
            identities[agent_uuid] = {
                "agent_name": agent_names_map.get(agent_uuid, agent_uuid),
                "msgs": msgs_count,
                "last_active": None,
                "mems": 0,
                "knowledge": 0,
                "spawns": 0,
                "channels": [],
            }

        for agent_uuid, channels_str in conn.execute(
            "SELECT agent_id, GROUP_CONCAT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL GROUP BY agent_id"
        ):
            channels = channels_str.split(",") if channels_str else []
            if agent_uuid in identities:
                identities[agent_uuid]["channels"] = channels

    if mem_db.exists():
        with db.connect(mem_db) as conn:
            for agent_uuid, mems_count in conn.execute(
                "SELECT agent_id, COUNT(*) FROM memories GROUP BY agent_id"
            ):
                if agent_uuid in identities:
                    identities[agent_uuid]["mems"] = mems_count

    if know_db.exists():
        with db.connect(know_db) as conn:
            for agent_uuid, knowledge_count in conn.execute(
                "SELECT agent_id, COUNT(*) FROM knowledge GROUP BY agent_id"
            ):
                if agent_uuid in identities:
                    identities[agent_uuid]["knowledge"] = knowledge_count

    events_db = paths.space_root() / "events.db"
    if events_db.exists():
        with db.connect(events_db) as conn:
            for agent_uuid, spawns_count in conn.execute(
                "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id"
            ):
                if agent_uuid in identities:
                    identities[agent_uuid]["spawns"] = spawns_count

            for agent_uuid, last_active_timestamp in conn.execute(
                "SELECT agent_id, MAX(timestamp) FROM events WHERE agent_id IS NOT NULL GROUP BY agent_id"
            ):
                if agent_uuid in identities:
                    identities[agent_uuid]["last_active"] = str(last_active_timestamp)

    agents = [
        AgentStats(
            agent_id=agent_uuid,
            agent_name=data["agent_name"],
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
        for agent_uuid, data in identities.items()
    ]

    agents.sort(key=lambda a: a.msgs, reverse=True)
    return agents[:limit] if limit else agents


def spawn_stats() -> SpawnStats:
    db_path = paths.dot_space() / "spawn.db"
    if not db_path.exists():
        return SpawnStats(available=False)

    with db.connect(db_path) as conn:
        agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

    return SpawnStats(available=True, total=agents, agents=agents, hashes=hashes)


def collect(limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
        spawn=spawn_stats(),
        agents=agent_stats(limit=limit),
    )
