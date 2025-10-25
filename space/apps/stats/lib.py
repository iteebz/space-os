from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from space.os import db
from space.os.core.spawn import db as spawn_db
from space.os.db import query_builders as qb
from space.os.db.registries import DB_REGISTRY_MAP
from space.os.lib import format as fmt
from space.os.lib import paths

from .models import (
    AgentStats,
    BridgeStats,
    EventsStats,
    KnowledgeStats,
    LeaderboardEntry,
    MemoryStats,
    SpaceStats,
    SpawnStats,
)

logger = logging.getLogger(__name__)

VALID_TABLES = {"messages", "memories", "knowledge", "events", "channels", "agents"}
VALID_COLUMNS = {
    "agent_id",
    "channel_id",
    "topic",
    "domain",
    "archived_at",
    "event_type",
    "timestamp",
}


def _validate_identifier(identifier: str, valid_set: set[str]) -> None:
    if identifier not in valid_set:
        raise ValueError(f"Invalid identifier: {identifier}")


def _get_columns_safe(conn: sqlite3.Connection, table: str) -> list[str]:
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}")
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def _get_agent_names_map() -> dict[str, str]:
    try:
        with spawn_db.connect() as reg_conn:
            return {row[0]: row[1] for row in reg_conn.execute("SELECT agent_id, name FROM agents")}
    except Exception as exc:
        logger.error(f"Failed to fetch agent names: {exc}")
        raise ValueError(f"Critical: unable to fetch agent registry: {exc}") from exc


def _discover_all_agent_ids(registered_ids: set[str], include_archived: bool = False) -> set[str]:
    """Discover all unique agent_ids across all activity tables and spawn_db."""
    from space.os.core.spawn import db as spawn_db

    all_agent_ids = set(registered_ids)

    if include_archived:
        try:
            with spawn_db.connect() as reg_conn:
                for row in reg_conn.execute(
                    "SELECT agent_id FROM agents WHERE archived_at IS NOT NULL"
                ):
                    all_agent_ids.add(row[0])
        except Exception as exc:
            logger.warning(f"Failed to discover archived agents: {exc}")

    dbs = [
        (paths.space_data() / "bridge.db", "messages"),
        (paths.space_data() / "memory.db", "memories"),
        (paths.space_data() / "knowledge.db", "knowledge"),
        (paths.space_data() / "events.db", "events"),
    ]

    for db_path, table in dbs:
        if db_path.exists():
            registry_name = DB_REGISTRY_MAP.get(db_path.name)
            if registry_name:
                try:
                    _validate_identifier(table, VALID_TABLES)
                    with db.ensure(registry_name) as conn:
                        columns = _get_columns_safe(conn, table)
                        if "agent_id" in columns:
                            for row in conn.execute(
                                f"SELECT DISTINCT agent_id FROM {table} WHERE agent_id IS NOT NULL"
                            ):
                                all_agent_ids.add(row[0])
                except Exception as exc:
                    logger.warning(f"Failed to discover agents from {db_path.name}:{table}: {exc}")

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

    registry_name = DB_REGISTRY_MAP.get(db_path.name)
    if not registry_name:
        return 0, 0, 0, None, []

    try:
        _validate_identifier(table_name, VALID_TABLES)
        if topic_column:
            _validate_identifier(topic_column, VALID_COLUMNS)
        if leaderboard_column:
            _validate_identifier(leaderboard_column, VALID_COLUMNS)
    except ValueError as e:
        logger.error(f"Invalid identifier in stats query: {e}")
        return 0, 0, 0, None, []

    with db.ensure(registry_name) as conn:
        columns = _get_columns_safe(conn, table_name)

        has_archived_at = "archived_at" in columns

        total = qb.count_table(conn, table_name)

        if has_archived_at:
            active = qb.count_active(conn, table_name)
            archived = qb.count_archived(conn, table_name)
        else:
            active = total
            archived = 0

        topics_or_channels = None
        if topic_column and topic_column in columns:
            topics_or_channels = (
                len(
                    qb.select_distinct(
                        conn, table_name, topic_column, include_archived=not has_archived_at
                    )
                )
                if has_archived_at
                else len(qb.select_distinct(conn, table_name, topic_column, include_archived=True))
            )

        leaderboard = []
        if leaderboard_column and leaderboard_column in columns:
            query = f"SELECT {leaderboard_column}, COUNT(*) as count FROM {table_name} GROUP BY {leaderboard_column} ORDER BY count DESC"
            params = ()
            if limit:
                query += " LIMIT ?"
                params = (limit,)
            count_rows = conn.execute(query, params).fetchall()
            agent_names_map = _get_agent_names_map()
            leaderboard = [
                LeaderboardEntry(identity=agent_names_map.get(row[0], row[0]), count=row[1])
                for row in count_rows
            ]

    return total, active, archived, topics_or_channels, leaderboard


