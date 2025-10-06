import json
import time

from space.os.lib import uuid7

from .models import Event
from .storage import db


def track(source: str, event_type: str, identity: str | None = None, data: dict | None = None):
    event_uuid = uuid7.uuid7()
    created_at = int(time.time())
    with db.get_db_connection() as conn:
        conn.execute(
            "INSERT INTO events (uuid, source, identity, event_type, data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                event_uuid,
                source,
                identity,
                event_type,
                json.dumps(data) if data else None,
                created_at,
            ),
        )
        conn.commit()


def emit(source: str, event_type: str, identity: str | None = None, data: dict | None = None):
    """Emits a structured event."""
    track(source=source, event_type=event_type, identity=identity, data=data)


def query(source: str | None = None, identity: str | None = None, limit: int = 50) -> list[Event]:
    with db.get_db_connection() as conn:
        query_parts = []
        params = []

        if source:
            query_parts.append("source = ?")
            params.append(source)
        if identity:
            query_parts.append("identity = ?")
            params.append(identity)

        where_clause = "WHERE " + " AND ".join(query_parts) if query_parts else ""
        sql = f"SELECT * FROM events {where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, tuple(params)).fetchall()
        return [Event(**dict(row)) for row in rows]
