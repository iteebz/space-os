import time
import uuid
from datetime import datetime

from space.core.models import Memory
from space.lib import store
from space.lib.ids import resolve_id
from space.lib.store import from_row
from space.lib.uuid7 import uuid7
from space.os import spawn


def _row_to_memory(row: store.Row) -> Memory:
    data = dict(row)
    data["core"] = bool(data["core"])
    return from_row(data, Memory)


def add_entry(
    agent_id: str, topic: str, message: str, core: bool = False, source: str = "manual"
) -> str:
    memory_id = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with store.ensure("memory") as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, agent_id, topic, message, ts, now, 1 if core else 0, source),
        )
    spawn.api.touch_agent(agent_id)
    return memory_id


def list_entries(
    identity: str,
    topic: str | None = None,
    show_all: bool = False,
    limit: int | None = None,
    filter: str | None = None,
) -> list[Memory]:
    """List memory entries. filter='core' or 'recent:days' (e.g., 'recent:7')."""
    from space.os import spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found.")
    agent_id = agent.agent_id

    with store.ensure("memory") as conn:
        params = [agent_id]
        query = "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE agent_id = ?"

        if topic:
            query += " AND topic = ?"
            params.append(topic)

        if filter == "core":
            query += " AND core = 1"
        elif filter and filter.startswith("recent:"):
            days = int(filter.split(":")[1])
            cutoff = int(time.time()) - (days * 86400)
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


def edit_entry(memory_id: str, new_message: str) -> None:
    full_id = resolve_id("memory", "memory_id", memory_id)
    entry = get_by_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with store.ensure("memory") as conn:
        conn.execute(
            "UPDATE memories SET message = ?, timestamp = ? WHERE memory_id = ? ",
            (new_message, ts, full_id),
        )
    spawn.api.touch_agent(entry.agent_id)


def delete_entry(memory_id: str) -> None:
    full_id = resolve_id("memory", "memory_id", memory_id)
    entry = get_by_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    with store.ensure("memory") as conn:
        conn.execute("DELETE FROM memories WHERE memory_id = ?", (full_id,))


def archive_entry(memory_id: str) -> None:
    full_id = resolve_id("memory", "memory_id", memory_id)
    entry = get_by_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    now = int(time.time())
    with store.ensure("memory") as conn:
        conn.execute(
            "UPDATE memories SET archived_at = ? WHERE memory_id = ?",
            (now, full_id),
        )


def restore_entry(memory_id: str, agent_id: str | None = None) -> None:
    full_id = resolve_id("memory", "memory_id", memory_id)
    entry = get_by_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    if agent_id is None:
        agent_id = entry.agent_id
    with store.ensure("memory") as conn:
        conn.execute(
            "UPDATE memories SET archived_at = NULL WHERE memory_id = ?",
            (full_id,),
        )


def mark_core(memory_id: str, core: bool = True, agent_id: str | None = None) -> None:
    entry = get_by_id(memory_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    if agent_id is None:
        agent_id = entry.agent_id
    with store.ensure("memory") as conn:
        conn.execute(
            "UPDATE memories SET core = ? WHERE memory_id = ?",
            (1 if core else 0, entry.memory_id),
        )


def find_related(entry: Memory, limit: int = 5, show_all: bool = False) -> list[tuple[Memory, int]]:
    from space.lib.text_utils import stopwords

    tokens = set(entry.message.lower().split()) | set(entry.topic.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    agent_id = entry.agent_id

    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure("memory") as conn:
        try:
            conn.execute("CREATE TEMPORARY TABLE keywords (keyword TEXT)")
            conn.executemany("INSERT INTO keywords VALUES (?)", [(k,) for k in keywords])

            query = f"""
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp,
                       m.created_at, m.archived_at, m.core, m.source, m.bridge_channel,
                       m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by, COUNT(k.keyword) as score
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


def get_by_id(memory_id: str) -> Memory | None:
    try:
        full_id = resolve_id("memory", "memory_id", memory_id)
    except ValueError:
        with store.ensure("memory") as conn:
            row = conn.execute(
                "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE topic LIKE ? AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (f"%{memory_id}%",),
            ).fetchone()
        if row:
            return _row_to_memory(row)
        return None

    with store.ensure("memory") as conn:
        row = conn.execute(
            "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE memory_id = ?",
            (full_id,),
        ).fetchone()
    if not row:
        return None

    return _row_to_memory(row)


def replace_entry(
    old_ids: list[str], agent_id: str, topic: str, message: str, note: str = "", core: bool = False
) -> str:
    full_old_ids = [resolve_id("memory", "memory_id", old_id) for old_id in old_ids]
    new_id = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    with store.ensure("memory") as conn:
        with conn:
            conn.execute(
                "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, core, source, synthesis_note, supersedes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id,
                    agent_id,
                    topic,
                    message,
                    ts,
                    now,
                    1 if core else 0,
                    "manual",
                    note,
                    ",".join(full_old_ids),
                ),
            )

            for full_old_id in full_old_ids:
                link_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT OR IGNORE INTO links (link_id, memory_id, parent_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
                    (link_id, new_id, full_old_id, "supersedes", now),
                )
                conn.execute(
                    "UPDATE memories SET archived_at = ?, superseded_by = ? WHERE memory_id = ?",
                    (now, new_id, full_old_id),
                )

    return new_id


def get_chain(memory_id: str) -> dict[str, Memory | list[Memory]]:
    full_id = resolve_id("memory", "memory_id", memory_id)
    predecessors = []
    successors = []
    visited = set()

    def _traverse_predecessors(current_id: str):
        if current_id in visited:
            return
        visited.add(current_id)
        with store.ensure("memory") as conn:
            rows = conn.execute(
                """
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp,
                       m.created_at, m.archived_at, m.core, m.source, m.bridge_channel,
                       m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by
                FROM links l
                JOIN memories m ON l.parent_id = m.memory_id
                WHERE l.memory_id = ? AND l.kind = 'supersedes'
                """,
                (current_id,),
            ).fetchall()
            for row in rows:
                pred_entry = _row_to_memory(row)
                predecessors.append(pred_entry)
                _traverse_predecessors(pred_entry.memory_id)

    def _traverse_successors(current_id: str):
        if current_id in visited:
            return
        visited.add(current_id)
        with store.ensure("memory") as conn:
            rows = conn.execute(
                """
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp,
                       m.created_at, m.archived_at, m.core, m.source, m.bridge_channel,
                       m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by
                FROM links l
                JOIN memories m ON l.memory_id = m.memory_id
                WHERE l.parent_id = ? AND l.kind = 'supersedes'
                """,
                (current_id,),
            ).fetchall()
            for row in rows:
                succ_entry = _row_to_memory(row)
                successors.append(succ_entry)
                _traverse_successors(succ_entry.memory_id)

    _traverse_predecessors(full_id)
    visited.clear()
    _traverse_successors(full_id)

    start_entry = get_by_id(full_id)
    return {"start_entry": start_entry, "predecessors": predecessors, "successors": successors}


def add_link(memory_id: str, parent_id: str, kind: str = "supersedes") -> str:
    link_id = str(uuid.uuid4())
    now = int(time.time())
    with store.ensure("memory") as conn:
        conn.execute(
            "INSERT OR IGNORE INTO links (link_id, memory_id, parent_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
            (link_id, memory_id, parent_id, kind, now),
        )
    return link_id
