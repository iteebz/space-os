from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..lib import db as libdb
from ..lib.ids import uuid7
from ..spawn import config as spawn_config

KNOWLEDGE_DB_NAME = "knowledge.db"

_KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    contributor TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_contributor ON knowledge(contributor);
"""


@dataclass
class Entry:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def database_path() -> Path:
    return libdb.workspace_db_path(spawn_config.workspace_root(), KNOWLEDGE_DB_NAME)


def connect():
    return libdb.workspace_db(spawn_config.workspace_root(), KNOWLEDGE_DB_NAME, _KNOWLEDGE_SCHEMA)


def write_knowledge(
    domain: str, contributor: str, content: str, confidence: float | None = None
) -> str:
    from .. import events

    entry_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence),
        )
        conn.commit()
    events.emit("knowledge", "entry.write", contributor, f"{domain}:{content[:50]}")
    return entry_id


def query_by_domain(domain: str) -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE domain = ? ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
    return [Entry(*row) for row in rows]


def query_by_contributor(contributor: str) -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE contributor = ? ORDER BY created_at DESC",
            (contributor,),
        ).fetchall()
    return [Entry(*row) for row in rows]


def list_all() -> list[Entry]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge ORDER BY created_at DESC"
        ).fetchall()
    return [Entry(*row) for row in rows]


def get_by_id(entry_id: str) -> Entry | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE id = ?",
            (entry_id,),
        ).fetchone()
    return Entry(*row) if row else None


def find_related(entry: Entry, limit: int = 5) -> list[tuple[Entry, int]]:
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "as", "by", "from", "not", "all", "each", "every", "some", "any", "no", "none"}
    
    tokens = set(entry.content.lower().split()) | set(entry.domain.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}
    
    if not keywords:
        return []
    
    with connect() as conn:
        all_entries = conn.execute(
            "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE id != ?",
            (entry.id,),
        ).fetchall()
    
    scored = []
    for row in all_entries:
        candidate = Entry(*row)
        candidate_tokens = set(candidate.content.lower().split()) | set(candidate.domain.lower().split())
        candidate_keywords = {t.strip(".,;:!?()[]{}") for t in candidate_tokens if len(t) > 3 and t not in stopwords}
        
        overlap = len(keywords & candidate_keywords)
        if overlap > 0:
            scored.append((candidate, overlap))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
