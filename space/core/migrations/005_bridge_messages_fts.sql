-- 005_bridge_messages_fts.sql
-- Performance optimization: add FTS5 for bridge message search

BEGIN;

-- FTS5 virtual table for message full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='message_id'
);

-- FTS5 triggers to keep messages index in sync
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

-- Backfill existing messages into FTS
INSERT INTO messages_fts(rowid, content)
SELECT rowid, content FROM messages;

PRAGMA user_version = 5;

COMMIT;
