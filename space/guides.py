import sqlite3
import time
from pathlib import Path

from space.lib.uuid7 import uuid7
from space.lib import hashing

DB_PATH = Path.cwd() / ".space" / "guides.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS guide_versions (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (name, hash)
);
"""


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        _migrate_schema(conn)
    finally:
        conn.close()


def _migrate_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='guide_versions'"
    )
    exists = cur.fetchone() is not None

    if not exists:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return

    columns = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(guide_versions)")}
    if "uuid" in columns and "created_at" in columns:
        # Already on the latest schema.
        return

    conn.execute("ALTER TABLE guide_versions RENAME TO guide_versions_legacy")
    conn.executescript(SCHEMA_SQL)

    legacy_rows = conn.execute(
        "SELECT name, hash, timestamp FROM guide_versions_legacy ORDER BY timestamp"
    ).fetchall()
    for name, content_hash, timestamp in legacy_rows:
        created_at = int(timestamp) if timestamp is not None else int(time.time())
        conn.execute(
            "INSERT INTO guide_versions (uuid, name, hash, created_at) VALUES (?, ?, ?, ?)",
            (uuid7(), name, content_hash, created_at),
        )

    conn.execute("DROP TABLE guide_versions_legacy")
    conn.commit()




def track(name: str, content: str):
    """Track protocol version by hashing content. Idempotent. Fails silently."""
    try:
        _init_db()
        content_hash = hashing.sha256(content, 16)
        created_at = int(time.time())

        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO protocol_versions (uuid, name, hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (uuid7(), name, content_hash, created_at),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def get_current_hash(name: str) -> str | None:
    """Get most recent hash for a protocol."""
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT hash
            FROM guide_versions
            WHERE name = ?
            ORDER BY uuid DESC
            LIMIT 1
            """,
            (name,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_guides() -> list[tuple[str, str, int]]:
    """List all protocols with their latest hash and timestamp."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT p.name, p.hash, p.created_at
            FROM guide_versions AS p
            WHERE p.uuid = (
                SELECT MAX(uuid)
                FROM guide_versions
                WHERE name = p.name
            )
            ORDER BY name
            """
        )
        return cur.fetchall()
    finally:
        conn.close()
