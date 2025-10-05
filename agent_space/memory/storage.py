import sqlite3
import time
from datetime import datetime
from pathlib import Path

from ..lib.ids import uuid7
from .models import Entry

DB_PATH = Path.cwd() / ".space" / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_identity_topic ON entries(identity, topic);
CREATE INDEX IF NOT EXISTS idx_identity_created ON entries(identity, created_at);
CREATE INDEX IF NOT EXISTS idx_uuid ON entries(uuid);
"""

MIGRATION_CHECK = """
SELECT COUNT(*) FROM sqlite_master 
WHERE type='table' AND name='entries' 
AND sql LIKE '%id INTEGER PRIMARY KEY%'
"""

LEGACY_MIGRATION = """
CREATE TABLE entries_new (
    uuid TEXT PRIMARY KEY,
    identity TEXT NOT NULL,
    topic TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

INSERT INTO entries_new (uuid, identity, topic, message, timestamp, created_at)
SELECT hex(randomblob(16)), identity, topic, message, timestamp, created_at
FROM entries
ORDER BY id;

DROP TABLE entries;
ALTER TABLE entries_new RENAME TO entries;

CREATE INDEX idx_identity_topic ON entries(identity, topic);
CREATE INDEX idx_identity_created ON entries(identity, created_at);
CREATE INDEX idx_uuid ON entries(uuid);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    needs_migration = conn.execute(MIGRATION_CHECK).fetchone()[0] > 0
    if needs_migration:
        conn.executescript(LEGACY_MIGRATION)
    else:
        conn.executescript(SCHEMA)
    
    conn.commit()
    conn.close()


def add_entry(identity: str, topic: str, message: str):
    init_db()
    entry_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO entries (uuid, identity, topic, message, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (entry_uuid, identity, topic, message, ts, now),
    )
    conn.commit()
    conn.close()


def get_entries(identity: str, topic: str | None = None) -> list[Entry]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if topic:
        rows = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at FROM entries WHERE identity = ? AND topic = ? ORDER BY uuid",
            (identity, topic),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at FROM entries WHERE identity = ? ORDER BY topic, uuid",
            (identity,),
        ).fetchall()
    conn.close()
    return [Entry(*row) for row in rows]


def edit_entry(entry_uuid: str, new_message: str):
    init_db()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE entries SET message = ?, timestamp = ? WHERE uuid = ?",
        (new_message, ts, entry_uuid),
    )
    conn.commit()
    conn.close()


def delete_entry(entry_uuid: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM entries WHERE uuid = ?", (entry_uuid,))
    conn.commit()
    conn.close()


def clear_entries(identity: str, topic: str | None = None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if topic:
        conn.execute("DELETE FROM entries WHERE identity = ? AND topic = ?", (identity, topic))
    else:
        conn.execute("DELETE FROM entries WHERE identity = ?", (identity,))
    conn.commit()
    conn.close()
