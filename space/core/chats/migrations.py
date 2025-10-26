MIGRATIONS = [
    (
        "schema_v1",
        """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    identity TEXT,
    task_id TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cli, session_id)
);

CREATE TABLE IF NOT EXISTS syncs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    session_id TEXT NOT NULL,
    last_byte_offset INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cli, session_id),
    FOREIGN KEY(cli, session_id) REFERENCES sessions(cli, session_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_identity ON sessions(identity);
CREATE INDEX IF NOT EXISTS idx_sessions_task_id ON sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_sessions_cli ON sessions(cli);
CREATE INDEX IF NOT EXISTS idx_syncs_session ON syncs(cli, session_id);
        """,
    ),
    (
        "add_messages_table",
        """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cli TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_id TEXT,
    role TEXT NOT NULL,
    content TEXT,
    timestamp TIMESTAMP,
    cwd TEXT,
    tool_type TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cli, session_id) REFERENCES sessions(cli, session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(cli, session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_cwd ON messages(cwd);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);
        """,
    ),
]
