import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass

from . import config

CONSTITUTIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS constitutions (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL
);
"""

GUIDES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS guides (
    name TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REGISTRY_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    channels TEXT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    constitution_hash TEXT NOT NULL,
    self_description TEXT,
    provider TEXT,
    model TEXT,
    FOREIGN KEY (constitution_hash) REFERENCES constitutions (hash)
);
"""

@dataclass
class Entry:
    id: int
    agent_id: str
    role: str
    channels: str
    registered_at: str
    constitution_hash: str
    self_description: str | None = None
    provider: str | None = None
    model: str | None = None
    identity: str | None = None # Populated from join


def init_db():
    config.spawn_dir().mkdir(parents=True, exist_ok=True)
    config.registry_db().parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(CONSTITUTIONS_TABLE_SCHEMA)
        conn.execute(GUIDES_TABLE_SCHEMA)
        conn.execute(REGISTRY_TABLE_SCHEMA)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON registry(agent_id)")
        conn.commit()

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
    agent_id: str,
    role: str,
    channels: list[str],
    constitution_hash: str,
    constitution_content: str,
    provider: str | None = None,
    model: str | None = None,
) -> int:
    with get_db() as conn:
        # Insert into constitutions table
        conn.execute(
            "INSERT OR IGNORE INTO constitutions (hash, content) VALUES (?, ?)",
            (constitution_hash, constitution_content),
        )

        cursor = conn.execute(
            """
            INSERT INTO registry (agent_id, role, channels, constitution_hash, provider, model)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (agent_id, role, ",".join(channels), constitution_hash, provider, model),
        )
        conn.commit()
        return cursor.lastrowid

def unregister(agent_id: str, channel_id: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM registry WHERE agent_id = ? AND ? LIKE '%' || channels || '%'",
            (agent_id, channel_id),
        )
        conn.commit()

def list() -> list[Entry]:
    with get_db() as conn:
        rows = conn.execute("""SELECT r.*, c.content as identity 
                             FROM registry r JOIN constitutions c ON r.constitution_hash = c.hash 
                             ORDER BY r.registered_at DESC""").fetchall()
        return [Entry(**dict(row)) for row in rows]

def fetch(agent_id: str, channel_id: str) -> Entry | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT r.*, c.content as identity 
               FROM registry r JOIN constitutions c ON r.constitution_hash = c.hash 
               WHERE r.agent_id = ? AND ? LIKE '%' || r.channels || '%'""",
            (agent_id, channel_id),
        ).fetchone()
        if row:
            return Entry(**dict(row))
        return None

def fetch_by_sender(agent_id: str) -> Entry | None:
    """Get the most recent registration for a given agent_id."""
    with get_db() as conn:
        row = conn.execute(
            """SELECT r.*, c.content as identity 
               FROM registry r JOIN constitutions c ON r.constitution_hash = c.hash 
               WHERE r.agent_id = ? ORDER BY r.registered_at DESC LIMIT 1""",
            (agent_id,),
        ).fetchone()
        if row:
            return Entry(**dict(row))
        return None

def rename_sender(
    old_agent_id: str,
    new_agent_id: str,
    new_self_description: str | None = None,
    new_provider: str | None = None,
    new_model: str | None = None,
):
    with get_db() as conn:
        updates = []
        params = []

        if new_self_description is not None:
            updates.append("self_description = ?")
            params.append(new_self_description)
        if new_provider is not None:
            updates.append("provider = ?")
            params.append(new_provider)
        if new_model is not None:
            updates.append("model = ?")
            params.append(new_model)

        if updates:
            update_clause = ", ".join(updates)
            conn.execute(
                f"UPDATE registry SET agent_id = ?, {update_clause} WHERE agent_id = ?",
                (new_agent_id, *params, old_agent_id),
            )
        else:
            conn.execute(
                "UPDATE registry SET agent_id = ? WHERE agent_id = ?",
                (new_agent_id, old_agent_id),
            )
        conn.commit()

def get_self_description(agent_id: str) -> str | None:
    """Get the self-description for a given agent_id."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self_description FROM registry WHERE agent_id = ? ORDER BY registered_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        if row and row["self_description"]:
            return row["self_description"]
        return None

def set_self_description(agent_id: str, description: str) -> int:
    """Set the self-description for a given agent_id."""
    with get_db() as conn:
        result = conn.execute(
            "UPDATE registry SET self_description = ? WHERE agent_id = ?",
            (description, agent_id),
        )
        conn.commit()
        return result.rowcount