import contextlib
import hashlib

from space.os import db
from space.os.lib import agents


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
    _insert_msgs("claude", agents.claude.chats(), identity)
    _insert_msgs("codex", agents.codex.chats(), identity)
    _insert_msgs("gemini", agents.gemini.chats(), identity)
