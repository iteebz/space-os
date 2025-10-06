from pathlib import Path
from datetime import datetime

from space.os.lib import uuid7
from space.os.core.storage import Storage # Import Storage
from .models import Memory

class MemoryRepository(Storage): # Inherit from Storage
    # __init__ is handled by Storage

    def _resolve_uuid(self, short_uuid: str) -> str:
        rows = self._fetch_all(
            "SELECT uuid FROM memory WHERE uuid LIKE ?", (f"%{short_uuid}",)
        )

        if not rows:
            raise ValueError(f"No entry found with UUID ending in '{short_uuid}'")

        if len(rows) > 1:
            ambiguous_uuids = [row[0] for row in rows]
            raise ValueError(
                f"Ambiguous UUID: '{short_uuid}' matches multiple entries: {ambiguous_uuids}"
            )

        return rows[0][0]

    def add(self, identity: str, topic: str, message: str) -> str:
        entry_uuid = uuid7.uuid7()
        created_at_timestamp = datetime.now().timestamp()
        self._execute(
            "INSERT INTO memory (uuid, identity, topic, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (entry_uuid, identity, topic, message, created_at_timestamp),
        )
        return str(entry_uuid)

    def get(self, identity: str, topic: str | None = None) -> list[Memory]:
        if topic:
            rows = self._fetch_all(
                "SELECT uuid, identity, topic, message, created_at FROM memory WHERE identity = ? AND topic = ? ORDER BY created_at DESC",
                (identity, topic),
            )
        else:
            rows = self._fetch_all(
                "SELECT uuid, identity, topic, message, created_at FROM memory WHERE identity = ? ORDER BY created_at DESC",
                (identity,),
            )
        return [Memory(*row) for row in rows]

    def update(self, entry_uuid: str, new_message: str):
        full_uuid = self._resolve_uuid(entry_uuid)
        self._execute(
            "UPDATE memory SET message = ? WHERE uuid = ?",
            (new_message, full_uuid),
        )

    def delete(self, entry_uuid: str):
        full_uuid = self._resolve_uuid(entry_uuid)
        self._execute("DELETE FROM memory WHERE uuid = ?", (full_uuid,))

    def clear(self, identity: str, topic: str | None = None):
        if topic:
            self._execute("DELETE FROM memory WHERE identity = ? AND topic = ?", (identity, topic))
        else:
            self._execute("DELETE FROM memory WHERE identity = ?", (identity,))