from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .bridge import config as bridge_config
from .spawn import config as spawn_config


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


def _candidates(name: str) -> list[Path]:
    workspace = spawn_config.workspace_root() / ".space" / name
    local = Path(__file__).resolve().parent.parent / ".space" / name
    return [p for p in (workspace, local) if p.exists()]


def bridge_stats(limit: int = 5) -> BridgeStats:
    db = bridge_config.DB_PATH
    if not db.exists():
        return BridgeStats(available=False)

    conn = sqlite3.connect(db)
    leaderboard = [
        LeaderboardEntry(identity=row[0], count=row[1])
        for row in conn.execute(
            "SELECT sender, COUNT(*) as count FROM messages GROUP BY sender ORDER BY count DESC LIMIT ?",
            (limit,),
        )
    ]
    conn.close()
    return BridgeStats(available=True, message_leaderboard=leaderboard)


def memory_stats(limit: int = 5) -> MemoryStats:
    candidates = _candidates("memory.db")
    if not candidates:
        return MemoryStats(available=False)

    counts: dict[str, int] = {}
    for db in candidates:
        conn = sqlite3.connect(db)
        for identity, count in conn.execute("SELECT identity, COUNT(*) FROM entries GROUP BY identity"):
            counts[identity] = counts.get(identity, 0) + int(count)
        conn.close()

    leaderboard = sorted(
        [LeaderboardEntry(identity=k, count=v) for k, v in counts.items()],
        key=lambda x: x.count,
        reverse=True,
    )[:limit]

    return MemoryStats(available=True, leaderboard=leaderboard)


def knowledge_stats(limit: int = 5) -> KnowledgeStats:
    candidates = _candidates("knowledge.db")
    if not candidates:
        return KnowledgeStats(available=False)

    counts: dict[str, int] = {}
    for db in candidates:
        conn = sqlite3.connect(db)
        for contrib, count in conn.execute("SELECT contributor, COUNT(*) FROM knowledge GROUP BY contributor"):
            counts[contrib] = counts.get(contrib, 0) + int(count)
        conn.close()

    leaderboard = sorted(
        [LeaderboardEntry(identity=k, count=v) for k, v in counts.items()],
        key=lambda x: x.count,
        reverse=True,
    )[:limit]

    return KnowledgeStats(available=True, leaderboard=leaderboard)


def collect(limit: int = 5) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
    )
