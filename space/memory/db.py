from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from .. import events
from ..lib import db as libdb
from ..lib.ids import uuid7
from ..spawn import config as spawn_config
from .models import Entry

MEMORY_DB_NAME = "memory.db"

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    archived_at INTEGER,
    core INTEGER DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'manual',
    bridge_channel TEXT,
    code_anchors TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_identity_topic ON memory(identity, topic);
CREATE INDEX IF NOT EXISTS idx_memory_identity_created ON memory(identity, created_at);
CREATE INDEX IF NOT EXISTS idx_memory_uuid ON memory(uuid);
CREATE INDEX IF NOT EXISTS idx_memory_archived ON memory(archived_at);
CREATE INDEX IF NOT EXISTS idx_memory_core ON memory(core);
"""


def database_path() -> Path:
    return libdb.workspace_db_path(spawn_config.workspace_root(), MEMORY_DB_NAME)


def connect():
    db_path = database_path()
    if db_path.exists():
        _migrate_schema(db_path)
    return libdb.workspace_db(spawn_config.workspace_root(), MEMORY_DB_NAME, _MEMORY_SCHEMA)


def _migrate_schema(db_path: Path):
    with libdb.connect(db_path) as conn:
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


def add_entry(identity: str, topic: str, message: str, core: bool = False, source: str = "manual"):
    entry_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, identity, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (entry_uuid, identity, topic, message, ts, now, 1 if core else 0, source),
        )
        conn.commit()
    events.emit(
        "memory", "entry.add", identity, f"{topic}:{message[:50]}" + (" [CORE]" if core else "")
    )


def add_checkpoint_entry(
    identity: str,
    topic: str,
    message: str,
    bridge_channel: str | None = None,
    code_anchors: str | None = None,
):
    entry_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, identity, topic, message, timestamp, created_at, core, source, bridge_channel, code_anchors) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry_uuid,
                identity,
                topic,
                message,
                ts,
                now,
                0,
                "checkpoint",
                bridge_channel,
                code_anchors,
            ),
        )
        conn.commit()
    events.emit("memory", "entry.add", identity, f"{topic}:{message[:50]} [CHECKPOINT]")


def get_entries(
    identity: str, topic: str | None = None, include_archived: bool = False
) -> list[Entry]:
    with connect() as conn:
        archive_filter = "" if include_archived else "AND archived_at IS NULL"
        if topic:
            rows = conn.execute(
                f"SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND topic = ? {archive_filter} ORDER BY uuid",
                (identity, topic),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? {archive_filter} ORDER BY topic, uuid",
                (identity,),
            ).fetchall()
    return [
        Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
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
    with connect() as conn:
        if topic:
            conn.execute("DELETE FROM memory WHERE identity = ? AND topic = ?", (identity, topic))
        else:
            conn.execute("DELETE FROM memory WHERE identity = ?", (identity,))
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


def get_core_entries(identity: str) -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND core = 1 AND archived_at IS NULL ORDER BY created_at DESC",
            (identity,),
        ).fetchall()
    return [
        Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
        )
        for row in rows
    ]


def get_recent_entries(identity: str, days: int = 7, limit: int = 20) -> list[Entry]:
    cutoff = int(time.time()) - (days * 86400)
    with connect() as conn:
        rows = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND created_at >= ? AND archived_at IS NULL ORDER BY created_at DESC LIMIT ?",
            (identity, cutoff, limit),
        ).fetchall()
    return [
        Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
        )
        for row in rows
    ]


def search_entries(identity: str, keyword: str, include_archived: bool = False) -> list[Entry]:
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND (message LIKE ? OR topic LIKE ?) {archive_filter} ORDER BY created_at DESC",
            (identity, f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
    return [
        Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
        )
        for row in rows
    ]


def find_related(
    entry: Entry, limit: int = 5, include_archived: bool = False
) -> list[tuple[Entry, int]]:
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

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        all_entries = conn.execute(
            f"SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND uuid != ? {archive_filter}",
            (entry.identity, entry.uuid),
        ).fetchall()

    scored = []
    for row in all_entries:
        candidate = Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
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


def get_by_uuid(entry_uuid: str) -> Entry | None:
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        row = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE uuid = ?",
            (full_uuid,),
        ).fetchone()
    return (
        Entry(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            bool(row[7]),
            row[8],
            row[9],
            row[10],
        )
        if row
        else None
    )
