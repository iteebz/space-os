from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from space.os.paths import data_for
from .models import Channel, Message, Note, ExportData

DB_PATH = data_for("bridge")

_BRIDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    guide_hash TEXT,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    prompt_hash TEXT,
    priority TEXT DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels (id)
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels (id)
);
"""

def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_BRIDGE_SCHEMA)
        conn.commit()

@contextmanager
def _connect(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row if row_factory is None else row_factory
    try:
        yield conn
    finally:
        conn.close()

def create_channel(channel_name: str, guide_hash: str) -> str:
    channel_id = f"channel_{channel_name}"
    with _connect() as conn:
        conn.execute("INSERT INTO channels (id, name, guide_hash) VALUES (?, ?, ?)", (channel_id, channel_name, guide_hash))
        conn.commit()
    return channel_id

def get_channel_id(channel_name: str) -> str | None:
    with _connect() as conn:
        cursor = conn.execute("SELECT id FROM channels WHERE name = ?", (channel_name,))
        result = cursor.fetchone()
    return result[0] if result else None

def create_message(channel_id: str, sender: str, content: str, prompt_hash: str) -> int:
    with _connect() as conn:
        cursor = conn.execute("INSERT INTO messages (channel_id, sender, content, prompt_hash) VALUES (?, ?, ?, ?)", (channel_id, sender, content, prompt_hash))
        message_id = cursor.lastrowid
        conn.commit()
    return message_id

def get_messages_for_channel(channel_id: str) -> list[Message]:
    with _connect() as conn:
        cursor = conn.execute("SELECT id, channel_id, sender, content, created_at FROM messages WHERE channel_id = ? ORDER BY created_at ASC", (channel_id,))
        return [Message(**row) for row in cursor.fetchall()]