import hashlib
import time

from .lib import db as libdb
from .lib.ids import uuid7
from .spawn import config as spawn_config

DB_PATH = spawn_config.workspace_root() / ".space" / "protocols.db"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS protocol_versions (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (name, hash)
);
"""


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with libdb.connect(DB_PATH) as conn:
        _migrate_schema(conn)


def _migrate_schema(conn) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='protocol_versions'"
    )
    exists = cur.fetchone() is not None

    if not exists:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        return

    columns = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(protocol_versions)")}
    if "uuid" in columns and "created_at" in columns:
        # Already on the latest schema.
        return

    conn.execute("ALTER TABLE protocol_versions RENAME TO protocol_versions_legacy")
    conn.executescript(SCHEMA_SQL)

    legacy_rows = conn.execute(
        "SELECT name, hash, timestamp FROM protocol_versions_legacy ORDER BY timestamp"
    ).fetchall()
    for name, content_hash, timestamp in legacy_rows:
        created_at = int(timestamp) if timestamp is not None else int(time.time())
        conn.execute(
            "INSERT INTO protocol_versions (uuid, name, hash, created_at) VALUES (?, ?, ?, ?)",
            (uuid7(), name, content_hash, created_at),
        )

    conn.execute("DROP TABLE protocol_versions_legacy")
    conn.commit()


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def track(name: str, content: str):
    """Track protocol version by hashing content. Idempotent."""
    _init_db()
    content_hash = _hash_content(content)
    created_at = int(time.time())

    with libdb.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO protocol_versions (uuid, name, hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (uuid7(), name, content_hash, created_at),
        )
        conn.commit()


def get_current_hash(name: str) -> str | None:
    """Get most recent hash for a protocol."""
    if not DB_PATH.exists():
        return None

    with libdb.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT hash
            FROM protocol_versions
            WHERE name = ?
            ORDER BY uuid DESC
            LIMIT 1
            """,
            (name,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def list_protocols() -> list[tuple[str, str, int]]:
    """List all protocols with their latest hash and timestamp."""
    if not DB_PATH.exists():
        return []

    with libdb.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            SELECT p.name, p.hash, p.created_at
            FROM protocol_versions AS p
            WHERE p.uuid = (
                SELECT MAX(uuid)
                FROM protocol_versions
                WHERE name = p.name
            )
            ORDER BY name
            """
        )
        return cur.fetchall()
