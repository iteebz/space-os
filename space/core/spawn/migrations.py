def _rename_name_to_identity(conn):
    """Rename 'name' column to 'identity' if it exists."""
    cursor = conn.execute("PRAGMA table_info(agents)")
    columns = {row[1] for row in cursor.fetchall()}
    if "name" in columns and "identity" not in columns:
        conn.execute("ALTER TABLE agents RENAME COLUMN name TO identity")


MIGRATIONS = [
    (
        "schema_v1",
        """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    name TEXT UNIQUE,
    self_description TEXT,
    archived_at INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    channel_id TEXT,
    input TEXT NOT NULL,
    output TEXT,
    stderr TEXT,
    status TEXT DEFAULT 'pending',
    pid INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks(channel_id);
    """,
    ),
    (
        "rename_name_to_identity",
        _rename_name_to_identity,
    ),
]
