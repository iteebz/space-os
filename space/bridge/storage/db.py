"""Core database connection, schema, and utilities."""

import sqlite3
from contextlib import contextmanager, suppress

from .. import config


def ensure_bridge_dir():
    """Ensure Bridge data directories exist."""
    config.SPACE_DIR.mkdir(exist_ok=True)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db_connection():
    """Provide a database connection with row factory set to sqlite3.Row."""
    ensure_bridge_dir()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize SQLite database with Bridge schema."""
    ensure_bridge_dir()
    with get_db_connection() as conn:
        # Messages table with prompt hash tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                priority TEXT DEFAULT 'normal'
            )
        """)

        # Bookmark tracking per agent per channel
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                agent_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                last_seen_id INTEGER DEFAULT 0,
                PRIMARY KEY (agent_id, channel_id)
            )
        """)

        # Channel metadata with UUID-based stable IDs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                archived_at TIMESTAMP
            )
        """)

        # Channel notes for experimental tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id)
            )
        """)

        # Coordination instructions versioning (DEPRECATED)

        # Migration: Add priority column to existing messages table
        with suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE messages ADD COLUMN priority TEXT DEFAULT 'normal'")

        # Migration: Add archived_at column to existing channels table
        with suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE channels ADD COLUMN archived_at TIMESTAMP")

        # Migration: Drop prompt_hash column from messages table
        with suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE messages DROP COLUMN prompt_hash")

        # Migration: Drop prompt_hash column from notes table
        with suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE notes DROP COLUMN prompt_hash")

        # Performance indexes
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority)")

        conn.commit()
