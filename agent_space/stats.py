"""Workspace statistics aggregation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .bridge import config as bridge_config
from .spawn import config as spawn_config


@dataclass
class TopChannel:
    name: str
    message_count: int
    last_activity: str | None


@dataclass
class BridgeStats:
    available: bool
    channel_count: int = 0
    message_count: int = 0
    note_count: int = 0
    active_24h: int = 0
    top_channels: list[TopChannel] | None = None
    message_leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


@dataclass
class MemoryStats:
    available: bool
    entry_count: int = 0
    identity_count: int = 0
    topic_count: int = 0
    sources: set[str] | None = None
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class KnowledgeStats:
    available: bool
    entry_count: int = 0
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class AgentStats:
    available: bool
    registration_count: int = 0
    unique_identities: int = 0


@dataclass
class SpaceStats:
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    agents: AgentStats


def _fetchone(conn: sqlite3.Connection, query: str, default: int = 0) -> int:
    try:
        row = conn.execute(query).fetchone()
        return int(row[0]) if row and row[0] is not None else default
    except sqlite3.OperationalError:
        return default


def _safe_connect(db_path: Path) -> sqlite3.Connection | None:
    try:
        return sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        return None


def bridge_stats(limit: int = 5) -> BridgeStats:
    bridge_db = bridge_config.DB_PATH
    if not bridge_db.exists():
        return BridgeStats(available=False)

    conn = _safe_connect(bridge_db)
    if conn is None:
        return BridgeStats(available=False)

    conn.row_factory = sqlite3.Row
    try:
        channel_count = _fetchone(conn, "SELECT COUNT(*) FROM channels")
        message_count = _fetchone(conn, "SELECT COUNT(*) FROM messages")
        note_count = _fetchone(conn, "SELECT COUNT(*) FROM notes")
        active_24h = _fetchone(
            conn,
            """
            SELECT COUNT(DISTINCT channel_id)
            FROM messages
            WHERE created_at >= datetime('now', '-24 hours')
            """,
        )

        try:
            cursor = conn.execute(
                """
                SELECT c.name AS name,
                       COUNT(m.id) AS messages,
                       MAX(m.created_at) AS last_activity
                FROM channels c
                LEFT JOIN messages m ON c.id = m.channel_id
                GROUP BY c.id, c.name
                ORDER BY messages DESC, c.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            top_channels = [
                TopChannel(
                    name=row["name"],
                    message_count=row["messages"],
                    last_activity=row["last_activity"],
                )
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            top_channels = []

        try:
            cursor = conn.execute(
                """
                SELECT sender, COUNT(*) as count
                FROM messages
                GROUP BY sender
                ORDER BY count DESC
                LIMIT ?
                """,
                (limit,),
            )
            message_leaderboard = [
                LeaderboardEntry(identity=row[0], count=row[1])
                for row in cursor.fetchall()
            ]
        except sqlite3.OperationalError:
            message_leaderboard = []
    finally:
        conn.close()

    return BridgeStats(
        available=True,
        channel_count=channel_count,
        message_count=message_count,
        note_count=note_count,
        active_24h=active_24h,
        top_channels=top_channels,
        message_leaderboard=message_leaderboard,
    )


def _memory_candidates() -> Iterable[Path]:
    workspace_memory = spawn_config.workspace_root() / ".space" / "memory.db"
    local_memory = Path(__file__).resolve().parent.parent / ".space" / "memory.db"
    seen = set()
    for candidate in (workspace_memory, local_memory):
        if candidate.exists() and candidate not in seen:
            seen.add(candidate)
            yield candidate


def memory_stats(limit: int = 5) -> MemoryStats:
    candidates = list(_memory_candidates())
    if not candidates:
        return MemoryStats(available=False)

    entry_total = 0
    identities: set[str] = set()
    topics: set[str] = set()
    leaderboard: dict[str, int] = {}
    sources: set[str] = set()

    for db_path in candidates:
        conn = _safe_connect(db_path)
        if conn is None:
            continue
        try:
            entry_total += _fetchone(conn, "SELECT COUNT(*) FROM entries")

            for row in conn.execute("SELECT DISTINCT identity FROM entries"):
                if row[0]:
                    identities.add(row[0])

            for row in conn.execute("SELECT DISTINCT topic FROM entries"):
                if row[0]:
                    topics.add(row[0])

            for identity, count in conn.execute(
                "SELECT identity, COUNT(*) FROM entries GROUP BY identity"
            ):
                leaderboard[identity] = leaderboard.get(identity, 0) + int(count)
        finally:
            conn.close()

        sources.add(db_path.parent.parent.name if db_path.parent.parent.name else str(db_path.parent))

    ordered_leaderboard = sorted(
        (LeaderboardEntry(identity=identity, count=count) for identity, count in leaderboard.items()),
        key=lambda item: item.count,
        reverse=True,
    )

    return MemoryStats(
        available=True,
        entry_count=entry_total,
        identity_count=len(identities),
        topic_count=len(topics),
        sources=sources,
        leaderboard=ordered_leaderboard[:limit],
    )


def _knowledge_candidates() -> Iterable[Path]:
    workspace_knowledge = spawn_config.workspace_root() / ".space" / "knowledge.db"
    local_knowledge = Path(__file__).resolve().parent.parent / ".space" / "knowledge.db"
    seen = set()
    for candidate in (workspace_knowledge, local_knowledge):
        if candidate.exists() and candidate not in seen:
            seen.add(candidate)
            yield candidate


def knowledge_stats(limit: int = 5) -> KnowledgeStats:
    candidates = list(_knowledge_candidates())
    if not candidates:
        return KnowledgeStats(available=False)

    entry_total = 0
    leaderboard: dict[str, int] = {}

    for db_path in candidates:
        conn = _safe_connect(db_path)
        if conn is None:
            continue
        try:
            entry_total += _fetchone(conn, "SELECT COUNT(*) FROM knowledge")
            try:
                for contributor, count in conn.execute(
                    "SELECT contributor, COUNT(*) FROM knowledge GROUP BY contributor"
                ):
                    leaderboard[contributor] = leaderboard.get(contributor, 0) + int(count)
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()

    ordered_leaderboard = sorted(
        (LeaderboardEntry(identity=contrib, count=count) for contrib, count in leaderboard.items()),
        key=lambda item: item.count,
        reverse=True,
    )

    return KnowledgeStats(
        available=True,
        entry_count=entry_total,
        leaderboard=ordered_leaderboard[:limit],
    )


def agent_stats() -> AgentStats:
    spawn_db = spawn_config.workspace_root() / ".space" / "spawn.db"
    if not spawn_db.exists():
        return AgentStats(available=False)

    conn = _safe_connect(spawn_db)
    if conn is None:
        return AgentStats(available=False)

    try:
        conn.row_factory = sqlite3.Row
        registration_count = _fetchone(conn, "SELECT COUNT(*) FROM registrations")
        unique_identities = _fetchone(
            conn,
            "SELECT COUNT(DISTINCT sender_id) FROM registrations",
        )
    finally:
        conn.close()

    return AgentStats(
        available=True,
        registration_count=registration_count,
        unique_identities=unique_identities,
    )


def collect(limit: int = 5) -> SpaceStats:
    """Collect all workspace stats."""

    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
        agents=agent_stats(),
    )


__all__ = [
    "AgentStats",
    "BridgeStats",
    "KnowledgeStats",
    "LeaderboardEntry",
    "MemoryStats",
    "SpaceStats",
    "collect",
]
