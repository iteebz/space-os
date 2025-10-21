from __future__ import annotations

import contextlib
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .. import events
from ..lib import db, paths
from ..lib.uuid7 import uuid7
from ..models import Memory
from ..spawn import registry

MEMORY_DB_NAME = "memory.db"

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    archived_at INTEGER,
    core INTEGER DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    bridge_channel TEXT,
    code_anchors TEXT,
    synthesis_note TEXT,
    supersedes TEXT,
    superseded_by TEXT
);

CREATE TABLE IF NOT EXISTS memory_links (
    link_id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(memory_id) REFERENCES memories(memory_id),
    FOREIGN KEY(parent_id) REFERENCES memories(memory_id),
    UNIQUE(memory_id, parent_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_topic ON memories(agent_id, topic);
CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_memory_id ON memories(memory_id);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);
CREATE INDEX IF NOT EXISTS idx_links_memory ON memory_links(memory_id);
CREATE INDEX IF NOT EXISTS idx_links_parent ON memory_links(parent_id);
"""


def database_path() -> Path:
    return paths.dot_space() / MEMORY_DB_NAME


def _migrate_memory_table_to_memories(conn: sqlite3.Connection):
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory'")
    if not cursor.fetchone():
        return
    cursor = conn.execute("PRAGMA table_info(memory)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "uuid" not in cols:
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            archived_at INTEGER,
            core INTEGER DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'manual',
            bridge_channel TEXT,
            code_anchors TEXT,
            synthesis_note TEXT,
            supersedes TEXT,
            superseded_by TEXT
        );
        INSERT OR IGNORE INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note)
            SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note FROM memory;
        DROP TABLE memory;
        CREATE INDEX IF NOT EXISTS idx_memories_agent_topic ON memories(agent_id, topic);
        CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_memories_memory_id ON memories(memory_id);
        CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
        CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);
    """)
    conn.commit()


def _backfill_memory_links(conn: sqlite3.Connection):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_links'"
    )
    if not cursor.fetchone():
        return

    now = int(time.time())
    rows = conn.execute(
        "SELECT memory_id, supersedes FROM memories WHERE supersedes IS NOT NULL"
    ).fetchall()
    for row in rows:
        memory_id = row[0]
        supersedes_str = row[1]
        if supersedes_str:
            parent_ids = [pid.strip() for pid in supersedes_str.split(",") if pid.strip()]
            for parent_id in parent_ids:
                link_id = uuid7()
                with contextlib.suppress(sqlite3.IntegrityError):
                    conn.execute(
                        "INSERT OR IGNORE INTO memory_links (link_id, memory_id, parent_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
                        (link_id, memory_id, parent_id, "supersedes", now),
                    )


db.register("memory", MEMORY_DB_NAME, _MEMORY_SCHEMA)

db.migrations(
    "memory",
    [
        ("migrate_memory_table_to_memories", _migrate_memory_table_to_memories),
        ("backfill_memory_links", _backfill_memory_links),
    ],
)


def connect():
    return db.ensure("memory")


def _resolve_memory_id(short_id: str) -> str:
    with connect() as conn:
        rows = conn.execute(
            "SELECT memory_id FROM memories WHERE memory_id LIKE ?", (f"%{short_id}",)
        ).fetchall()

    if not rows:
        raise ValueError(f"No entry found with ID ending in '{short_id}'")

    if len(rows) > 1:
        ambiguous_ids = [row[0] for row in rows]
        raise ValueError(f"Ambiguous ID: '{short_id}' matches multiple entries: {ambiguous_ids}")

    return rows[0][0]


def add_entry(agent_id: str, topic: str, message: str, core: bool = False, source: str = "manual"):
    memory_id = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, agent_id, topic, message, ts, now, 1 if core else 0, source),
        )
    events.emit(
        "memory", "note_add", agent_id, f"{topic}:{message[:50]}" + (" [CORE]" if core else "")
    )
    return memory_id


def _row_to_memory(row: dict) -> Memory:
    return Memory(
        memory_id=row["memory_id"],
        agent_id=row["agent_id"],
        topic=row["topic"],
        message=row["message"],
        timestamp=row["timestamp"],
        created_at=row["created_at"],
        archived_at=row["archived_at"],
        core=bool(row["core"]),
        source=row["source"],
        bridge_channel=row["bridge_channel"],
        code_anchors=row["code_anchors"],
        synthesis_note=row["synthesis_note"],
        supersedes=row["supersedes"],
        superseded_by=row["superseded_by"],
    )


def get_memories(
    identity: str,
    topic: str | None = None,
    include_archived: bool = False,
    limit: int | None = None,
) -> list[Memory]:
    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        raise ValueError(f"Agent '{identity}' not found.")

    with connect() as conn:
        params = [agent_id]
        query = "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE agent_id = ?"
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if not include_archived:
            query += " AND archived_at IS NULL"
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_memory(row) for row in rows]


def edit_entry(memory_id: str, new_message: str):
    full_id = _resolve_memory_id(memory_id)
    entry = get_by_memory_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "UPDATE memories SET message = ?, timestamp = ? WHERE memory_id = ? ",
            (new_message, ts, full_id),
        )
    events.emit("memory", "note_edit", entry.agent_id, f"{full_id[-8:]}")


