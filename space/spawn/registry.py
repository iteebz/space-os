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
                archived_at INTEGER,
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


def get_agent_ids(name: str, include_archived: bool = False) -> list[str]:
    """Get all agent UUIDs matching name."""
    with get_db() as conn:
        archive_filter = "" if include_archived else "AND archived_at IS NULL"
        rows = conn.execute(
            f"SELECT id FROM agents WHERE name = ? {archive_filter}",
            (name,)
        ).fetchall()
        return [row["id"] for row in rows]


def get_agent_id(name: str) -> str | None:
    """Get first active agent UUID by name. For single-agent ops."""
    ids = get_agent_ids(name, include_archived=False)
    return ids[0] if ids else None


def get_agent_name(agent_id: str) -> str | None:
    """Get agent name by UUID."""
    with get_db() as conn:
        row = conn.execute("SELECT name FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return row["name"] if row else None


def ensure_agent(name: str) -> str:
    """Get or create agent, return UUID."""
    agent_id = get_agent_id(name)
    if not agent_id:
        agent_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute("INSERT INTO agents (id, name) VALUES (?, ?)", (agent_id, name))
            conn.commit()
    return agent_id


def get_self_description(agent_name: str) -> str | None:
    """Get self-description for agent."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT self_description FROM agents WHERE name = ? LIMIT 1",
            (agent_name,),
        ).fetchone()
        return row["self_description"] if row else None


def set_self_description(agent_name: str, description: str) -> bool:
    """Set self-description for agent. Returns True when an update occurs."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ? LIMIT 1", (agent_name,)).fetchone()
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
        ("add_archived_at", "ALTER TABLE agents ADD COLUMN archived_at INTEGER"),
        ("drop_canonical_id", _drop_canonical_id),
        ("drop_agent_aliases", "DROP TABLE IF EXISTS agent_aliases"),
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
                if "duplicate column" not in str(e).lower() and "no such table" not in str(e).lower():
                    raise RuntimeError(f"Migration '{name}' failed: {e}") from e


def rename_agent(old_name: str, new_name: str) -> bool:
    """Rename an agent. Merges histories if new_name exists."""
    with get_db() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (old_name,)).fetchone()
        if not row:
            return False
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
    """Drop UNIQUE constraint from agents.name to allow shared names."""
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


def _drop_canonical_id(conn):
    """Remove canonical_id column - shared names replace canonical linking."""
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agents'")
    row = cursor.fetchone()
    if not row:
        return

    schema = row[0]
    if "canonical_id" not in schema:
        return

    cursor = conn.execute("PRAGMA table_info(agents)")
    columns = [col[1] for col in cursor.fetchall() if col[1] != "canonical_id"]
    col_list = ", ".join(columns)

    conn.execute(f"""
        CREATE TABLE agents_new (
            id TEXT PRIMARY KEY,
            name TEXT,
            self_description TEXT,
            archived_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute(f"""
        INSERT INTO agents_new ({col_list})
        SELECT {col_list} FROM agents
    """)

    conn.execute("DROP TABLE agents")
    conn.execute("ALTER TABLE agents_new RENAME TO agents")


def archive_agent(name: str) -> bool:
    """Archive an agent. Returns True if archived, False if not found."""
    import time

    agent_id = get_agent_id(name)
    if not agent_id:
        return False
    
    with get_db() as conn:
        conn.execute(
            "UPDATE agents SET archived_at = ? WHERE id = ?",
            (int(time.time()), agent_id)
        )
        conn.commit()
    return True


def restore_agent(name: str) -> bool:
    """Restore an archived agent. Returns True if restored, False if not found."""
    agent_ids = get_agent_ids(name, include_archived=True)
    if not agent_ids:
        return False
    
    with get_db() as conn:
        for agent_id in agent_ids:
            conn.execute(
                "UPDATE agents SET archived_at = NULL WHERE id = ?",
                (agent_id,)
            )
        conn.commit()
    return True


def _resolve_agent(identifier: str) -> str | None:
    """Resolve name or UUID to UUID."""
    if len(identifier) == 36 and identifier.count('-') == 4:
        with get_db() as conn:
            row = conn.execute("SELECT id FROM agents WHERE id = ?", (identifier,)).fetchone()
            return row["id"] if row else None
    else:
        ids = get_agent_ids(identifier, include_archived=True)
        if len(ids) > 1:
            return None
        return ids[0] if ids else None


def merge_agents(from_identifier: str, to_identifier: str) -> bool:
    """Merge agent histories. Migrates all references from source to target."""
    from ..lib import paths
    
    from_id = _resolve_agent(from_identifier)
    to_id = _resolve_agent(to_identifier)
    
    if not from_id:
        return False
    if not to_id:
        return False
    if from_id == to_id:
        return False
    
    spawn_db = config.registry_db()
    events_db = paths.space_root() / "events.db"
    memory_db = paths.space_root() / "memory.db"
    knowledge_db = paths.space_root() / "knowledge.db"
    bridge_db = paths.space_root() / "bridge.db"
    
    with get_db() as conn:
        conn.execute("UPDATE agents SET name = (SELECT name FROM agents WHERE id = ?) WHERE id = ?", (to_id, from_id))
        conn.commit()
    
    import sqlite3
    if events_db.exists():
        conn = sqlite3.connect(events_db)
        conn.execute("UPDATE events SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()
    
    if memory_db.exists():
        conn = sqlite3.connect(memory_db)
        conn.execute("UPDATE memory SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()
    
    if knowledge_db.exists():
        conn = sqlite3.connect(knowledge_db)
        conn.execute("UPDATE knowledge SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()
    
    if bridge_db.exists():
        conn = sqlite3.connect(bridge_db)
        conn.execute("UPDATE messages SET agent_id = ? WHERE agent_id = ?", (to_id, from_id))
        conn.commit()
        conn.close()
    
    with get_db() as conn:
        conn.execute("DELETE FROM agents WHERE id = ?", (from_id,))
        conn.commit()
    
    return True
