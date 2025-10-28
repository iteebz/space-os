"""Knowledge operations: pure business logic, zero typer imports.

Contains all database operations and business logic.
Callers: commands.py only.
"""

from __future__ import annotations

from datetime import datetime

from space.core.models import Knowledge
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7
from space.os import spawn


def _row_to_knowledge(row: dict) -> Knowledge:
    return from_row(row, Knowledge)


def add_entry(domain: str, agent_id: str, content: str, confidence: float | None = None) -> str:
    """Add new knowledge entry. Returns entry_id."""
    knowledge_id = uuid7()
    with store.ensure("knowledge") as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content, confidence),
        )
    spawn.api.touch_agent(agent_id)
    return knowledge_id


def list_entries(show_all: bool = False) -> list[Knowledge]:
    """List all knowledge entries."""
    archive_filter = "" if show_all else "WHERE archived_at IS NULL"
    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge {archive_filter} ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_by_domain(domain: str, show_all: bool = False) -> list[Knowledge]:
    """Query knowledge entries by domain."""
    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE domain = ? {archive_filter} ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_by_agent(agent_id: str, show_all: bool = False) -> list[Knowledge]:
    """Query knowledge entries by agent."""
    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE agent_id = ? {archive_filter} ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def get_by_id(entry_id: str) -> Knowledge | None:
    """Get knowledge entry by its UUID."""
    with store.ensure("knowledge") as conn:
        row = conn.execute(
            "SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE knowledge_id = ?",
            (entry_id,),
        ).fetchone()
    return _row_to_knowledge(row) if row else None


def find_related(
    entry: Knowledge, limit: int = 5, show_all: bool = False
) -> list[tuple[Knowledge, int]]:
    """Find related entries via keyword similarity."""
    from space.lib.text_utils import stopwords

    tokens = set(entry.content.lower().split()) | set(entry.domain.lower().split())
    keywords = {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > 3 and t not in stopwords}

    if not keywords:
        return []

    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure("knowledge") as conn:
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


def archive_entry(entry_id: str) -> None:
    """Archive a knowledge entry."""
    now = datetime.now().isoformat()
    with store.ensure("knowledge") as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
            (now, entry_id),
        )


def restore_entry(entry_id: str) -> None:
    """Restore an archived knowledge entry."""
    with store.ensure("knowledge") as conn:
        conn.execute(
            "UPDATE knowledge SET archived_at = NULL WHERE knowledge_id = ?",
            (entry_id,),
        )
