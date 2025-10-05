import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from . import config


@dataclass
class Registration:
    id: int
    role: str
    sender_id: str
    topic: str
    constitution_hash: str
    registered_at: str
    self: str | None = None
    model: str | None = None


def init_db():
    config.spawn_dir().mkdir(parents=True, exist_ok=True)
    config.registry_db().parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                constitution_hash TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                self TEXT,
                model TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sender_topic ON registrations(sender_id, topic)
        """)
        try:
            conn.execute("ALTER TABLE registrations ADD COLUMN self TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE registrations ADD COLUMN model TEXT")
        except sqlite3.OperationalError:
            pass
        conn.commit()


@contextmanager
def get_db():
    conn = sqlite3.connect(config.registry_db())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def register(role: str, sender_id: str, topic: str, constitution_hash: str, model: str | None = None) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO registrations (role, sender_id, topic, constitution_hash, model)
            VALUES (?, ?, ?, ?, ?)
        """,
            (role, sender_id, topic, constitution_hash, model),
        )
        conn.commit()
        return cursor.lastrowid


def unregister(role: str, sender_id: str, topic: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE role = ? AND sender_id = ? AND topic = ?",
            (role, sender_id, topic),
        )
        conn.commit()


def list_registrations() -> list[Registration]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM registrations ORDER BY registered_at DESC").fetchall()
        return [Registration(**dict(row)) for row in rows]


def get_registration(role: str, sender_id: str, topic: str) -> Registration | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE role = ? AND sender_id = ? AND topic = ?",
            (role, sender_id, topic),
        ).fetchone()
        if row:
            return Registration(**dict(row))
        return None


def get_registration_by_sender(sender_id: str, topic: str) -> Registration | None:
    """Get registration by sender_id and topic only."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE sender_id = ? AND topic = ?",
            (sender_id, topic),
        ).fetchone()
        if row:
            return Registration(**dict(row))
        return None


def rename_sender(old_sender_id: str, new_sender_id: str, new_role: str = None):
    with get_db() as conn:
        if new_role:
            conn.execute(
                "UPDATE registrations SET sender_id = ?, role = ? WHERE sender_id = ?",
                (new_sender_id, new_role, old_sender_id),
            )
        else:
            conn.execute(
                "UPDATE registrations SET sender_id = ? WHERE sender_id = ?",
                (new_sender_id, old_sender_id),
            )
        conn.commit()


def get_self_description(sender_id: str) -> str | None:
    """Get self-description for sender_id from any registration."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self FROM registrations WHERE sender_id = ? AND self IS NOT NULL ORDER BY registered_at DESC LIMIT 1",
            (sender_id,),
        ).fetchone()
        return row["self"] if row else None
