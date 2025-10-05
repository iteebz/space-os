import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .models import Entry

DB_PATH = Path.cwd() / ".space" / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_identity_topic ON entries(identity, topic);
CREATE INDEX IF NOT EXISTS idx_identity_created ON entries(identity, created_at);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def add_entry(identity: str, topic: str, message: str):
    init_db()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO entries (identity, topic, message, timestamp, created_at) VALUES (?, ?, ?, ?, ?)",
        (identity, topic, message, ts, now),
    )
    conn.commit()
    conn.close()


def get_entries(identity: str, topic: str | None = None) -> list[Entry]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if topic:
        rows = conn.execute(
            "SELECT identity, topic, message, timestamp, created_at FROM entries WHERE identity = ? AND topic = ? ORDER BY created_at",
            (identity, topic),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT identity, topic, message, timestamp, created_at FROM entries WHERE identity = ? ORDER BY topic, created_at",
            (identity,),
        ).fetchall()
    conn.close()
    return [Entry(*row) for row in rows]


def clear_entries(identity: str, topic: str | None = None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if topic:
        conn.execute("DELETE FROM entries WHERE identity = ? AND topic = ?", (identity, topic))
    else:
        conn.execute("DELETE FROM entries WHERE identity = ?", (identity,))
    conn.commit()
    conn.close()
