from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .bridge import config as bridge_config
from .knowledge import db as knowledge_db
from .lib import db as libdb
from .memory import db as memory_db


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


@dataclass
class AgentStats:
    identity: str
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
    channels: int = 0
    active_channels: int = 0
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


def bridge_stats(limit: int = None) -> BridgeStats:
    db = bridge_config.DB_PATH
    if not db.exists():
        return BridgeStats(available=False)

    with libdb.connect(db) as conn:
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL"
        ).fetchone()[0]
        active_channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE created_at > datetime('now', '-7 days')"
        ).fetchone()[0]
        notes = conn.execute("SELECT COUNT(*) FROM notes WHERE channel_id IS NOT NULL").fetchone()[
            0
        ]

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
    return BridgeStats(
        available=True,
        total=total,
        channels=channels,
        active_channels=active_channels,
        notes=notes,
        message_leaderboard=leaderboard,
    )


def memory_stats(limit: int = None) -> MemoryStats:
    db_path = memory_db.database_path()
    if not db_path.exists():
        return MemoryStats(available=False)

    with memory_db.connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM memory WHERE archived_at IS NULL").fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM memory WHERE archived_at IS NOT NULL"
        ).fetchone()[0]
        topics = conn.execute(
            "SELECT COUNT(DISTINCT topic) FROM memory WHERE archived_at IS NULL"
        ).fetchone()[0]

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
    return MemoryStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def knowledge_stats(limit: int = None) -> KnowledgeStats:
    db_path = knowledge_db.database_path()
    if not db_path.exists():
        return KnowledgeStats(available=False)

    with knowledge_db.connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE archived_at IS NOT NULL"
        ).fetchone()[0]
        topics = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM knowledge WHERE domain IS NOT NULL"
        ).fetchone()[0]

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
    return KnowledgeStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def agent_stats(limit: int = None) -> list[AgentStats] | None:
    from . import events
    from .spawn import config as spawn_config
    from .spawn import registry

    bridge_db = bridge_config.DB_PATH
    mem_db = memory_db.database_path()
    know_db = knowledge_db.database_path()

    if not bridge_db.exists():
        return None

    identities = {}

    with libdb.connect(bridge_db) as conn:
        for row in conn.execute("SELECT sender, COUNT(*) as msgs FROM messages GROUP BY sender"):
            identities[row[0]] = {
                "msgs": row[1],
                "last_active": None,
                "mems": 0,
                "knowledge": 0,
                "spawns": 0,
            }

        for row in conn.execute(
            "SELECT sender, GROUP_CONCAT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL GROUP BY sender"
        ):
            channels = row[1].split(",") if row[1] else []
            if row[0] in identities:
                identities[row[0]]["channels"] = channels

    if events.DB_PATH.exists():
        with libdb.connect(events.DB_PATH) as conn:
            for row in conn.execute(
                "SELECT identity, MAX(timestamp) FROM events WHERE identity IS NOT NULL GROUP BY identity"
            ):
                if row[0] in identities:
                    identities[row[0]]["last_active"] = str(row[1])

    spawn_db = spawn_config.registry_db()
    if spawn_db.exists():
        with registry.get_db() as conn:
            for row in conn.execute(
                "SELECT agent_name, COUNT(*) FROM registrations GROUP BY agent_name"
            ):
                if row[0] in identities:
                    identities[row[0]]["spawns"] = row[1]

    if mem_db.exists():
        with memory_db.connect() as conn:
            for row in conn.execute("SELECT identity, COUNT(*) FROM memory GROUP BY identity"):
                if row[0] in identities:
                    identities[row[0]]["mems"] = row[1]

    if know_db.exists():
        with knowledge_db.connect() as conn:
            for row in conn.execute(
                "SELECT contributor, COUNT(*) FROM knowledge GROUP BY contributor"
            ):
                if row[0] in identities:
                    identities[row[0]]["knowledge"] = row[1]

    def humanize_time(ts_str: str) -> str:
        if not ts_str:
            return None
        try:
            ts = datetime.fromtimestamp(int(ts_str))
            now = datetime.now()
            delta = now - ts

            if delta < timedelta(minutes=1):
                return "just now"
            if delta < timedelta(hours=1):
                mins = int(delta.total_seconds() / 60)
                return f"{mins}m ago"
            if delta < timedelta(days=1):
                hours = int(delta.total_seconds() / 3600)
                return f"{hours}h ago"
            if delta < timedelta(days=7):
                days = delta.days
                return f"{days}d ago"
            return ts.strftime("%b %d")
        except (ValueError, TypeError):
            return None

    agents = [
        AgentStats(
            identity=ident,
            spawns=data["spawns"],
            msgs=data["msgs"],
            mems=data["mems"],
            knowledge=data["knowledge"],
            channels=data.get("channels", []),
            last_active=data.get("last_active"),
            last_active_human=humanize_time(data.get("last_active")),
        )
        for ident, data in identities.items()
    ]

    agents.sort(key=lambda a: a.msgs, reverse=True)
    return agents[:limit] if limit else agents


def spawn_stats() -> SpawnStats:
    from .spawn import config as spawn_config
    from .spawn import registry

    db_path = spawn_config.registry_db()
    if not db_path.exists():
        return SpawnStats(available=False)

    with registry.get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM invocations").fetchone()[0]

        active_agents = conn.execute("SELECT DISTINCT agent_name FROM registrations").fetchall()
        agents = len(active_agents)

        if active_agents:
            placeholders = ",".join("?" * len(active_agents))
            agent_names = [row[0] for row in active_agents]
            hashes = conn.execute(
                f"SELECT COUNT(DISTINCT constitution_hash) FROM registrations WHERE agent_name IN ({placeholders})",
                agent_names,
            ).fetchone()[0]
        else:
            hashes = 0

    return SpawnStats(available=True, total=total, agents=agents, hashes=hashes)


def collect(limit: int = None) -> SpaceStats:
    return SpaceStats(
        bridge=bridge_stats(limit=limit),
        memory=memory_stats(limit=limit),
        knowledge=knowledge_stats(limit=limit),
        spawn=spawn_stats(),
        agents=agent_stats(limit=limit),
    )
