from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import db, paths


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


def bridge_stats(limit: int = None) -> BridgeStats:
    db_path = paths.space_root() / "bridge.db"
    if not db_path.exists():
        return BridgeStats(available=False)

    with db.connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM messages m JOIN channels c ON m.channel_id = c.id WHERE c.archived_at IS NULL"
        ).fetchone()[0]
        archived = conn.execute(
            "SELECT COUNT(*) FROM messages m JOIN channels c ON m.channel_id = c.id WHERE c.archived_at IS NOT NULL"
        ).fetchone()[0]
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

        if limit:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) as count FROM messages GROUP BY agent_id ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) as count FROM messages GROUP BY agent_id ORDER BY count DESC"
            ).fetchall()

    from ..spawn import registry

    with registry.get_db() as reg_conn:
        names = {row[0]: row[1] for row in reg_conn.execute("SELECT id, name FROM agents")}

    leaderboard = [
        LeaderboardEntry(identity=names.get(row[0], row[0]), count=row[1]) for row in rows
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
        message_leaderboard=leaderboard,
    )


def memory_stats(limit: int = None) -> MemoryStats:
    db_path = paths.space_root() / "memory.db"
    if not db_path.exists():
        return MemoryStats(available=False)

    with db.connect(db_path) as conn:
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
                "SELECT agent_id, COUNT(*) as count FROM memory GROUP BY agent_id ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) as count FROM memory GROUP BY agent_id ORDER BY count DESC"
            ).fetchall()

    from ..spawn import registry

    with registry.get_db() as reg_conn:
        names = {row[0]: row[1] for row in reg_conn.execute("SELECT id, name FROM agents")}

    leaderboard = [
        LeaderboardEntry(identity=names.get(row[0], row[0]), count=row[1]) for row in rows
    ]
    return MemoryStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def knowledge_stats(limit: int = None) -> KnowledgeStats:
    db_path = paths.space_root() / "knowledge.db"
    if not db_path.exists():
        return KnowledgeStats(available=False)

    with db.connect(db_path) as conn:
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
                "SELECT agent_id, COUNT(*) as count FROM knowledge GROUP BY agent_id ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) as count FROM knowledge GROUP BY agent_id ORDER BY count DESC"
            ).fetchall()

    from ..spawn import registry

    with registry.get_db() as reg_conn:
        names = {row[0]: row[1] for row in reg_conn.execute("SELECT id, name FROM agents")}

    leaderboard = [
        LeaderboardEntry(identity=names.get(row[0], row[0]), count=row[1]) for row in rows
    ]
    return KnowledgeStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
        leaderboard=leaderboard,
    )


def get_agent_metrics() -> dict[str, dict]:
    """Get s-b-m-k metrics for all agents by UUID."""
    from ..spawn import registry
    
    bridge_db = paths.space_root() / "bridge.db"
    mem_db = paths.space_root() / "memory.db"
    know_db = paths.space_root() / "knowledge.db"
    events_db = paths.space_root() / "events.db"
    
    metrics = {}
    
    if bridge_db.exists():
        with db.connect(bridge_db) as conn:
            for row in conn.execute("SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id"):
                metrics[row[0]] = {"spawns": 0, "msgs": row[1], "mems": 0, "knowledge": 0}
    
    if events_db.exists():
        with db.connect(events_db) as conn:
            for row in conn.execute(
                "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id"
            ):
                if row[0] in metrics:
                    metrics[row[0]]["spawns"] = row[1]
                else:
                    metrics[row[0]] = {"spawns": row[1], "msgs": 0, "mems": 0, "knowledge": 0}
    
    if mem_db.exists():
        with db.connect(mem_db) as conn:
            for row in conn.execute("SELECT agent_id, COUNT(*) FROM memory GROUP BY agent_id"):
                if row[0] in metrics:
                    metrics[row[0]]["mems"] = row[1]
    
    if know_db.exists():
        with db.connect(know_db) as conn:
            for row in conn.execute("SELECT agent_id, COUNT(*) FROM knowledge GROUP BY agent_id"):
                if row[0] in metrics:
                    metrics[row[0]]["knowledge"] = row[1]
    
    return metrics


def agent_stats(limit: int = None) -> list[AgentStats] | None:
    from ..spawn import registry

    bridge_db = paths.space_root() / "bridge.db"
    mem_db = paths.space_root() / "memory.db"
    know_db = paths.space_root() / "knowledge.db"
    paths.space_root() / "spawn.db"

    if not bridge_db.exists():
        return None

    with registry.get_db() as reg_conn:
        names = {row[0]: row[1] for row in reg_conn.execute("SELECT id, name FROM agents")}
        set(names.keys())

    identities = {}

    with db.connect(bridge_db) as conn:
        for row in conn.execute(
            "SELECT agent_id, COUNT(*) as msgs FROM messages GROUP BY agent_id"
        ):
            agent_name = names.get(row[0], row[0])
            identities[agent_name] = {
                "msgs": row[1],
                "last_active": None,
                "mems": 0,
                "knowledge": 0,
                "spawns": 0,
                "channels": [],
            }

        for row in conn.execute(
            "SELECT agent_id, GROUP_CONCAT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL GROUP BY agent_id"
        ):
            agent_name = names.get(row[0], row[0])
            channels = row[1].split(",") if row[1] else []
            if agent_name in identities:
                identities[agent_name]["channels"] = channels


    if mem_db.exists():
        with db.connect(mem_db) as conn:
            for row in conn.execute("SELECT agent_id, COUNT(*) FROM memory GROUP BY agent_id"):
                agent_name = names.get(row[0], row[0])
                if agent_name in identities:
                    identities[agent_name]["mems"] = row[1]

    if know_db.exists():
        with db.connect(know_db) as conn:
            for row in conn.execute("SELECT agent_id, COUNT(*) FROM knowledge GROUP BY agent_id"):
                agent_name = names.get(row[0], row[0])
                if agent_name in identities:
                    identities[agent_name]["knowledge"] = row[1]

    events_db = paths.space_root() / "events.db"
    if events_db.exists():
        with db.connect(events_db) as conn:
            for row in conn.execute(
                "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id"
            ):
                agent_name = names.get(row[0], row[0])
                if agent_name in identities:
                    identities[agent_name]["spawns"] = row[1]

            for row in conn.execute(
                "SELECT agent_id, MAX(timestamp) FROM events WHERE agent_id IS NOT NULL GROUP BY agent_id"
            ):
                agent_name = names.get(row[0], row[0])
                if agent_name in identities:
                    identities[agent_name]["last_active"] = str(row[1])

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
    db_path = paths.space_root() / "spawn.db"
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
