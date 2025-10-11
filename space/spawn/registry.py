import sqlite3
import uuid
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
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                self_description TEXT,
                canonical_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (canonical_id) REFERENCES agents(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_aliases (
                agent_id TEXT NOT NULL,
                alias TEXT NOT NULL,
                PRIMARY KEY (agent_id, alias),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
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


def get_agent_id(name: str) -> str | None:
    """Get canonical agent UUID by name or alias."""
    with get_db() as conn:
        row = conn.execute("SELECT id, canonical_id FROM agents WHERE name = ?", (name,)).fetchone()
        if row:
            return row["canonical_id"] if row["canonical_id"] else row["id"]

        row = conn.execute("SELECT agent_id FROM agent_aliases WHERE alias = ?", (name,)).fetchone()
        if row:
            canonical = conn.execute(
                "SELECT canonical_id FROM agents WHERE id = ?", (row["agent_id"],)
            ).fetchone()
            return (
                canonical["canonical_id"]
                if canonical and canonical["canonical_id"]
                else row["agent_id"]
            )

        return None


def get_agent_name(agent_id: str) -> str | None:
    """Get agent name by UUID."""
    with get_db() as conn:
        row = conn.execute("SELECT name FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return row["name"] if row else None


def ensure_agent(name: str) -> str:
    """Get or create agent, return canonical UUID."""
    agent_id = get_agent_id(name)
    if not agent_id:
        agent_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute("INSERT INTO agents (id, name) VALUES (?, ?)", (agent_id, name))
            conn.execute(
                "INSERT INTO agent_aliases (agent_id, alias) VALUES (?, ?)", (agent_id, name)
            )
            conn.commit()
    return agent_id


def get_self_description(agent_name: str) -> str | None:
    """Get self-description for agent."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self_description FROM agents WHERE name = ?",
            (agent_name,),
        ).fetchone()
        return row["self_description"] if row else None


def set_self_description(agent_name: str, description: str) -> bool:
    """Set self-description for agent. Returns True when an update occurs."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (agent_name,)).fetchone()
        if row:
            conn.execute(
                "UPDATE agents SET self_description = ? WHERE id = ?",
                (description, row["id"]),
            )
        else:
            agent_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO agents (id, name, self_description) VALUES (?, ?, ?)",
                (agent_id, agent_name, description),
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
        ("rename_identities_to_agents", _rename_identities_to_agents),
        ("drop_registry", "DROP TABLE IF EXISTS registry"),
        (
            "add_canonical_id",
            "ALTER TABLE agents ADD COLUMN canonical_id TEXT REFERENCES agents(id)",
        ),
        ("drop_name_unique", _drop_name_unique_constraint),
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


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Returns True if renamed, False if old_name not found or new_name exists."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (old_name,)).fetchone()
        if not row:
            return False
        existing = conn.execute("SELECT id FROM agents WHERE name = ?", (new_name,)).fetchone()
        if existing:
            raise ValueError(f"Agent '{new_name}' already exists")
        conn.execute("UPDATE agents SET name = ? WHERE id = ?", (new_name, row["id"]))
        conn.commit()
        return True


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


def _rename_identities_to_agents(conn):
    """Rename identities table to agents and add UUID primary key."""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='identities'")
    if not cursor.fetchone():
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            self_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    rows = conn.execute("SELECT name, self_description FROM identities").fetchall()
    for row in rows:
        agent_id = str(uuid.uuid4())
        conn.execute(
            "INSERT OR IGNORE INTO agents (id, name, self_description) VALUES (?, ?, ?)",
            (agent_id, row[0], row[1]),
        )

    conn.execute("DROP TABLE IF EXISTS identities")


def _drop_name_unique_constraint(conn):
    """Drop UNIQUE constraint from agents.name to allow aliases."""
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agents'")
    row = cursor.fetchone()
    if not row:
        return

    schema = row[0]
    if "UNIQUE" not in schema:
        return

    conn.execute("""
        CREATE TABLE agents_new (
            id TEXT PRIMARY KEY,
            name TEXT,
            self_description TEXT,
            canonical_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (canonical_id) REFERENCES agents(id)
        )
    """)

    conn.execute("""
        INSERT INTO agents_new (id, name, self_description, canonical_id, created_at)
        SELECT id, name, self_description, canonical_id, created_at FROM agents
    """)

    conn.execute("DROP TABLE agents")
    conn.execute("ALTER TABLE agents_new RENAME TO agents")