def delete_entry(memory_id: str):
    full_id = _resolve_memory_id(memory_id)
    entry = get_by_memory_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    with connect() as conn:
        conn.execute("DELETE FROM memories WHERE memory_id = ?", (full_id,))
    events.emit("memory", "note_delete", entry.agent_id, f"{full_id[-8:]}")


def clear_entries(identity: str, topic: str | None = None):
    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        raise ValueError(f"Agent '{identity}' not found.")
    with connect() as conn:
        if topic:
            conn.execute("DELETE FROM memories WHERE agent_id = ? AND topic = ?", (agent_id, topic))
        else:
            conn.execute("DELETE FROM memories WHERE agent_id = ?", (agent_id,))


def archive_entry(memory_id: str):
    full_id = _resolve_memory_id(memory_id)
    entry = get_by_memory_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            "UPDATE memories SET archived_at = ? WHERE memory_id = ?",
            (now, full_id),
        )
    events.emit("memory", "note_archive", entry.agent_id, f"{full_id[-8:]}")


def restore_entry(memory_id: str):
    full_id = _resolve_memory_id(memory_id)
    entry = get_by_memory_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    with connect() as conn:
        conn.execute(
            "UPDATE memories SET archived_at = NULL WHERE memory_id = ?",
            (full_id,),
        )
    events.emit("memory", "note_restore", entry.agent_id, f"{full_id[-8:]}")


def mark_core(memory_id: str, core: bool = True):
    full_id = _resolve_memory_id(memory_id)
    entry = get_by_memory_id(full_id)
    if not entry:
        raise ValueError(f"Entry with ID '{memory_id}' not found.")
    with connect() as conn:
        conn.execute(
            "UPDATE memories SET core = ? WHERE memory_id = ?",
            (1 if core else 0, full_id),
        )
    events.emit("memory", "note_core", entry.agent_id, f"{full_id[-8:]} → {core}")


def get_core_entries(identity: str) -> list[Memory]:
    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    with connect() as conn:
        rows = conn.execute(
            "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE agent_id = ? AND core = 1 AND archived_at IS NULL ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_memory(row) for row in rows]


def get_recent_entries(identity: str, days: int = 7, limit: int = 20) -> list[Memory]:
    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    cutoff = int(time.time()) - (days * 86400)
    with connect() as conn:
        rows = conn.execute(
            "SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE agent_id = ? AND created_at >= ? AND archived_at IS NULL ORDER BY created_at DESC LIMIT ?",
            (agent_id, cutoff, limit),
        ).fetchall()
    return [_row_to_memory(row) for row in rows]


def search_entries(identity: str, keyword: str, include_archived: bool = False) -> list[Memory]:
    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT memory_id, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, synthesis_note, supersedes, superseded_by FROM memories WHERE agent_id = ? AND (message LIKE ? OR topic LIKE ?) {archive_filter} ORDER BY created_at DESC",
            (agent_id, f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    return [_row_to_memory(row) for row in rows]


def find_related(
    entry: Memory, limit: int = 5, include_archived: bool = False
) -> list[tuple[Memory, int]]:
    from ..lib.text_utils import stopwords

    tokens = set(entry.message.lower().split()) | set(entry.topic.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    agent_id = entry.agent_id

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        try:
            conn.execute("CREATE TEMPORARY TABLE keywords (keyword TEXT)")
            conn.executemany("INSERT INTO keywords VALUES (?)", [(k,) for k in keywords])

            query = f"""
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp, m.created_at, m.archived_at, m.core, m.source, m.bridge_channel, m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by, COUNT(k.keyword) as score
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


def get_by_memory_id(memory_id: str) -> Memory | None:
    full_id = _resolve_memory_id(memory_id)
    with connect() as conn:
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
    full_old_ids = [_resolve_memory_id(old_id) for old_id in old_ids]
    new_id = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    with connect() as conn:
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
                link_id = uuid7()
                conn.execute(
                    "INSERT OR IGNORE INTO memory_links (link_id, memory_id, parent_id, kind, created_at) VALUES (?, ?, ?, ?, ?)",
                    (link_id, new_id, full_old_id, "supersedes", now),
                )
                conn.execute(
                    "UPDATE memories SET archived_at = ?, superseded_by = ? WHERE memory_id = ?",
                    (now, new_id, full_old_id),
                )

    events.emit("memory", "note_replace", agent_id, f"{len(old_ids)} archived, new: {new_id[-8:]}")
    return new_id


def get_chain(memory_id: str) -> dict:
    """Get the full lineage (predecessors and successors) for a given memory_id."""
    full_id = _resolve_memory_id(memory_id)
    predecessors = []
    successors = []
    visited = set()

    def _traverse_predecessors(current_id: str):
        if current_id in visited:
            return
        visited.add(current_id)
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp,
                       m.created_at, m.archived_at, m.core, m.source, m.bridge_channel,
                       m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by
                FROM memory_links l
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
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT m.memory_id, m.agent_id, m.topic, m.message, m.timestamp,
                       m.created_at, m.archived_at, m.core, m.source, m.bridge_channel,
                       m.code_anchors, m.synthesis_note, m.supersedes, m.superseded_by
                FROM memory_links l
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

    start_entry = get_by_memory_id(full_id)
    return {"start_entry": start_entry, "predecessors": predecessors, "successors": successors}
