import sqlite3
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Iterator

from space.os.paths import data_for
from .models import Message

# We will need a migration utility, for now, we assume it exists.
# from space.os.db.migration import apply_migrations

class BridgeRepo:
    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path or data_for("bridge")
        self._app_root_path = Path(__file__).parent
        self.init_db()

    @contextmanager
    def _connect(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the app's dedicated database."""
        conn = sqlite3.connect(self._db_path)
        if row_factory:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Initializes the database and applies migrations."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    guide_hash TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    archived_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    prompt_hash TEXT,
                    priority TEXT DEFAULT 'normal',
                    constitution_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES channels (id)
                )
            """)
            conn.commit()

    def create_channel(self, channel_name: str, guide_hash: str) -> str:
        """Create channel record in DB, locking guide version. Returns channel_id."""
        channel_id = f"channel_{channel_name}"
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO channels (id, name, guide_hash) VALUES (?, ?, ?)",
                (channel_id, channel_name, guide_hash),
            )
            conn.commit()
        return channel_id

    def get_channel_id(self, channel_name: str) -> str | None:
        """Get stable channel ID from human-readable name."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
            result = cursor.fetchone()
        return result[0] if result else None

    def get_channel_name(self, channel_id: str) -> str | None:
        """Resolve a channel UUID back to its human-readable name."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT name FROM channels WHERE id = ?", (channel_id,))
            row = cursor.fetchone()
        return row[0] if row else None

    def create_message(
        self, channel_id: str, sender: str, content: str, prompt_hash: str
    ) -> int:
        """Insert a message record into the database."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (channel_id, sender, content, prompt_hash)
                VALUES (?, ?, ?, ?)
            """,
                (channel_id, sender, content, prompt_hash),
            )
            message_id = cursor.lastrowid
            conn.commit()
        return message_id

    def get_messages_for_channel(self, channel_id: str) -> list[Message]:
        """Retrieve all messages for a given channel from storage."""
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute(
                """
                SELECT id, channel_id, sender, content, created_at
                FROM messages
                WHERE channel_id = ?
                ORDER BY created_at ASC
            """,
                (channel_id,),
            )
            return [Message(**row) for row in cursor.fetchall()]

    def fetch_sender_history(self, sender: str, limit: int | None = None) -> list[Message]:
        with self._connect(row_factory=sqlite3.Row) as conn:
            query = "SELECT id, channel_id, sender, content, created_at FROM messages WHERE sender = ? ORDER BY created_at ASC"
            params = (sender,)
            if limit:
                query += " LIMIT ?"
                params = (sender, limit)
            cursor = conn.execute(query, params)
            return [Message(**row) for row in cursor.fetchall()]
