-- 003_performance_indexes.sql
-- Performance optimization: add missing indexes and FTS for memories

BEGIN;

-- Index for spawn tree traversal (parent_spawn_id queries)
-- Used by: get_spawn_children, get_all_root_spawns, get_root_spawns_for_agent
CREATE INDEX IF NOT EXISTS idx_spawns_parent ON spawns(parent_spawn_id);

-- Composite index for agent root spawn queries
-- Optimizes: get_root_spawns_for_agent (WHERE parent_spawn_id IS NULL AND agent_id = ?)
CREATE INDEX IF NOT EXISTS idx_spawns_parent_agent ON spawns(parent_spawn_id, agent_id);

-- FTS5 virtual table for memory full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    message,
    topic,
    content='memories',
    content_rowid='rowid'
);

-- FTS5 triggers to keep memory index in sync
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

-- Backfill existing memories into FTS
INSERT INTO memory_fts(rowid, message, topic)
SELECT rowid, message, topic FROM memories;

-- FTS5 virtual table for knowledge full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    content,
    domain,
    content='knowledge',
    content_rowid='rowid'
);

-- FTS5 triggers to keep knowledge index in sync
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

-- Backfill existing knowledge into FTS
INSERT INTO knowledge_fts(rowid, content, domain)
SELECT rowid, content, domain FROM knowledge;

PRAGMA user_version = 3;

COMMIT;
