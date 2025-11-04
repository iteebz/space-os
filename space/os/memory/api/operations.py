"""Memory operations: working memory for agents (flat, linear accumulation)."""

from datetime import datetime, timedelta

from space.core.models import Memory
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import resolve_id, uuid7
from space.os import spawn


def _row_to_memory(row: store.Row) -> Memory:
    data = dict(row)
    data["core"] = bool(data["core"])
    data["topic"] = data.get("topic")
    return from_row(data, Memory)


def add_memory(
    agent_id: str,
    message: str,
    topic: str | None = None,
    core: bool = False,
    source: str = "manual",
) -> str:
    memory_id = uuid7()
    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, message, topic, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (memory_id, agent_id, message, topic, now, 1 if core else 0, source),
        )
    spawn.api.touch_agent(agent_id)
    return memory_id


def list_memories(
    identity: str,
    topic: str | None = None,
    show_all: bool = False,
    limit: int | None = None,
    filter: str | None = None,
) -> list[Memory]:
    from space.os import spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")
    agent_id = agent.agent_id

    with store.ensure() as conn:
        params = [agent_id]
        query = "SELECT memory_id, agent_id, message, topic, created_at, archived_at, core, source FROM memories WHERE agent_id = ?"

        if topic:
            query += " AND topic = ?"
            params.append(topic)

        if filter == "core":
            query += " AND core = 1"
        elif filter and filter.startswith("recent:"):
            days = int(filter.split(":")[1])
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            query += " AND created_at >= ?"
            params.append(cutoff)

        if not show_all:
            query += " AND archived_at IS NULL"

        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_memory(row) for row in rows]


def edit_memory(memory_id: str, new_message: str) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)
    entry = get_memory(full_id)
    if not entry:
        raise ValueError(f"Memory '{memory_id}' not found")
    with store.ensure() as conn:
        conn.execute(
            "UPDATE memories SET message = ? WHERE memory_id = ?",
            (new_message, full_id),
        )
    spawn.api.touch_agent(entry.agent_id)


def delete_memory(memory_id: str) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)
    entry = get_memory(full_id)
    if not entry:
        raise ValueError(f"Memory '{memory_id}' not found")
    with store.ensure() as conn:
        conn.execute("DELETE FROM memories WHERE memory_id = ?", (full_id,))


def archive_memory(memory_id: str, restore: bool = False) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)
    entry = get_memory(full_id)
    if not entry:
        raise ValueError(f"Memory '{memory_id}' not found")

    if restore:
        with store.ensure() as conn:
            conn.execute(
                "UPDATE memories SET archived_at = NULL WHERE memory_id = ?",
                (full_id,),
            )
    else:
        now = datetime.now().isoformat()
        with store.ensure() as conn:
            conn.execute(
                "UPDATE memories SET archived_at = ? WHERE memory_id = ?",
                (now, full_id),
            )


def mark_memory_core(memory_id: str, core: bool = True) -> None:
    entry = get_memory(memory_id)
    if not entry:
        raise ValueError(f"Memory '{memory_id}' not found")
    with store.ensure() as conn:
        conn.execute(
            "UPDATE memories SET core = ? WHERE memory_id = ?",
            (1 if core else 0, memory_id),
        )


def toggle_memory_core(memory_id: str) -> bool:
    entry = get_memory(memory_id)
    if not entry:
        raise ValueError(f"Memory '{memory_id}' not found")
    is_core = entry.core
    new_state = not is_core
    with store.ensure() as conn:
        conn.execute(
            "UPDATE memories SET core = ? WHERE memory_id = ?",
            (1 if new_state else 0, memory_id),
        )
    return new_state


