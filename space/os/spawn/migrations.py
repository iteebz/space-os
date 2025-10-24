import sqlite3


def _drop_canonical_id(conn: sqlite3.Connection):
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

    conn.execute(
        """
        CREATE TABLE agents_new (
            agent_id TEXT PRIMARY KEY,
            name TEXT,
            self_description TEXT,
            archived_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.execute(f"""
        INSERT INTO agents_new ({col_list})
        SELECT {col_list} FROM agents
    """)

    conn.execute("DROP TABLE agents")
    conn.execute("ALTER TABLE agents_new RENAME TO agents")


def _migrate_spawn_agents_id_to_agent_id(conn: sqlite3.Connection):
    """Rename agents.id to agent_id."""
    cursor = conn.execute("PRAGMA table_info(agents)")
    cols = {row[1] for row in cursor.fetchall()}
    if "agent_id" in cols:
        return
    conn.executescript(
        """
        CREATE TABLE agents_new (
            agent_id TEXT PRIMARY KEY,
            name TEXT UNIQUE,
            self_description TEXT,
            archived_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO agents_new SELECT id, name, self_description, archived_at, created_at FROM agents;
        DROP TABLE agents;
        ALTER TABLE agents_new RENAME TO agents;
    """
    )


def _migrate_spawn_tasks_id_to_task_id(conn: sqlite3.Connection):
    """Rename tasks.id to task_id, identity to agent_id, make channel_id optional."""
    cursor = conn.execute("PRAGMA table_info(tasks)")
    cols = {row[1] for row in cursor.fetchall()}
    if "task_id" in cols:
        return
    conn.executescript(
        """
        CREATE TABLE tasks_new (
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
        INSERT INTO tasks_new SELECT id, identity, channel_id, input, output, stderr, status, pid, started_at, completed_at, created_at FROM tasks;
        DROP TABLE tasks;
        ALTER TABLE tasks_new RENAME TO tasks;
        CREATE INDEX idx_tasks_status ON tasks(status);
        CREATE INDEX idx_tasks_agent ON tasks(agent_id);
        CREATE INDEX idx_tasks_channel ON tasks(channel_id);
    """
    )


def _add_pid_to_tasks(conn: sqlite3.Connection):
    """Add pid column to tasks table for process tracking."""
    cursor = conn.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    if "pid" in columns:
        return
    conn.execute("ALTER TABLE tasks ADD COLUMN pid INTEGER")


MIGRATIONS = [
    ("drop_canonical_id", _drop_canonical_id),
    ("add_pid_to_tasks", _add_pid_to_tasks),
    ("migrate_spawn_agents_id_to_agent_id", _migrate_spawn_agents_id_to_agent_id),
    ("migrate_spawn_tasks_id_to_task_id", _migrate_spawn_tasks_id_to_task_id),
]
