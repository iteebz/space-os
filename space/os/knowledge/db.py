from __future__ import annotations

import time
from pathlib import Path

from space.os import db
from space.os.db import from_row
from space.os.lib.uuid7 import uuid7

from .. import events
from ..lib import paths
from ..models import Knowledge
from . import migrations


def schema() -> str:
    """Knowledge database schema."""
    return """
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


def _row_to_knowledge(row: dict) -> Knowledge:
    return from_row(row, Knowledge)


def path() -> Path:
    return paths.dot_space() / "knowledge.db"


db.register("knowledge", "knowledge.db", schema())
db.add_migrations("knowledge", migrations.MIGRATIONS)


def write_knowledge(
    domain: str, agent_id: str, content: str, confidence: float | None = None
) -> str:
    knowledge_id = uuid7()
    with db.ensure("knowledge") as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content, confidence),
        )
    events.emit("knowledge", "entry.write", agent_id, f"{domain}:{content[:50]}")
    return knowledge_id


def query_by_domain(domain: str, include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with db.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE domain = ? {archive_filter} ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_by_agent(agent_id: str, include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    with db.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE agent_id = ? {archive_filter} ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def list_all(include_archived: bool = False) -> list[Knowledge]:
    archive_filter = "" if include_archived else "WHERE archived_at IS NULL"
    with db.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge {archive_filter} ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def get_by_id(knowledge_id: str) -> Knowledge | None:
    with db.ensure("knowledge") as conn:
        row = conn.execute(
            "SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
    return _row_to_knowledge(row) if row else None


def archive_entry(knowledge_id: str):
    now = int(time.time())
    with db.ensure("knowledge") as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
            (now, knowledge_id),
        )


def restore_entry(knowledge_id: str):
    with db.ensure("knowledge") as conn:
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
    with db.ensure("knowledge") as conn:
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
