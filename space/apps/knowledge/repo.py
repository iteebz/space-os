from pathlib import Path
import sqlite3
from datetime import datetime

from space.os.lib import uuid7
from space.os.core.storage import Repo
from .models import Knowledge # Assuming a models.py exists for Knowledge dataclass

class KnowledgeRepo(Repo):
    def __init__(self, app_name: str):
        super().__init__(app_name)

    def _row_to_entity(self, row: sqlite3.Row) -> Knowledge:
        return Knowledge(
            id=row["id"],
            domain=row["domain"],
            contributor=row["contributor"],
            content=row["content"],
            confidence=row["confidence"],
            created_at=row["created_at"],
        )

    def add(self, domain: str, contributor: str, content: str, confidence: float | None = None) -> str:
        entry_id = str(uuid7.uuid7())
        created_at_timestamp = datetime.now().isoformat() # Use ISO format for consistency
        self._execute(
            "INSERT INTO knowledge (id, domain, contributor, content, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, domain, contributor, content, confidence, created_at_timestamp),
        )
        return entry_id

    def get(self, domain: str | None = None, contributor: str | None = None, entry_id: str | None = None) -> list[Knowledge]:
        query = "SELECT id, domain, contributor, content, confidence, created_at FROM knowledge WHERE 1=1"
        params = []

        if entry_id:
            query += " AND id = ?"
            params.append(entry_id)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if contributor:
            query += " AND contributor = ?"
            params.append(contributor)

        query += " ORDER BY created_at DESC"

        rows = self._fetch_all(query, tuple(params))
        return [self._row_to_entity(row) for row in rows]

    def update(self, entry_id: str, new_content: str, new_confidence: float | None = None):
        query = "UPDATE knowledge SET content = ?"
        params = [new_content]
        if new_confidence is not None:
            query += ", confidence = ?"
            params.append(new_confidence)
        query += " WHERE id = ?"
        params.append(entry_id)
        self._execute(query, tuple(params))

    def delete(self, entry_id: str):
        self._execute("DELETE FROM knowledge WHERE id = ?", (entry_id,))

    def clear(self, domain: str | None = None, contributor: str | None = None):
        query = "DELETE FROM knowledge WHERE 1=1"
        params = []
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        if contributor:
            query += " AND contributor = ?"
            params.append(contributor)
        self._execute(query, tuple(params))
