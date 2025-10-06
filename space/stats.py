from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .bridge import config as bridge_config
from .lib.storage import context, utils


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


@dataclass
class BridgeStats:
    available: bool
    message_leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class MemoryStats:
    available: bool
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class KnowledgeStats:
    available: bool
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class SpaceStats:
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats


def bridge_stats(limit: int = None) -> BridgeStats:
    db = bridge_config.DB_PATH
    if not db.exists():
        return BridgeStats(available=False)

    conn = sqlite3.connect(db)
    if limit:
        leaderboard = [
            LeaderboardEntry(identity=row[0], count=row[1])
            for row in conn.execute(
                "SELECT sender, COUNT(*) as count FROM messages GROUP BY sender ORDER BY count DESC LIMIT ?",
                (limit,),
            )
        ]
    else:
        leaderboard = [
            LeaderboardEntry(identity=row[0], count=row[1])
            for row in conn.execute(
                "SELECT sender, COUNT(*) as count FROM messages GROUP BY sender ORDER BY count DESC"
            )
        ]
    conn.close()
    return BridgeStats(available=True, message_leaderboard=leaderboard)


def memory_stats(limit: int = None) -> MemoryStats:
    ctx_db = utils.database_path("context.db")
    if not ctx_db.exists():
        return MemoryStats(available=False)

    with context.connect() as conn:
        if limit:
            rows = conn.execute(
                "SELECT identity, COUNT(*) as count FROM memory GROUP BY identity ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT identity, COUNT(*) as count FROM memory GROUP BY identity ORDER BY count DESC"
            ).fetchall()

    leaderboard = [LeaderboardEntry(identity=row[0], count=row[1]) for row in rows]
    return MemoryStats(available=True, leaderboard=leaderboard)


def knowledge_stats(limit: int = None) -> KnowledgeStats:
    ctx_db = utils.database_path("context.db")
    if not ctx_db.exists():
        return KnowledgeStats(available=False)

    with context.connect() as conn:
        if limit:
            rows = conn.execute(
                "SELECT contributor, COUNT(*) as count FROM knowledge GROUP BY contributor ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT contributor, COUNT(*) as count FROM knowledge GROUP BY contributor ORDER BY count DESC"
            ).fetchall()

    leaderboard = [LeaderboardEntry(identity=row[0], count=row[1]) for row in rows]
    return KnowledgeStats(available=True, leaderboard=leaderboard)


def collect(limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
    )
