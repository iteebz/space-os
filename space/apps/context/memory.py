from datetime import datetime

from space import events
from space.lib import uuid7

from .db import connect
from .models import Memory


def _resolve_uuid(short_uuid: str) -> str:
    with connect() as conn:
        # Find all uuids that end with the short_uuid
        rows = conn.execute(
            "SELECT uuid FROM memory WHERE uuid LIKE ?", (f"%{short_uuid}",)
        ).fetchall()

    if not rows:
        raise ValueError(f"No entry found with UUID ending in '{short_uuid}'")

    if len(rows) > 1:
        ambiguous_uuids = [row[0] for row in rows]
        raise ValueError(
            f"Ambiguous UUID: '{short_uuid}' matches multiple entries: {ambiguous_uuids}"
        )

    return rows[0][0]


def memorize(identity: str, topic: str, message: str):
    entry_uuid = uuid7.uuid7()
    created_at_timestamp = datetime.now().timestamp()
    with connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, identity, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (entry_uuid, identity, topic, message, created_at_timestamp),
        )
        conn.commit()
    events.emit("memory", "entry.add", identity, {"topic": topic, "message": message[:50]})


def recall(identity: str, topic: str | None = None) -> list[Memory]:
    with connect() as conn:
        if topic:
            rows = conn.execute(
                "SELECT uuid, identity, topic, message, created_at FROM memory WHERE identity = ? AND topic = ? ORDER BY uuid",
                (identity, topic),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT uuid, identity, topic, message, created_at FROM memory WHERE identity = ? ORDER BY topic, uuid",
                (identity,),
            ).fetchall()
    return [Memory(*row) for row in rows]


def edit(entry_uuid: str, new_message: str):
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        conn.execute(
            "UPDATE memory SET message = ? WHERE uuid = ?",
            (new_message, full_uuid),
        )
        conn.commit()
    events.emit("memory", "entry.edit", None, {"uuid": full_uuid[-8:]})


def delete(entry_uuid: str):
    full_uuid = _resolve_uuid(entry_uuid)
    with connect() as conn:
        conn.execute("DELETE FROM memory WHERE uuid = ?", (full_uuid,))
        conn.commit()
    events.emit("memory", "entry.delete", None, {"uuid": full_uuid[-8:]})


def clear(identity: str, topic: str | None = None):
    with connect() as conn:
        if topic:
            conn.execute("DELETE FROM memory WHERE identity = ? AND topic = ?", (identity, topic))
        else:
            conn.execute("DELETE FROM memory WHERE identity = ?", (identity,))
