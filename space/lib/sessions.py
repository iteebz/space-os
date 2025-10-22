import hashlib
import sqlite3
from typing import Any

from space import db
from space.lib import agents
from space.lib.models import Message

_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    model TEXT,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    identity TEXT,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    raw_hash TEXT UNIQUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cli, session_id, timestamp)
);

CREATE INDEX IF NOT EXISTS idx_identity ON entries(identity);
CREATE INDEX IF NOT EXISTS idx_cli_session ON entries(cli, session_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON entries(timestamp);
"""

db.register("sessions", "sessions.db", _SESSIONS_SCHEMA)
db.add_migrations("sessions", [])


def init_db():
    db.ensure("sessions").close()


def _insert_msgs(cli: str, msgs: list[Message]) -> int:
    synced = 0
    conn = db.ensure("sessions")
    for msg in msgs:
        raw_hash = hashlib.sha256(
            f"{cli}{msg.session_id}{msg.timestamp}{msg.text}".encode()
        ).hexdigest()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO entries
                (cli, model, session_id, timestamp, identity, role, text, raw_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cli,
                    msg.model,
                    msg.session_id,
                    msg.timestamp,
                    None,
                    msg.role,
                    msg.text,
                    raw_hash,
                ),
            )
            synced += 1
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return synced


def sync(identity: str | None = None) -> dict[str, int]:
    init_db()

    results = {
        "claude": _insert_msgs("claude", agents.claude.sessions()),
        "codex": _insert_msgs("codex", agents.codex.sessions()),
        "gemini": _insert_msgs("gemini", agents.gemini.sessions()),
    }

    if identity:
        conn = db.ensure("sessions")
        conn.execute("UPDATE entries SET identity = ? WHERE identity IS NULL", (identity,))
        conn.close()

    return results


def search(query: str, identity: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    conn = db.ensure("sessions")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = """
        SELECT id, cli, model, session_id, timestamp, identity, role, text
        FROM entries
        WHERE text LIKE ?
    """
    params = [f"%{query}%"]

    if identity:
        sql += " AND identity = ?"
        params.append(identity)

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def list_entries(identity: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    conn = db.ensure("sessions")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if identity:
        cursor.execute(
            """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            WHERE identity = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (identity, limit),
        )
    else:
        cursor.execute(
            """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_entry(entry_id: int) -> dict[str, Any] | None:
    init_db()
    conn = db.ensure("sessions")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_surrounding_context(entry_id: int, context_size: int = 5) -> list[dict[str, Any]]:
    entry = get_entry(entry_id)
    if not entry:
        return []

    init_db()
    conn = db.ensure("sessions")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, cli, model, session_id, timestamp, identity, role, text
        FROM entries
        WHERE cli = ? AND session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (entry["cli"], entry["session_id"], context_size * 2),
    )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def sample(
    count: int = 5, identity: str | None = None, cli: str | None = None
) -> list[dict[str, Any]]:
    init_db()
    conn = db.ensure("sessions")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = (
        "SELECT id, cli, model, session_id, timestamp, identity, role, text FROM entries WHERE 1=1"
    )
    params = []

    if identity:
        sql += " AND identity = ?"
        params.append(identity)

    if cli:
        sql += " AND cli = ?"
        params.append(cli)

    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results
