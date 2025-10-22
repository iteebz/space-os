from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from space import db
from space.db import from_row

from .. import events
from ..lib import paths
from ..lib.uuid7 import uuid7

KNOWLEDGE_DB_NAME = "knowledge.db"

_KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);
"""


@dataclass
class Knowledge:
    knowledge_id: str
    domain: str
    agent_id: str
    content: str
    confidence: float | None
    created_at: str
    archived_at: int | None = None


def _row_to_knowledge(row: dict) -> Knowledge:
    return from_row(row, Knowledge)


def database_path() -> Path:
    return paths.dot_space() / KNOWLEDGE_DB_NAME


def _migrate_id_to_knowledge_id(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(knowledge)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "id" in cols and "knowledge_id" not in cols:
        conn.execute("ALTER TABLE knowledge RENAME COLUMN id TO knowledge_id")


db.register("knowledge", KNOWLEDGE_DB_NAME, _KNOWLEDGE_SCHEMA)

db.add_migrations(
    "knowledge",
    [
        ("migrate_id_to_knowledge_id", _migrate_id_to_knowledge_id),
    ],
)


def connect():
    return db.ensure("knowledge")


def write_knowledge(
    domain: str, agent_id: str, content: str, confidence: float | None = None
) -> str:
    knowledge_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content, confidence),
        )
    events.emit("knowledge", "entry.write", agent_id, f"{domain}:{content[:50]}")
    return knowledge_id


def query_by_domain(domain: str, include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE domain = ? {archive_filter} ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_by_agent(agent_id: str, include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE agent_id = ? {archive_filter} ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def list_all(include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "WHERE archived_at IS NULL"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge {archive_filter} ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def get_by_id(knowledge_id: str) -> Knowledge | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
    return _row_to_knowledge(row) if row else None


def archive_entry(knowledge_id: str):
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
            (now, knowledge_id),
        )


def restore_entry(knowledge_id: str):
    with connect() as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = NULL WHERE knowledge_id = ?",
            (knowledge_id,),
        )


def find_related(
    entry: Knowledge, limit: int = 5, include_archived: bool = False
) -> list[tuple[Knowledge, int]]:
    from ..lib.text_utils import stopwords

    tokens = set(entry.content.lower().split()) | set(entry.domain.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with connect() as conn:
        all_entries = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE knowledge_id != ? {archive_filter}",
            (entry.knowledge_id,),
        ).fetchall()

    scored = []
    for row in all_entries:
        candidate = _row_to_knowledge(row)
        candidate_tokens = set(candidate.content.lower().split()) | set(
            candidate.domain.lower().split()
        )
        candidate_keywords = {
            t.strip(".,;:!?()[]{}") for t in candidate_tokens if len(t) > 3 and t not in stopwords
        }

        overlap = len(keywords & candidate_keywords)
        if overlap > 0:
            scored.append((candidate, overlap))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
