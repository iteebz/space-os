from pathlib import Path

from space.lib import db as db_lib
from space.lib import paths

from . import migrations

_initialized = False


def schema() -> str:
    return """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    identity TEXT,
    task_id TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cli, session_id)
);

CREATE TABLE IF NOT EXISTS syncs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    session_id TEXT NOT NULL,
    last_byte_offset INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cli, session_id),
    FOREIGN KEY(cli, session_id) REFERENCES sessions(cli, session_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_identity ON sessions(identity);
CREATE INDEX IF NOT EXISTS idx_sessions_task_id ON sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_sessions_cli ON sessions(cli);
CREATE INDEX IF NOT EXISTS idx_syncs_session ON syncs(cli, session_id);
"""


def path() -> Path:
    return paths.space_data() / "chats.db"


def register() -> None:
    global _initialized
    if _initialized:
        return
    _initialized = True

    db_lib.register("chats", "chats.db", schema())
    db_lib.add_migrations("chats", migrations.MIGRATIONS)


def connect():
    """Return connection to chats database via central registry."""
    return db_lib.ensure("chats")
