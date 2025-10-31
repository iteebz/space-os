-- 002_chats.sql
-- Chat session tracking: link to tasks, store identity + metadata for audit trail

BEGIN;

CREATE TABLE IF NOT EXISTS chats (
    session_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    identity TEXT,
    task_id TEXT,
    file_path TEXT NOT NULL,
    message_count INTEGER,
    tools_used INTEGER DEFAULT 0,
    token_count INTEGER,
    first_message_at TEXT,
    last_message_at TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_chats_task_id ON chats(task_id);
CREATE INDEX IF NOT EXISTS idx_chats_identity ON chats(identity);
CREATE INDEX IF NOT EXISTS idx_chats_provider ON chats(provider);
CREATE INDEX IF NOT EXISTS idx_chats_created ON chats(created_at);

COMMIT;
