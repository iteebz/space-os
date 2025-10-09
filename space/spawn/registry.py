import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from .. import events
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_identities (
                sender_id TEXT PRIMARY KEY,
                full_identity TEXT NOT NULL,
                constitution_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS constitutions (
                constitution_hash TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _apply_migrations(conn)
        conn.commit()


def save_constitution(constitution_hash: str, content: str):
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO constitutions (constitution_hash, content)
            VALUES (?, ?)
            """,
            (constitution_hash, content),
        )
        conn.commit()


def get_constitution(constitution_hash: str) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM constitutions WHERE constitution_hash = ?",
            (constitution_hash,),
        ).fetchone()
        return row["content"] if row else None


def save_agent_identity(sender_id: str, full_identity: str, constitution_hash: str):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO agent_identities (sender_id, full_identity, constitution_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(sender_id) DO UPDATE SET
                full_identity = EXCLUDED.full_identity,
                constitution_hash = EXCLUDED.constitution_hash,
                updated_at = CURRENT_TIMESTAMP
            """,
            (sender_id, full_identity, constitution_hash),
        )
        conn.commit()


def get_agent_identity(sender_id: str) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT full_identity FROM agent_identities WHERE sender_id = ?",
            (sender_id,),
        ).fetchone()
        return row["full_identity"] if row else None


@contextmanager
def get_db():
    db_path = config.registry_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def register(
    role: str, sender_id: str, topic: str, constitution_hash: str, model: str | None = None
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO registrations (role, sender_id, topic, constitution_hash, model)
            VALUES (?, ?, ?, ?, ?)
        """,
            (role, sender_id, topic, constitution_hash, model),
        )
        conn.commit()
        reg_id = cursor.lastrowid
    events.emit("spawn", "identity.register", sender_id, f"{role}:{topic}")
    return reg_id


def unregister(role: str, sender_id: str, topic: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE role = ? AND sender_id = ? AND topic = ?",
            (role, sender_id, topic),
        )
        conn.commit()
    events.emit("spawn", "identity.unregister", sender_id, f"{role}:{topic}")


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


def delete_agent(sender_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM registrations WHERE sender_id = ?", (sender_id,))
        conn.commit()
    events.emit("spawn", "identity.delete", sender_id, "")


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


def set_self_description(sender_id: str, description: str) -> bool:
    """Set self-description for sender_id. Returns True when an update occurs."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE registrations SET self = ? WHERE sender_id = ?", (description, sender_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def _apply_migrations(conn):
    """Apply incremental schema migrations."""
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")

    migrations = [
        ("add_self", "ALTER TABLE registrations ADD COLUMN self TEXT"),
        ("add_model", "ALTER TABLE registrations ADD COLUMN model TEXT"),
    ]

    for name, sql in migrations:
        applied = conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,)).fetchone()
        if not applied:
            try:
                conn.execute(sql)
                conn.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
            except sqlite3.OperationalError:
                pass
