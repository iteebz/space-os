-- 001_foundation.sql
-- Unified schema for space.db covering agents, sessions, transcripts, bridge, memory, knowledge, and tasks.

PRAGMA journal_mode=WAL;

BEGIN;

-- ============================================================================
-- CORE DOMAIN TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS agents (
    agent_id TEXT PRIMARY KEY,
    identity TEXT NOT NULL UNIQUE,
    model TEXT,
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
    parent_channel_id TEXT REFERENCES channels(channel_id),
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    archived_at TEXT,
    pinned_at TEXT
);

CREATE TABLE IF NOT EXISTS spawns (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    parent_spawn_id TEXT,
    session_id TEXT,
    channel_id TEXT,
    constitution_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    pid INTEGER,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    ended_at TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE SET NULL,
    FOREIGN KEY (parent_spawn_id) REFERENCES spawns(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(agent_id),
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

-- ============================================================================
-- BRIDGE & COMMUNICATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS handoffs (
    handoff_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    from_agent TEXT NOT NULL,
    to_agent TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    summary TEXT NOT NULL,
    message_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    closed_at TEXT,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
    FOREIGN KEY (from_agent) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (to_agent) REFERENCES agents(agent_id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookmarks (
    reader_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_read_id TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%f', 'now')),
    PRIMARY KEY (reader_id, channel_id),
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);

-- ============================================================================
-- AGENT COGNITION
-- ============================================================================

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

-- ============================================================================
-- OBSERVABILITY
-- ============================================================================

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    provider TEXT NOT NULL,
    type TEXT NOT NULL,
    identity TEXT,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    UNIQUE (session_id, message_index)
);

-- ============================================================================
-- FULL-TEXT SEARCH
-- ============================================================================

CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts USING fts5(
    content,
    type UNINDEXED,
    provider UNINDEXED,
    content='transcripts',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='message_id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    message,
    topic,
    content='memories',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    content,
    domain,
    content='knowledge',
    content_rowid='rowid'
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Agents
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_provider ON sessions(provider);

-- Channels
CREATE INDEX IF NOT EXISTS idx_channels_parent ON channels(parent_channel_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_channel ON bookmarks(channel_id);

-- Spawns
CREATE INDEX IF NOT EXISTS idx_spawns_agent_created ON spawns(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_status ON spawns(status);
CREATE INDEX IF NOT EXISTS idx_spawns_channel_created ON spawns(channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_parent ON spawns(parent_spawn_id);
CREATE INDEX IF NOT EXISTS idx_spawns_parent_agent ON spawns(parent_spawn_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_spawns_parent_created ON spawns(parent_spawn_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_agent_parent_created ON spawns(agent_id, parent_spawn_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spawns_session_created ON spawns(session_id, created_at DESC);

-- Messages
CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id);

-- Handoffs
CREATE INDEX IF NOT EXISTS idx_handoffs_to_agent_status ON handoffs(to_agent, status);
CREATE INDEX IF NOT EXISTS idx_handoffs_channel ON handoffs(channel_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_from_agent ON handoffs(from_agent);

-- Memories
CREATE INDEX IF NOT EXISTS idx_memories_agent_created ON memories(agent_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_archived ON memories(archived_at);
CREATE INDEX IF NOT EXISTS idx_memories_core ON memories(core);

-- Knowledge
CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge(domain);
CREATE INDEX IF NOT EXISTS idx_knowledge_agent ON knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_archived ON knowledge(archived_at);

-- Tasks
CREATE INDEX IF NOT EXISTS idx_tasks_creator_created ON tasks(creator_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_status ON tasks(agent_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- Transcripts
CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_provider ON transcripts(provider);
CREATE INDEX IF NOT EXISTS idx_transcripts_timestamp ON transcripts(timestamp);
CREATE INDEX IF NOT EXISTS idx_transcripts_identity ON transcripts(identity);

-- ============================================================================
-- FTS TRIGGERS
-- ============================================================================

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

CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content)
    VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    DELETE FROM messages_fts WHERE rowid = old.rowid;
    INSERT INTO messages_fts(rowid, content)
    VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memory_fts(rowid, message, topic)
    VALUES (new.rowid, new.message, new.topic);
END;

CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memories BEGIN
    DELETE FROM memory_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memories BEGIN
    DELETE FROM memory_fts WHERE rowid = old.rowid;
    INSERT INTO memory_fts(rowid, message, topic)
    VALUES (new.rowid, new.message, new.topic);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, content, domain)
    VALUES (new.rowid, new.content, new.domain);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
    DELETE FROM knowledge_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
    DELETE FROM knowledge_fts WHERE rowid = old.rowid;
    INSERT INTO knowledge_fts(rowid, content, domain)
    VALUES (new.rowid, new.content, new.domain);
END;

PRAGMA user_version = 6;

COMMIT;
