import sqlite3
import time
from datetime import datetime

from .. import events
from ..lib import context_db
from ..lib.ids import uuid7
from .models import Entry


def _resolve_uuid(short_uuid: str) -> str:
    with context_db.connect() as conn:
        # Find all uuids that end with the short_uuid
        rows = conn.execute("SELECT uuid FROM memory WHERE uuid LIKE ?", (f"%{short_uuid}",)).fetchall()
    
    if not rows:
        raise ValueError(f"No entry found with UUID ending in '{short_uuid}'")
    
    if len(rows) > 1:
        ambiguous_uuids = [row[0] for row in rows]
        raise ValueError(f"Ambiguous UUID: '{short_uuid}' matches multiple entries: {ambiguous_uuids}")
    
    return rows[0][0]

def add_entry(identity: str, topic: str, message: str):
    entry_uuid = uuid7()
    now = int(time.time())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with context_db.connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, identity, topic, message, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_uuid, identity, topic, message, ts, now),
        )
        conn.commit()
    events.emit("memory", "entry.add", identity, f"{topic}:{message[:50]}")


def get_entries(identity: str, topic: str | None = None) -> list[Entry]:
    with context_db.connect() as conn:
        if topic:
            rows = conn.execute(
                "SELECT uuid, identity, topic, message, timestamp, created_at FROM memory WHERE identity = ? AND topic = ? ORDER BY uuid",
                (identity, topic),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT uuid, identity, topic, message, timestamp, created_at FROM memory WHERE identity = ? ORDER BY topic, uuid",
                (identity,),
            ).fetchall()
    return [Entry(*row) for row in rows]


def edit_entry(entry_uuid: str, new_message: str):
    full_uuid = _resolve_uuid(entry_uuid)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with context_db.connect() as conn:
        conn.execute(
            "UPDATE memory SET message = ?, timestamp = ? WHERE uuid = ?",
            (new_message, ts, full_uuid),
        )
        conn.commit()
    events.emit("memory", "entry.edit", None, f"{full_uuid[-8:]}")


def delete_entry(entry_uuid: str):
    full_uuid = _resolve_uuid(entry_uuid)
    with context_db.connect() as conn:
        conn.execute("DELETE FROM memory WHERE uuid = ?", (full_uuid,))
        conn.commit()
    events.emit("memory", "entry.delete", None, f"{full_uuid[-8:]}")


def clear_entries(identity: str, topic: str | None = None):
    with context_db.connect() as conn:
        if topic:
            conn.execute("DELETE FROM memory WHERE identity = ? AND topic = ?", (identity, topic))
        else:
            conn.execute("DELETE FROM memory WHERE identity = ?", (identity,))
        conn.commit()