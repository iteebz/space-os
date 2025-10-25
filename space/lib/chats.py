import contextlib
import hashlib

from space.lib import db, providers


def schema() -> str:
    """Chat database schema."""
    return """
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


db.register("chats", "chats.db", schema())
db.add_migrations("chats", [])


def _insert_msgs(cli: str, msgs: list, identity: str) -> None:
    with db.ensure("chats") as conn:
        for msg in msgs:
            raw_hash = hashlib.sha256(
                f"{cli}{msg.session_id}{msg.timestamp}{msg.text}".encode()
            ).hexdigest()
            with contextlib.suppress(Exception):
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
                        identity,
                        msg.role,
                        msg.text,
                        raw_hash,
                    ),
                )


def sync(identity: str) -> None:
    """Sync CLI sessions for a specific identity."""
    _insert_msgs("claude", providers.claude.chats(), identity)
    _insert_msgs("codex", providers.codex.chats(), identity)
    _insert_msgs("gemini", providers.gemini.chats(), identity)


def search(query: str, identity: str | None, all_agents: bool) -> list[dict]:
    """Search chat entries by query, optionally filtering by agent."""
    results = []
    with db.ensure("chats") as conn:
        sql_query = (
            "SELECT cli, session_id, identity, role, text, timestamp FROM entries WHERE text LIKE ?"
        )
        params = [f"%{query}%"]

        if identity and not all_agents:
            sql_query += " AND identity = ?"
            params.append(identity)

        sql_query += " ORDER BY timestamp ASC"

        rows = conn.execute(sql_query, params).fetchall()
        for row in rows:
            results.append(
                {
                    "source": "chats",
                    "cli": row["cli"],
                    "session_id": row["session_id"],
                    "identity": row["identity"],
                    "role": row["role"],
                    "text": row["text"],
                    "timestamp": row["timestamp"],
                    "reference": f"chats:{row['cli']}:{row['session_id']}",
                }
            )
    return results