def find_related_memories(
    entry: Memory, limit: int = 5, show_all: bool = False
) -> list[tuple[Memory, int]]:
    """Find memories related by keyword similarity."""
    from space.lib.stopwords import stopwords

    tokens = set(entry.message.lower().split())
    if entry.topic:
        tokens |= set(entry.topic.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    agent_id = entry.agent_id

    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure() as conn:
        try:
            conn.execute("CREATE TEMPORARY TABLE keywords (keyword TEXT)")
            conn.executemany("INSERT INTO keywords VALUES (?)", [(k,) for k in keywords])

            query = f"""
                SELECT m.memory_id, m.agent_id, m.message, m.topic, m.created_at,
                       m.archived_at, m.core, m.source, COUNT(k.keyword) as score
                FROM memories m, keywords k
                WHERE m.agent_id = ? AND m.memory_id != ? AND (m.message LIKE '%' || k.keyword || '%' OR m.topic LIKE '%' || k.keyword || '%') {archive_filter}
                GROUP BY m.memory_id
                ORDER BY score DESC
                LIMIT ?
            """
            rows = conn.execute(query, (agent_id, entry.memory_id, limit)).fetchall()
        finally:
            conn.execute("DROP TABLE IF EXISTS keywords")

    return [(_row_to_memory(row), row["score"]) for row in rows]


def get_memory(memory_id: str) -> Memory | None:
    """Get memory entry by ID."""
    try:
        full_id = resolve_id("memories", "memory_id", memory_id)
    except ValueError:
        return None

    with store.ensure() as conn:
        row = conn.execute(
            "SELECT memory_id, agent_id, message, topic, created_at, archived_at, core, source FROM memories WHERE memory_id = ?",
            (full_id,),
        ).fetchone()
    if not row:
        return None

    return _row_to_memory(row)


def get_agent_memories(
    agent_id: str,
    after_timestamp: str | None = None,
    limit: int | None = None,
) -> list[Memory]:
    """Get memories for an agent by ID (low-level API for primitives/apps).

    Args:
        agent_id: Agent ID
        after_timestamp: Optional ISO timestamp cutoff (memories after this time)
        limit: Maximum number of memories to return

    Returns:
        List of Memory objects, ordered by creation time (newest first)
    """
    with store.ensure() as conn:
        query = "SELECT memory_id, agent_id, message, topic, created_at, archived_at, core, source FROM memories WHERE agent_id = ? AND archived_at IS NULL"
        params = [agent_id]

        if after_timestamp:
            query += " AND created_at > ?"
            params.append(after_timestamp)

        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_memory(row) for row in rows]


def count_memories() -> tuple[int, int, int]:
    """Get memory counts: (total, active, archived)."""
    with store.ensure() as conn:
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM memories WHERE archived_at IS NULL").fetchone()[
            0
        ]
        archived = total - active
    return total, active, archived


def stats(agent_id: str | None = None) -> "MemoryStats":
    """Get memory statistics for an agent or all agents."""
    from space.core.models import MemoryStats

    with store.ensure() as conn:
        if agent_id:
            total = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id = ?", (agent_id,)
            ).fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id = ? AND archived_at IS NULL",
                (agent_id,),
            ).fetchone()[0]
            topics = conn.execute(
                "SELECT COUNT(DISTINCT topic) FROM memories WHERE agent_id = ? AND topic IS NOT NULL",
                (agent_id,),
            ).fetchone()[0]
        else:
            total, active, _ = count_memories()
            topics = conn.execute(
                "SELECT COUNT(DISTINCT topic) FROM memories WHERE topic IS NOT NULL"
            ).fetchone()[0]

        archived = total - active

    return MemoryStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=topics,
    )


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search memory entries by query, filtering by agent if identity provided."""
    results = []
    with store.ensure() as conn:
        sql_query = (
            "SELECT memory_id, agent_id, topic, message, created_at FROM memories "
            "WHERE (message LIKE ? OR topic LIKE ?)"
        )
        params = [f"%{query}%", f"%{query}%"]

        if identity and not all_agents:
            agent = spawn.get_agent(identity)
            if not agent:
                raise ValueError(f"Agent '{identity}' not found")
            sql_query += " AND agent_id = ?"
            params.append(agent.agent_id)

        sql_query += " ORDER BY created_at ASC"
        rows = conn.execute(sql_query, params).fetchall()

        for row in rows:
            agent = spawn.get_agent(row["agent_id"])
            results.append(
                {
                    "source": "memory",
                    "memory_id": row["memory_id"],
                    "topic": row["topic"],
                    "message": row["message"],
                    "identity": agent.identity if agent else row["agent_id"],
                    "timestamp": row["created_at"],
                    "reference": f"memory:{row['memory_id']}",
                }
            )
    return results
