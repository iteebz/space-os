"""Knowledge operations: discovered patterns and insights across domains."""

from datetime import datetime

from space.core.models import Knowledge
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7
from space.os import spawn


def _row_to_knowledge(row: dict) -> Knowledge:
    return from_row(row, Knowledge)


def add_knowledge(domain: str, agent_id: str, content: str, confidence: float | None = None) -> str:
    """Add knowledge entry in domain. Returns knowledge_id."""
    knowledge_id = uuid7()
    with store.ensure("knowledge") as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content, confidence),
        )
    spawn.api.touch_agent(agent_id)
    return knowledge_id


def list_knowledge(show_all: bool = False) -> list[Knowledge]:
    """List all knowledge entries."""
    archive_filter = "" if show_all else "WHERE archived_at IS NULL"
    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge {archive_filter} ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_knowledge(domain: str, show_all: bool = False) -> list[Knowledge]:
    """Query knowledge entries by domain (supports wildcard paths like 'architecture/*')."""
    archive_filter = "" if show_all else "AND archived_at IS NULL"

    if domain.endswith("/*"):
        domain_prefix = domain[:-2]
        where_clause = f"WHERE (domain = ? OR domain LIKE ?) {archive_filter}"
        params = (domain_prefix, f"{domain_prefix}/%")
    else:
        where_clause = f"WHERE domain = ? {archive_filter}"
        params = (domain,)

    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge {where_clause} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_knowledge_by_agent(agent_id: str, show_all: bool = False) -> list[Knowledge]:
    """Query knowledge entries by agent."""
    archive_filter = "" if show_all else "AND archived_at IS NULL"
    with store.ensure("knowledge") as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE agent_id = ? {archive_filter} ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def get_knowledge(entry_id: str) -> Knowledge | None:
    """Get knowledge entry by its UUID."""
    with store.ensure("knowledge") as conn:
        row = conn.execute(
            "SELECT knowledge_id, domain, agent_id, content, confidence, created_at, archived_at FROM knowledge WHERE knowledge_id = ?",
            (entry_id,),
        ).fetchone()
    return _row_to_knowledge(row) if row else None


def find_related_knowledge(
    entry: Knowledge, limit: int = 5, show_all: bool = False
) -> list[tuple[Knowledge, int]]:
    """Find knowledge related by keyword similarity."""
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


def archive_knowledge(entry_id: str, restore: bool = False) -> None:
    """Archive or restore knowledge entry."""
    if restore:
        with store.ensure("knowledge") as conn:
            conn.execute(
                "UPDATE knowledge SET archived_at = NULL WHERE knowledge_id = ?",
                (entry_id,),
            )
    else:
        now = datetime.now().isoformat()
        with store.ensure("knowledge") as conn:
            conn.execute(
                "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
                (now, entry_id),
            )


def get_domain_tree(parent_domain: str | None = None, show_all: bool = False) -> dict:
    """Get hierarchical domain tree, optionally filtered by parent domain."""
    archive_filter = "" if show_all else "WHERE archived_at IS NULL"

    with store.ensure("knowledge") as conn:
        if parent_domain:
            prefix = f"{parent_domain}/"
            rows = conn.execute(
                f"SELECT DISTINCT domain FROM knowledge WHERE domain LIKE ? {archive_filter} ORDER BY domain",
                (f"{prefix}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT DISTINCT domain FROM knowledge {archive_filter} ORDER BY domain"
            ).fetchall()

    domains = [row[0] for row in rows]
    tree = {}
    for domain in domains:
        parts = domain.split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]

    return tree
