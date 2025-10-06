import sqlite3
from contextlib import contextmanager
from pathlib import Path

EVENTS_DB_PATH = Path.home() / ".space" / "events.db"


def ensure_events_dir():
    EVENTS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db_connection():
    ensure_events_dir()
    conn = sqlite3.connect(EVENTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    ensure_events_dir()
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                uuid TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                identity TEXT,
                event_type TEXT NOT NULL,
                data TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON events(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_identity ON events(identity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_uuid ON events(uuid)")
        conn.commit()