def bridge_stats(limit: int = None) -> BridgeStats:
    db_path = paths.space_data() / "bridge.db"
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
    db_path = paths.space_data() / "memory.db"
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
    db_path = paths.space_data() / "knowledge.db"
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
    try:
        with spawn_db.connect() as reg_conn:
            where_clause = "" if include_archived else "WHERE archived_at IS NULL"
            agent_ids = {
                row[0] for row in reg_conn.execute(f"SELECT agent_id FROM agents {where_clause}")
            }
    except Exception as exc:
        logger.error(f"Failed to fetch registered agents: {exc}")
        agent_ids = set()

    agent_ids_from_all_tables = _discover_all_agent_ids(
        agent_ids, include_archived=include_archived
    )

    if not agent_ids_from_all_tables:
        return None

    agent_names_map = _get_agent_names_map()
    data_dir = paths.space_data()

    agent_stats_map = {
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
            data_dir / "bridge.db",
            [
                ("SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id", "msgs"),
                (
                    "SELECT agent_id, GROUP_CONCAT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL GROUP BY agent_id",
                    "channels",
                ),
            ],
        ),
        (
            data_dir / "memory.db",
            [
                ("SELECT agent_id, COUNT(*) FROM memories GROUP BY agent_id", "mems"),
            ],
        ),
        (
            data_dir / "knowledge.db",
            [
                ("SELECT agent_id, COUNT(*) FROM knowledge GROUP BY agent_id", "knowledge"),
            ],
        ),
        (
            data_dir / "events.db",
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

    for db_path, query_list in queries:
        if not db_path.exists():
            continue
        registry_name = DB_REGISTRY_MAP.get(db_path.name)
        if not registry_name:
            continue
        try:
            with db.ensure(registry_name) as conn:
                for sql, field in query_list:
                    try:
                        for row in conn.execute(sql):
                            agent_id = row[0]
                            if agent_id not in agent_stats_map:
                                continue
                            if field == "channels":
                                agent_stats_map[agent_id][field] = (
                                    row[1].split(",") if row[1] else []
                                )
                            elif field == "last_active":
                                agent_stats_map[agent_id][field] = str(row[1])
                            else:
                                agent_stats_map[agent_id][field] = row[1]
                    except Exception as exc:
                        logger.warning(f"Query failed for {field}: {exc}")
        except Exception as exc:
            logger.warning(f"Failed to connect to {db_path.name}: {exc}")

    active_polls_map = {}
    try:
        from space.os.core.bridge import db as bridge_db

        polls = bridge_db.get_active_polls()
        for poll in polls:
            agent_id = poll.get("agent_id")
            channel_id = poll.get("channel_id")
            if agent_id and channel_id:
                channel_name = bridge_db.get_channel_name(channel_id)
                if agent_id not in active_polls_map:
                    active_polls_map[agent_id] = []
                if channel_name:
                    active_polls_map[agent_id].append(channel_name)
    except Exception as exc:
        logger.warning(f"Failed to fetch active polls: {exc}")

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
            last_active_human=fmt.humanize_timestamp(data.get("last_active"))
            if data.get("last_active")
            else None,
            active_polls=active_polls_map.get(agent_id),
        )
        for agent_id, data in agent_stats_map.items()
    ]

    agents.sort(key=lambda a: a.last_active or "0", reverse=True)
    return agents[:limit] if limit else agents


def spawn_stats() -> SpawnStats:
    db_path = paths.space_data() / "spawn.db"
    if not db_path.exists():
        return SpawnStats(available=False)

    try:
        with db.ensure("spawn") as conn:
            agent_count = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
            hashes = conn.execute("SELECT COUNT(*) FROM constitutions").fetchone()[0]

        return SpawnStats(available=True, total=agent_count, agents=agent_count, hashes=hashes)
    except Exception as exc:
        logger.error(f"Failed to fetch spawn stats: {exc}")
        return SpawnStats(available=False)


def events_stats() -> EventsStats:
    db_path = paths.space_data() / "events.db"
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
