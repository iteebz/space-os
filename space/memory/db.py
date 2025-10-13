from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .. import events
from ..lib import db, paths
from ..lib.uuid7 import uuid7
from ..models import Memory

MEMORY_DB_NAME = "memory.db"

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    uuid TEXT PRIMARY KEY,
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
    supersedes TEXT,
    superseded_by TEXT,
    synthesis_note TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_agent_topic ON memory(agent_id, topic);
CREATE INDEX IF NOT EXISTS idx_memory_agent_created ON memory(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memory_uuid ON memory(uuid);
CREATE INDEX IF NOT EXISTS idx_memory_archived ON memory(archived_at);
CREATE INDEX IF NOT EXISTS idx_memory_core ON memory(core);
CREATE INDEX IF NOT EXISTS idx_memory_superseded_by ON memory(superseded_by);
"""


def database_path() -> Path:
    return paths.space_root() / MEMORY_DB_NAME


def connect():
    db_path = database_path()
    if not db_path.exists():
        db.ensure_schema(db_path, _MEMORY_SCHEMA)
    _migrate_schema(db_path)
    return db.connect(db_path)


def _migrate_schema(db_path: Path):
    with db.connect(db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(memory)")
        columns = {row[1] for row in cursor.fetchall()}

        if "archived_at" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN archived_at INTEGER")
            conn.commit()

        if "core" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN core INTEGER DEFAULT 0")
            conn.commit()

        if "source" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
            conn.commit()

        if "bridge_channel" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN bridge_channel TEXT")
            conn.commit()

        if "code_anchors" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN code_anchors TEXT")
            conn.commit()

        if "supersedes" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN supersedes TEXT")
            conn.commit()

        if "superseded_by" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN superseded_by TEXT")
            conn.commit()

        if "synthesis_note" not in columns:
            conn.execute("ALTER TABLE memory ADD COLUMN synthesis_note TEXT")
            conn.commit()


def _resolve_uuid(short_uuid: str) -> str:
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid FROM memory WHERE uuid LIKE ?", (f"%{short_uuid}",)
        ).fetchall()

    if not rows:
        raise ValueError(f"No entry found with UUID ending in '{short_uuid}'")

    if len(rows) > 1:
        ambiguous_uuids = [row[0] for row in rows]
        raise ValueError(
            f"Ambiguous UUID: '{short_uuid}' matches multiple entries: {ambiguous_uuids}"
        )

    return rows[0][0]


def add_entry(agent_id: str, topic: str, message: str, core: bool = False, source: str = "manual"):
    from ..spawn import registry

    identity = registry.get_agent_name(agent_id)
    if not identity:
        raise ValueError(f"No identity for agent_id {agent_id}")

    entry_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, agent_id, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_uuid, agent_id, topic, message, ts, now, 1 if core else 0, source),
        )
        conn.commit()
    events.emit(
        "memory", "entry.add", agent_id, f"{topic}:{message[:50]}" + (" [CORE]" if core else "")
    )


def get_entries(
    identity: str, topic: str | None = None, include_archived: bool = False
) -> list[Memory]:
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    with connect() as conn:
        archive_filter = "" if include_archived else "AND archived_at IS NULL"
        if topic:
            rows = conn.execute(
                f"SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? AND topic = ? {archive_filter} ORDER BY created_at ASC",
                (agent_id, topic),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? {archive_filter} ORDER BY topic, created_at ASC",
                (agent_id,),
            ).fetchall()
    return [
        Memory(
            row[0],
            identity,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        for row in rows
    ]


def edit_entry(entry_uuid: str, new_message: str):
    full_uuid = _resolve_uuid(entry_uuid)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "UPDATE memory SET message = ?, timestamp = ? WHERE uuid = ? ",
            (new_message, ts, full_uuid),
        )
        conn.commit()
    events.emit("memory", "entry.edit", None, f"{full_uuid[-8:]}")


def delete_entry(entry_uuid: str):
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        conn.execute("DELETE FROM memory WHERE uuid = ?", (full_uuid,))
        conn.commit()
    events.emit("memory", "entry.delete", None, f"{full_uuid[-8:]}")


def clear_entries(identity: str, topic: str | None = None):
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return

    with connect() as conn:
        if topic:
            conn.execute("DELETE FROM memory WHERE agent_id = ? AND topic = ?", (agent_id, topic))
        else:
            conn.execute("DELETE FROM memory WHERE agent_id = ?", (agent_id,))
        conn.commit()


def archive_entry(entry_uuid: str):
    full_uuid = _resolve_uuid(entry_uuid)
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            "UPDATE memory SET archived_at = ? WHERE uuid = ?",
            (now, full_uuid),
        )
        conn.commit()
    events.emit("memory", "entry.archive", None, f"{full_uuid[-8:]}")


def restore_entry(entry_uuid: str):
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        conn.execute(
            "UPDATE memory SET archived_at = NULL WHERE uuid = ?",
            (full_uuid,),
        )
        conn.commit()
    events.emit("memory", "entry.restore", None, f"{full_uuid[-8:]}")


def mark_core(entry_uuid: str, core: bool = True):
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        conn.execute(
            "UPDATE memory SET core = ? WHERE uuid = ?",
            (1 if core else 0, full_uuid),
        )
        conn.commit()
    events.emit("memory", "entry.core", None, f"{full_uuid[-8:]} → {core}")


def get_core_entries(identity: str) -> list[Memory]:
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? AND core = 1 AND archived_at IS NULL ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [
        Memory(
            row[0],
            identity,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        for row in rows
    ]


def get_recent_entries(identity: str, days: int = 7, limit: int = 20) -> list[Memory]:
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    cutoff = int(time.time()) - (days * 86400)
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? AND created_at >= ? AND archived_at IS NULL ORDER BY created_at DESC LIMIT ?",
            (agent_id, cutoff, limit),
        ).fetchall()
    return [
        Memory(
            row[0],
            identity,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        for row in rows
    ]


def search_entries(identity: str, keyword: str, include_archived: bool = False) -> list[Memory]:
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        return []

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? AND (message LIKE ? OR topic LIKE ?) {archive_filter} ORDER BY created_at DESC",
            (agent_id, f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    return [
        Memory(
            row[0],
            identity,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        for row in rows
    ]


def find_related(
    entry: Memory, limit: int = 5, include_archived: bool = False
) -> list[tuple[Memory, int]]:
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "as",
        "by",
        "from",
        "not",
        "all",
        "each",
        "every",
        "some",
        "any",
        "no",
        "none",
    }

    tokens = set(entry.message.lower().split()) | set(entry.topic.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    from ..spawn import registry

    agent_id = registry.get_agent_id(entry.identity)
    if not agent_id:
        return []

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        all_entries = conn.execute(
            f"SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE agent_id = ? AND uuid != ? {archive_filter}",
            (agent_id, entry.uuid),
        ).fetchall()

    scored = []
    for row in all_entries:
        candidate = Memory(
            row[0],
            entry.identity,
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        candidate_tokens = set(candidate.message.lower().split()) | set(
            candidate.topic.lower().split()
        )
        candidate_keywords = {
            t.strip(".,;:!?()[]{}") for t in candidate_tokens if len(t) > 3 and t not in stopwords
        }

        overlap = len(keywords & candidate_keywords)
        if overlap > 0:
            scored.append((candidate, overlap))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def get_by_uuid(entry_uuid: str) -> Memory | None:
    from ..spawn import registry

    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        row = conn.execute(
            "SELECT uuid, agent_id, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors, supersedes, superseded_by, synthesis_note FROM memory WHERE uuid = ?",
            (full_uuid,),
        ).fetchone()
    if not row:
        return None

    identity = registry.get_agent_name(row[1]) or row[1]
    return Memory(
        row[0],
        identity,
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        bool(row[7]),
        row[8],
        row[9],
        row[10],
        row[11],
        row[12],
        row[13],
    )


def replace_entry(
    old_ids: list[str], agent_id: str, topic: str, message: str, note: str = "", core: bool = False
) -> str:
    from ..spawn import registry

    identity = registry.get_agent_name(agent_id)
    if not identity:
        raise ValueError(f"No identity for agent_id {agent_id}")

    full_old_ids = [_resolve_uuid(old_id) for old_id in old_ids]
    supersedes_str = ",".join(full_old_ids)
    new_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    with connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, agent_id, topic, message, timestamp, created_at, core, source, supersedes, synthesis_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_uuid,
                agent_id,
                topic,
                message,
                ts,
                now,
                1 if core else 0,
                "manual",
                supersedes_str,
                note,
            ),
        )

        for full_old_id in full_old_ids:
            conn.execute(
                "UPDATE memory SET archived_at = ?, superseded_by = ? WHERE uuid = ?",
                (now, new_uuid, full_old_id),
            )

        conn.commit()

    events.emit("memory", "entry.replace", agent_id, f"{len(old_ids)} → {new_uuid[-8:]}")
    return new_uuid


def get_chain(entry_uuid: str) -> dict:
    full_uuid = _resolve_uuid(entry_uuid)
    entry = get_by_uuid(full_uuid)
    if not entry:
        return {"current": None, "predecessors": [], "successor": None}

    predecessors = []
    if entry.supersedes:
        pred_ids = entry.supersedes.split(",")
        for pred_id in pred_ids:
            pred = get_by_uuid(pred_id.strip())
            if pred:
                predecessors.append(pred)

    successor = None
    if entry.superseded_by:
        successor = get_by_uuid(entry.superseded_by)

    return {"current": entry, "predecessors": predecessors, "successor": successor}
