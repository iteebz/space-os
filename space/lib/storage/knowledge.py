import sqlite3
from dataclasses import dataclass

from ...lib.uuid7 import uuid7
from .context import connect


@dataclass
class Knowledge:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def write_knowledge(
    domain: str,
    contributor: str,
    content: str,
    confidence: float | None = None,
) -> str:
    import json

    from ..events import emit

    entry_id = uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence),
        )
        conn.commit()

    emit(
        source="knowledge",
        event_type="write",
        identity=contributor,
        data=json.dumps({"id": entry_id, "domain": domain}),
    )
    return entry_id


def query_by_domain(domain: str) -> list[Knowledge]:
    with connect(row_factory=sqlite3.Row) as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge WHERE domain = ? ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def query_by_contributor(contributor: str) -> list[Knowledge]:
    with connect(row_factory=sqlite3.Row) as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge WHERE contributor = ? ORDER BY created_at DESC",
            (contributor,),
        ).fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def list_all() -> list[Knowledge]:
    with connect(row_factory=sqlite3.Row) as conn:
        rows = conn.execute("SELECT * FROM knowledge ORDER BY created_at DESC").fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def get_by_id(entry_id: str) -> Knowledge | None:
    with connect(row_factory=sqlite3.Row) as conn:
        row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (entry_id,)).fetchone()
        if row:
            return Knowledge(**dict(row))
        return None
