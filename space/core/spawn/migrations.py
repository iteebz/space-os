def _rename_name_to_identity(conn):
    """Rename 'name' column to 'identity' if it exists."""
    cursor = conn.execute("PRAGMA table_info(agents)")
    columns = {row[1] for row in cursor.fetchall()}
    if "name" in columns and "identity" not in columns:
        conn.execute("ALTER TABLE agents RENAME COLUMN name TO identity")


def _add_constitution_and_base_agent(conn):
    """Add constitution and base_agent to agents table."""
    cursor = conn.execute("PRAGMA table_info(agents)")
    columns = {row[1] for row in cursor.fetchall()}

    if "constitution" not in columns:
        conn.execute("ALTER TABLE agents ADD COLUMN constitution TEXT NOT NULL DEFAULT ''")
    if "base_agent" not in columns:
        conn.execute("ALTER TABLE agents ADD COLUMN base_agent TEXT NOT NULL DEFAULT ''")
    conn.execute("DELETE FROM agents WHERE identity IS NULL")


MIGRATIONS = [
    (
        "schema_v1",
        """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT UNIQUE NOT NULL,
    constitution TEXT NOT NULL,
    base_agent TEXT NOT NULL,
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
    (
        "add_constitution_and_base_agent",
        _add_constitution_and_base_agent,
    ),
]
