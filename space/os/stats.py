from __future__ import annotations

from space.apps.bridge.db import connect as get_bridge_db_connection
from space.apps.knowledge import db as knowledge_db
from space.apps.memory import db as memory_db
from space.os.lib import db_utils


def memory_stats(limit: int = None) -> dict:
    mem_db = db_utils.database_path("memory.db")
    if not mem_db.exists():
        return {"available": False, "leaderboard": None}

    with memory_db.connect() as conn:
        if limit:
            rows = conn.execute(
                "SELECT identity, COUNT(*) as count FROM memory GROUP BY identity ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT identity, COUNT(*) as count FROM memory GROUP BY identity ORDER BY count DESC"
            ).fetchall()

    leaderboard = [{"identity": row[0], "count": row[1]} for row in rows]
    return {"available": True, "leaderboard": leaderboard}


def knowledge_stats(limit: int = None) -> dict:
    k_db = db_utils.database_path("knowledge.db")
    if not k_db.exists():
        return {"available": False, "leaderboard": None}

    with knowledge_db.connect() as conn:
        if limit:
            rows = conn.execute(
                "SELECT contributor, COUNT(*) as count FROM knowledge GROUP BY contributor ORDER BY count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT contributor, COUNT(*) as count FROM knowledge GROUP BY contributor ORDER BY count DESC"
            ).fetchall()

    leaderboard = [{"identity": row[0], "count": row[1]} for row in rows]
    return {"available": True, "leaderboard": leaderboard}


def bridge_stats(limit: int = None) -> dict:
    try:
        with get_bridge_db_connection() as conn:
            if limit:
                rows = conn.execute(
                    "SELECT sender, COUNT(*) as count FROM messages GROUP BY sender ORDER BY count DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT sender, COUNT(*) as count FROM messages GROUP BY sender ORDER BY count DESC"
                ).fetchall()
        leaderboard = [{"identity": row[0], "count": row[1]} for row in rows]
        return {"available": True, "leaderboard": leaderboard}
    except Exception:
        return {"available": False, "leaderboard": None}


def collect(limit: int = None) -> dict:
    return {
        "bridge": bridge_stats(limit=limit),
        "memory": memory_stats(limit=limit),
        "knowledge": knowledge_stats(limit=limit),
    }
