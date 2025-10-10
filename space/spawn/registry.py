import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from .. import events
from ..errors import MigrationError
from . import config


@dataclass
class Registration:
    id: int
    role: str
    agent_name: str
    topic: str
    constitution_hash: str
    registered_at: str
    agent_id: str | None = None
    client: str | None = None
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
                                agent_name TEXT NOT NULL,
                                topic TEXT NOT NULL,
                                constitution_hash TEXT NOT NULL,
                                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                self TEXT,
                                model TEXT
                            )        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_topic ON registrations(agent_name, topic)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS constitutions (
                hash TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _apply_migrations(conn)
        conn.commit()


def save_constitution(constitution_hash: str, content: str):
    """Save constitution content by hash (content-addressable store)."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO constitutions (hash, content)
            VALUES (?, ?)
            """,
            (constitution_hash, content),
        )
        conn.commit()


def get_constitution(constitution_hash: str) -> str | None:
    """Retrieve constitution content by hash."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM constitutions WHERE hash = ?",
            (constitution_hash,),
        ).fetchone()
        return row["content"] if row else None


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
    role: str,
    agent_name: str,
    topic: str,
    constitution_hash: str,
    model: str | None = None,
    client: str | None = None,
    agent_id: str | None = None,
) -> int:
    import uuid

    if agent_id is None:
        agent_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO registrations (role, agent_name, topic, constitution_hash, model, client, agent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (role, agent_name, topic, constitution_hash, model, client, agent_id),
        )
        conn.commit()
        reg_id = cursor.lastrowid
    events.emit("spawn", "identity.register", agent_name, f"{role}:{topic}")
    return reg_id


def unregister(role: str, agent_name: str, topic: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE role = ? AND agent_name = ? AND topic = ?",
            (role, agent_name, topic),
        )
        conn.commit()
    events.emit("spawn", "identity.unregister", agent_name, f"{role}:{topic}")


def list_registrations() -> list[Registration]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM registrations ORDER BY registered_at DESC").fetchall()
        return [Registration(**dict(row)) for row in rows]


def get_registration(role: str, agent_name: str, topic: str) -> Registration | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE role = ? AND agent_name = ? AND topic = ?",
            (role, agent_name, topic),
        ).fetchone()
        if row:
            return Registration(**dict(row))
        return None


def get_registration_by_agent(agent_name: str, topic: str) -> Registration | None:
    """Get registration by agent_name and topic only."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE agent_name = ? AND topic = ?",
            (agent_name, topic),
        ).fetchone()
        if row:
            return Registration(**dict(row))
        return None


def delete_agent(agent_name: str):
    with get_db() as conn:
        conn.execute("DELETE FROM registrations WHERE agent_name = ?", (agent_name,))
        conn.commit()
    events.emit("spawn", "identity.delete", agent_name, "")


def rename_agent(old_name: str, new_name: str, new_role: str = None):
    with get_db() as conn:
        if new_role:
            conn.execute(
                "UPDATE registrations SET agent_name = ?, role = ? WHERE agent_name = ?",
                (new_name, new_role, old_name),
            )
        else:
            conn.execute(
                "UPDATE registrations SET agent_name = ? WHERE agent_name = ?",
                (new_name, old_name),
            )
        conn.commit()


def get_self_description(agent_name: str) -> str | None:
    """Get self-description for agent_name from any registration."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self FROM registrations WHERE agent_name = ? AND self IS NOT NULL ORDER BY registered_at DESC LIMIT 1",
            (agent_name,),
        ).fetchone()
        return row["self"] if row else None


def set_self_description(agent_name: str, description: str) -> bool:
    """Set self-description for agent_name. Returns True when an update occurs."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE registrations SET self = ? WHERE agent_name = ?", (description, agent_name)
        )
        conn.commit()
        return cursor.rowcount > 0


def _apply_migrations(conn):
    """Apply incremental schema migrations."""
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")

    migrations = [
        ("add_self", "ALTER TABLE registrations ADD COLUMN self TEXT"),
        ("add_model", "ALTER TABLE registrations ADD COLUMN model TEXT"),
        ("add_agent_id", "ALTER TABLE registrations ADD COLUMN agent_id TEXT"),
        ("add_client", "ALTER TABLE registrations ADD COLUMN client TEXT"),
        ("rename_sender_id", _migrate_rename_sender_id),
        ("rename_idx_sender_topic", _migrate_rename_idx_sender_topic),
        ("backfill_agent_id", _migrate_backfill_agent_id),
        ("backfill_client", _migrate_backfill_client),
    ]

    for name, migration in migrations:
        applied = conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,)).fetchone()
        if not applied:
            try:
                if callable(migration):
                    migration(conn)
                else:
                    conn.execute(migration)
                conn.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise MigrationError(f"Migration '{name}' failed: {e}") from e


def _migrate_rename_sender_id(conn):
    """Rename sender_id column to agent_name."""
    # Check if sender_id column exists before attempting to rename
    cursor = conn.execute("PRAGMA table_info(registrations)")
    columns = [col[1] for col in cursor.fetchall()]
    if "sender_id" in columns:
        conn.execute("ALTER TABLE registrations RENAME COLUMN sender_id TO agent_name")


def _migrate_backfill_agent_id(conn):
    """Backfill agent_id with UUIDs for existing registrations."""
    import uuid

    rows = conn.execute("SELECT id FROM registrations WHERE agent_id IS NULL").fetchall()
    for row in rows:
        agent_id = str(uuid.uuid4())
        conn.execute("UPDATE registrations SET agent_id = ? WHERE id = ?", (agent_id, row[0]))


def _migrate_backfill_client(conn):
    """Infer client from agent_name patterns."""

    client_map = {
        "zealot-1": "claude",
        "zealot-2": "claude",
        "gemilot": "gemini",
        "codelot": "codex",
        "harbinger-1": "gemini",
        "harbinger-2": "gemini",
        "kitsuragi": "codex",
        "lieutenant": "chatgpt",
        "sentinel": "codex",
        "scribe": "claude",
    }

    for agent_name, client in client_map.items():
        conn.execute(
            "UPDATE registrations SET client = ? WHERE agent_name = ? AND client IS NULL",
            (client, agent_name),
        )


def _migrate_rename_idx_sender_topic(conn):
    """Rename idx_sender_topic to idx_agent_topic."""
    # SQLite does not support renaming indexes directly.
    # Drop the old index and create a new one.
    conn.execute("DROP INDEX IF EXISTS idx_sender_topic")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_topic ON registrations(agent_name, topic)")
