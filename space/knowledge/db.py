from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..lib import db, paths
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
    return Knowledge(
        knowledge_id=row["knowledge_id"],
        domain=row["domain"],
        agent_id=row["agent_id"],
        content=row["content"],
        confidence=row["confidence"],
        created_at=row["created_at"],
        archived_at=row["archived_at"],
    )


def database_path() -> Path:
    return paths.dot_space() / KNOWLEDGE_DB_NAME


def connect():
    import sqlite3

    db_path = database_path()
    db.ensure_schema(db_path, _KNOWLEDGE_SCHEMA)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _run_migrations(conn)
    return db.connect(db_path)


def _run_migrations(conn):
    cursor = conn.execute("PRAGMA table_info(knowledge)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "id" in cols and "knowledge_id" not in cols:
        conn.execute("ALTER TABLE knowledge RENAME COLUMN id TO knowledge_id")
        conn.commit()


def write_knowledge(
    domain: str, agent_id: str, content: str, confidence: float | None = None
) -> str:
    from .. import events

    knowledge_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content, confidence),
        )
        conn.commit()
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
    import time

    now = int(time.time())
    with connect() as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
            (now, knowledge_id),
        )
        conn.commit()
    from .. import events

    events.emit("knowledge", "entry.archive", None, f"{knowledge_id[-8:]}")


def restore_entry(knowledge_id: str):
    with connect() as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = NULL WHERE knowledge_id = ?",
            (knowledge_id,),
        )
        conn.commit()
    from .. import events

    events.emit("knowledge", "entry.restore", None, f"{knowledge_id[-8:]}")


def find_related(
    entry: Knowledge, limit: int = 5, include_archived: bool = False
) -> list[tuple[Knowledge, int]]:
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
