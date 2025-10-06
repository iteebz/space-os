from ...lib import hashing
import sqlite3
import time
from pathlib import Path

from space.lib.uuid7 import uuid7
from space.lib import hashing

DB_PATH = Path.cwd() / ".space" / "constitutions.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS constitution_versions (
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
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()




def track(name: str, content: str):
    """Track constitution version by hashing content. Idempotent. Fails silently."""
    try:
        _init_db()
        content_hash = hashing.sha256(content, 16)
        created_at = int(time.time())

        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO constitution_versions (uuid, name, hash, created_at)
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
    """Get most recent hash for a constitution."""
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT hash
            FROM constitution_versions
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


def list_constitutions() -> list[tuple[str, str, int]]:
    """List all constitutions with their latest hash and timestamp."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT p.name, p.hash, p.created_at
            FROM constitution_versions AS p
            WHERE p.uuid = (
                SELECT MAX(uuid)
                FROM constitution_versions
                WHERE name = p.name
            )
            ORDER BY name
            """
        )
        return cur.fetchall()
    finally:
        conn.close()
