"""Memory operations: working memory for agents (flat, linear accumulation)."""

from datetime import datetime, timedelta

from space.core.models import Memory, SearchResult
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
    topic = topic or "general"
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
    filter_type: str | None = None,
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

        if filter_type == "core":
            query += " AND core = 1"
        elif filter_type and filter_type.startswith("recent:"):
            days = int(filter_type.split(":")[1])
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


def search_memories(
    identity: str,
    query: str,
    show_all: bool = False,
    limit: int | None = None,
) -> list[Memory]:
    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")
    agent_id = agent.agent_id

    archive_filter = "" if show_all else "AND archived_at IS NULL"

    with store.ensure() as conn:
        sql = f"""
            SELECT m.memory_id, m.agent_id, m.message, m.topic, m.created_at,
                   m.archived_at, m.core, m.source
            FROM memories m
            WHERE m.agent_id = ? AND m.memory_id IN (
                SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?
            ) {archive_filter}
            ORDER BY m.created_at DESC
        """
        params = [agent_id, query]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_memory(row) for row in rows]


def edit_memory(memory_id: str, new_message: str) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)
    with store.ensure() as conn:
        cursor = conn.execute(
            "UPDATE memories SET message = ? WHERE memory_id = ? RETURNING agent_id",
            (new_message, full_id),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Memory '{memory_id}' not found")
        spawn.api.touch_agent(row[0])


def delete_memory(memory_id: str) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)
    with store.ensure() as conn:
        cursor = conn.execute("DELETE FROM memories WHERE memory_id = ?", (full_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"Memory '{memory_id}' not found")


def archive_memory(memory_id: str, restore: bool = False) -> None:
    full_id = resolve_id("memories", "memory_id", memory_id)

    with store.ensure() as conn:
        if restore:
            cursor = conn.execute(
                "UPDATE memories SET archived_at = NULL WHERE memory_id = ?",
                (full_id,),
            )
        else:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                "UPDATE memories SET archived_at = ? WHERE memory_id = ?",
                (now, full_id),
            )
        if cursor.rowcount == 0:
            raise ValueError(f"Memory '{memory_id}' not found")


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
    from space.lib.stopwords import extract_keywords

    text = entry.message
    if entry.topic:
        text += " " + entry.topic
    keywords = extract_keywords(text)

    if not keywords:
        return []

    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure() as conn:
        fts_query = " OR ".join(keywords)
        try:
            query = f"""
                SELECT m.memory_id, m.agent_id, m.message, m.topic, m.created_at,
                       m.archived_at, m.core, m.source
                FROM memories m
                WHERE m.agent_id = ? AND m.memory_id != ? AND m.rowid IN (
                    SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?
                ) {archive_filter}
                ORDER BY m.created_at DESC
                LIMIT ?
            """
            rows = conn.execute(
                query, (entry.agent_id, entry.memory_id, fts_query, limit)
            ).fetchall()
            return [(_row_to_memory(row), len(keywords)) for row in rows]
        except Exception:
            return []


def get_memory(memory_id: str) -> Memory | None:
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
    with store.ensure() as conn:
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM memories WHERE archived_at IS NULL").fetchone()[
            0
        ]
        archived = total - active
    return total, active, archived


def stats(agent_id: str | None = None) -> "MemoryStats":
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


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[SearchResult]:
    results = []

    agent_id = None
    if identity and not all_agents:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Agent '{identity}' not found")
        agent_id = agent.agent_id

    with store.ensure() as conn:
        try:
            fts_query = """
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.created_at
                FROM memories m
                WHERE m.rowid IN (
                    SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?
                ) AND m.archived_at IS NULL
            """
            params = [query]

            if agent_id:
                fts_query += " AND m.agent_id = ?"
                params.append(agent_id)

            fts_query += " ORDER BY m.created_at ASC"
            rows = conn.execute(fts_query, params).fetchall()
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"FTS query failed, falling back to LIKE: {e}")
            rows = []
            fallback_query = (
                "SELECT memory_id, agent_id, topic, message, created_at FROM memories "
                "WHERE (message LIKE ? OR topic LIKE ?) AND archived_at IS NULL"
            )
            params = [f"%{query}%", f"%{query}%"]

            if agent_id:
                fallback_query += " AND agent_id = ?"
                params.append(agent_id)

            fallback_query += " ORDER BY created_at ASC"
            rows = conn.execute(fallback_query, params).fetchall()

        for row in rows:
            agent = spawn.get_agent(row["agent_id"])
            results.append(
                SearchResult(
                    source="memory",
                    reference=f"memory:{row['memory_id']}",
                    content=row["message"],
                    timestamp=row["created_at"],
                    agent_id=row["agent_id"],
                    identity=agent.identity if agent else row["agent_id"],
                    metadata={"memory_id": row["memory_id"], "topic": row["topic"]},
                )
            )
    return results
