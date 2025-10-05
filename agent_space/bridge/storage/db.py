"""Core database connection, schema, and utilities."""

import sqlite3
from contextlib import contextmanager

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
                prompt_hash TEXT,
                priority TEXT DEFAULT 'normal'
            )
        """)

        # Identity prompts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identities (
                hash TEXT PRIMARY KEY,
                base_identity TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
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
                instruction_hash TEXT
            )
        """)

        # Channel notes for experimental tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                prompt_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(id)
            )
        """)

        # Coordination instructions versioning
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instructions (
                hash TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        # Migration: Add priority column to existing messages table
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN priority TEXT DEFAULT 'normal'")
        except sqlite3.OperationalError:
            pass

        # Performance indexes
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_channel_time ON messages(channel_id, created_at)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks ON bookmarks(agent_id, channel_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes ON notes(channel_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority)")

        conn.commit()
