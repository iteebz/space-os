-- 001_foundation.sql
-- Unified schema for space.db covering agents, sessions, transcripts, bridge, memory, knowledge, and tasks.

BEGIN;

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL UNIQUE,
    model TEXT NOT NULL,
    constitution TEXT,
    role TEXT,
    spawn_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_active_at TEXT,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    topic TEXT,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    pinned_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    source_path TEXT,
    source_mtime REAL,
    source_size INTEGER,
    first_message_at TEXT,
    last_message_at TEXT
);

CREATE TABLE IF NOT EXISTS spawns (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    session_id TEXT,
    channel_id TEXT,
    constitution_hash TEXT,
    is_ephemeral BOOLEAN NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    pid INTEGER,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual',
    message TEXT NOT NULL,
    core INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    agent_id TEXT,
    content TEXT NOT NULL,
    project TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (creator_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bookmarks (
    reader_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_read_id TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    PRIMARY KEY (reader_id, channel_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    provider TEXT NOT NULL,              -- 'claude', 'codex', 'gemini'
    type TEXT NOT NULL,                  -- 'user' or 'assistant'
    identity TEXT,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,          -- unix epoch for efficient range queries
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE (session_id, message_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts USING fts5(
    content,
    type UNINDEXED,
    provider UNINDEXED,
    content='transcripts',
    content_rowid='id'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);

CREATE INDEX IF NOT EXISTS idx_spawns_agent_created ON spawns(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_status ON spawns(status);
CREATE INDEX IF NOT EXISTS idx_spawns_channel_created ON spawns(channel_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider);

CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);

CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);

CREATE INDEX IF NOT EXISTS idx_tasks_creator_created ON tasks(creator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_status ON tasks(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_provider ON transcripts(provider);
CREATE INDEX IF NOT EXISTS idx_transcripts_timestamp ON transcripts(timestamp);
CREATE INDEX IF NOT EXISTS idx_transcripts_identity ON transcripts(identity);

CREATE INDEX IF NOT EXISTS idx_bookmarks_channel ON bookmarks(channel_id);

-- FTS5 triggers to keep index in sync with inserts/updates/deletes
CREATE TRIGGER IF NOT EXISTS transcripts_ai AFTER INSERT ON transcripts BEGIN
    INSERT INTO transcripts_fts(rowid, content, type, provider)
    VALUES (new.id, new.content, new.type, new.provider);
END;

CREATE TRIGGER IF NOT EXISTS transcripts_ad AFTER DELETE ON transcripts BEGIN
    DELETE FROM transcripts_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS transcripts_au AFTER UPDATE ON transcripts BEGIN
    DELETE FROM transcripts_fts WHERE rowid = old.id;
    INSERT INTO transcripts_fts(rowid, content, type, provider)
    VALUES (new.id, new.content, new.type, new.provider);
END;

PRAGMA user_version = 1;

COMMIT;
