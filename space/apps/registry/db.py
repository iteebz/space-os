import sqlite3

from .config import registry_db
from .models import Entry


def get_db() -> sqlite3.Connection:
    """Get a database connection."""
    db_path = registry_db()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS constitutions (
                hash TEXT PRIMARY KEY,
                content TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE,
                role TEXT,
                channels TEXT,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                constitution_hash TEXT,
                provider TEXT,
                model TEXT,
                FOREIGN KEY (constitution_hash) REFERENCES constitutions(hash)
            )
        """)
        conn.commit()


_init_db()


def list_constitutions() -> list[tuple[str, str]]:
    """List all constitutions."""
    with get_db() as conn:
        return conn.execute("SELECT hash, content FROM constitutions ORDER BY hash").fetchall()


def track_constitution(constitution_hash: str, constitution_content: str):
    """Track a constitution in the database."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO constitutions (hash, content) VALUES (?, ?)",
            (constitution_hash, constitution_content),
        )
        conn.commit()


def get_constitution_content(constitution_hash: str) -> str | None:
    """Retrieve constitution content by its hash."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT content FROM constitutions WHERE hash = ?", (constitution_hash,)
        )
        result = cursor.fetchone()
        return result["content"] if result else None


def link(
    agent_id: str,
    role: str,
    channels: list[str],
    constitution_hash: str,
    constitution_content: str,
    provider: str | None,
    model: str | None,
):
    """Link an agent to the registry."""
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO entries
            (agent_id, role, channels, constitution_hash, provider, model)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent_id, role, ",".join(channels), constitution_hash, provider, model),
        )
        conn.commit()


def fetch_by_sender(sender_id: str) -> Entry | None:
    """Fetch a registry entry by sender_id."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT
                e.id, e.agent_id, e.role, e.channels, e.registered_at, e.constitution_hash,
                c.content AS self_description, e.provider, e.model
            FROM entries e
            JOIN constitutions c ON e.constitution_hash = c.hash
            WHERE e.agent_id = ?
            """,
            (sender_id,),
        )
        row = cursor.fetchone()
        if row:
            return Entry(
                id=row["id"],
                agent_id=row["agent_id"],
                role=row["role"],
                channels=row["channels"].split(",") if row["channels"] else [],
                registered_at=row["registered_at"],
                constitution_hash=row["constitution_hash"],
                self_description=row["self_description"],
                provider=row["provider"],
                model=row["model"],
            )
        return None
