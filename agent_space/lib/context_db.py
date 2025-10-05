from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from . import storage

CONTEXT_DB_NAME = "context.db"
CONTEXT_DB_PATH: Path = storage.database_path(CONTEXT_DB_NAME)
_MIGRATED = False

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_identity_topic ON memory(identity, topic);
CREATE INDEX IF NOT EXISTS idx_memory_identity_created ON memory(identity, created_at);
CREATE INDEX IF NOT EXISTS idx_memory_uuid ON memory(uuid);
"""

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


def set_context_db_path(path: Path) -> None:
    """Override context database path (test hook)."""
    global CONTEXT_DB_PATH, _MIGRATED
    CONTEXT_DB_PATH = path
    CONTEXT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MIGRATED = False


def ensure() -> None:
    """Ensure the context database exists, schema is applied, and legacy data migrated."""
    global _MIGRATED
    with sqlite3.connect(CONTEXT_DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_MEMORY_SCHEMA)
        conn.executescript(_KNOWLEDGE_SCHEMA)
        if not _MIGRATED:
            _migrate_legacy(conn)
            _MIGRATED = True
        conn.commit()


@contextmanager
def connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a connection to the context database, ensuring schema beforehand."""
    ensure()
    conn = sqlite3.connect(CONTEXT_DB_PATH)
    if row_factory is not None:
        conn.row_factory = row_factory
    try:
        yield conn
    finally:
        conn.close()


def _migrate_legacy(conn: sqlite3.Connection) -> None:
    _migrate_memory_legacy_files(conn)
    _migrate_knowledge_legacy_files(conn)
    _migrate_memory_old_table(conn)
    _migrate_knowledge_old_table(conn)


def _migrate_memory_legacy_files(conn: sqlite3.Connection) -> None:
    legacy_path = storage.database_path("memory.db")
    if not legacy_path.exists():
        return

    with sqlite3.connect(legacy_path) as legacy_conn:
        try:
            rows = legacy_conn.execute(
                "SELECT uuid, identity, topic, message, timestamp, created_at FROM entries"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []

    if rows:
        conn.executemany(
            "INSERT OR IGNORE INTO memory (uuid, identity, topic, message, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

    legacy_path.unlink(missing_ok=True)


def _migrate_knowledge_legacy_files(conn: sqlite3.Connection) -> None:
    legacy_path = storage.database_path("knowledge.db")
    if not legacy_path.exists():
        return

    with sqlite3.connect(legacy_path) as legacy_conn:
        try:
            rows = legacy_conn.execute(
                "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []

    if rows:
        conn.executemany(
            "INSERT OR IGNORE INTO knowledge (id, domain, contributor, content, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )

    legacy_path.unlink(missing_ok=True)


def _migrate_memory_old_table(conn: sqlite3.Connection) -> None:
    try:
        old_count = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
    except sqlite3.OperationalError:
        return
    
    if old_count == 0:
        return
    
    new_count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
    if new_count > 0:
        return
    
    rows = conn.execute("SELECT uuid, identity, topic, message, timestamp, created_at FROM memory_entries").fetchall()
    conn.executemany(
        "INSERT OR IGNORE INTO memory (uuid, identity, topic, message, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def _migrate_knowledge_old_table(conn: sqlite3.Connection) -> None:
    try:
        old_count = conn.execute("SELECT COUNT(*) FROM knowledge_entries").fetchone()[0]
    except sqlite3.OperationalError:
        return
    
    if old_count == 0:
        return
    
    new_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    if new_count > 0:
        return
    
    rows = conn.execute("SELECT id, domain, contributor, content, confidence, created_at FROM knowledge_entries").fetchall()
    conn.executemany(
        "INSERT OR IGNORE INTO knowledge (id, domain, contributor, content, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
