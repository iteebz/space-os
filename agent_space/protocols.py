import hashlib
import sqlite3
import time
from pathlib import Path


DB_PATH = Path.cwd() / ".space" / "protocols.db"


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS protocol_versions (
            name TEXT,
            hash TEXT,
            timestamp INTEGER,
            PRIMARY KEY (name, hash)
        )
        """
    )
    conn.commit()
    conn.close()


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def track(name: str, content: str):
    """Track protocol version by hashing content. Idempotent."""
    _init_db()
    
    content_hash = _hash_content(content)
    now = int(time.time())
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO protocol_versions (name, hash, timestamp) VALUES (?, ?, ?)",
            (name, content_hash, now),
        )
        conn.commit()
    finally:
        conn.close()


def get_current_hash(name: str) -> str | None:
    """Get most recent hash for a protocol."""
    if not DB_PATH.exists():
        return None
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT hash FROM protocol_versions WHERE name = ? ORDER BY timestamp DESC LIMIT 1",
            (name,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def list_protocols() -> list[tuple[str, str, int]]:
    """List all protocols with their latest hash and timestamp."""
    if not DB_PATH.exists():
        return []
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT name, hash, timestamp 
            FROM protocol_versions 
            WHERE (name, timestamp) IN (
                SELECT name, MAX(timestamp) 
                FROM protocol_versions 
                GROUP BY name
            )
            ORDER BY name
            """
        )
        return cur.fetchall()
    finally:
        conn.close()
