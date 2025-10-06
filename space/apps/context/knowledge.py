import sqlite3
from dataclasses import dataclass

from space import events
from space.lib import uuid7

from .db import connect


@dataclass
class Knowledge:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def write(
    domain: str,
    contributor: str,
    content: str,
    confidence: float | None = None,
) -> str:
    entry_id = uuid7.uuid7()
    with connect() as conn:
        conn.execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence) VALUES (?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence),
        )
        conn.commit()

    events.track(
        source="knowledge",
        event_type="write",
        identity=contributor,
        data={"id": entry_id, "domain": domain},
    )
    return entry_id


def query(
    domain: str | None = None,
    contributor: str | None = None,
    entry_id: str | None = None,
) -> list[Knowledge]:
    with connect(row_factory=sqlite3.Row) as conn:
        if entry_id:
            row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (entry_id,)).fetchone()
            return [Knowledge(**dict(row))] if row else []
        if domain:
            rows = conn.execute(
                "SELECT * FROM knowledge WHERE domain = ? ORDER BY created_at DESC",
                (domain,),
            ).fetchall()
            return [Knowledge(**dict(row)) for row in rows]
        if contributor:
            rows = conn.execute(
                "SELECT * FROM knowledge WHERE contributor = ? ORDER BY created_at DESC",
                (contributor,),
            ).fetchall()
            return [Knowledge(**dict(row)) for row in rows]
        rows = conn.execute("SELECT * FROM knowledge ORDER BY created_at DESC").fetchall()
        return [Knowledge(**dict(row)) for row in rows]
