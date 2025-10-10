import sqlite3
from contextlib import contextmanager

from . import config


def init_db():
    config.spawn_dir().mkdir(parents=True, exist_ok=True)
    config.registry_db().parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS constitutions (
                hash TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS identities (
                name TEXT PRIMARY KEY,
                self_description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def get_self_description(agent_name: str) -> str | None:
    """Get self-description for identity."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self_description FROM identities WHERE name = ?",
            (agent_name,),
        ).fetchone()
        return row["self_description"] if row else None


def set_self_description(agent_name: str, description: str) -> bool:
    """Set self-description for identity. Returns True when an update occurs."""
    import time

    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO identities (name, self_description, updated_at) VALUES (?, ?, ?)",
            (agent_name, description, time.time()),
        )
        conn.commit()
        return True


def _apply_migrations(conn):
    """Apply incremental schema migrations."""
    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")

    migrations = [
        ("migrate_to_identities", _migrate_to_identities),
        ("drop_registrations", "DROP TABLE IF EXISTS registrations"),
        ("drop_invocations", "DROP TABLE IF EXISTS invocations"),
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
                    raise RuntimeError(f"Migration '{name}' failed: {e}") from e


def _migrate_to_identities(conn):
    """Migrate self descriptions from registrations to identities table."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='registrations'"
    )
    if not cursor.fetchone():
        return

    rows = conn.execute(
        "SELECT DISTINCT agent_name, self FROM registrations WHERE self IS NOT NULL ORDER BY registered_at DESC"
    ).fetchall()

    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO identities (name, self_description) VALUES (?, ?)",
            (row[0], row[1]),
        )
