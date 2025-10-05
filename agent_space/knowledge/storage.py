import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from ..lib.ids import uuid7
from . import config


@dataclass
class Knowledge:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str


def init_db():
    config.knowledge_db().parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                contributor TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain ON knowledge(domain)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_contributor ON knowledge(contributor)
        """)
        conn.commit()


@contextmanager
def get_db():
    conn = sqlite3.connect(config.knowledge_db())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def write_knowledge(
    domain: str,
    contributor: str,
    content: str,
    confidence: float | None = None,
) -> str:
    entry_id = uuid7()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO knowledge (id, domain, contributor, content, confidence)
            VALUES (?, ?, ?, ?, ?)
        """,
            (entry_id, domain, contributor, content, confidence),
        )
        conn.commit()

    import json

    from ..events import emit

    emit(
        source="knowledge",
        event_type="write",
        identity=contributor,
        data=json.dumps({"id": entry_id, "domain": domain}),
    )

    return entry_id


def query_by_domain(domain: str) -> list[Knowledge]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge WHERE domain = ? ORDER BY created_at DESC",
            (domain,),
        ).fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def query_by_contributor(contributor: str) -> list[Knowledge]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge WHERE contributor = ? ORDER BY created_at DESC",
            (contributor,),
        ).fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def list_all() -> list[Knowledge]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM knowledge ORDER BY created_at DESC").fetchall()
        return [Knowledge(**dict(row)) for row in rows]


def get_by_id(entry_id: str) -> Knowledge | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM knowledge WHERE id = ?", (entry_id,)).fetchone()
        if row:
            return Knowledge(**dict(row))
        return None
