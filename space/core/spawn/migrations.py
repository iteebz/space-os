MIGRATIONS = [
    (
        "schema",
        """
CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT UNIQUE NOT NULL,
    constitution TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
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
        "add_last_active_at",
        """
ALTER TABLE agents ADD COLUMN last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
UPDATE agents SET last_active_at = created_at WHERE last_active_at IS NULL;
""",
    ),
]
