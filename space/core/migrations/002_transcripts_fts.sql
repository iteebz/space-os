-- 002_transcripts_fts.sql
-- Add distributed episodic memory: FTS5-indexed conversation transcripts

BEGIN;

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    provider TEXT NOT NULL,              -- 'claude', 'codex', 'gemini'
    role TEXT NOT NULL,                  -- 'user' or 'assistant'
    identity TEXT,                       -- agent identity (NULL until phase 2)
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,          -- unix epoch for efficient range queries
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE (session_id, message_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts USING fts5(
    content,
    role UNINDEXED,
    provider UNINDEXED,
    content='transcripts',
    content_rowid='id'
);

CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_provider ON transcripts(provider);
CREATE INDEX IF NOT EXISTS idx_transcripts_timestamp ON transcripts(timestamp);
CREATE INDEX IF NOT EXISTS idx_transcripts_identity ON transcripts(identity);

-- FTS5 triggers to keep index in sync with inserts/updates/deletes
CREATE TRIGGER IF NOT EXISTS transcripts_ai AFTER INSERT ON transcripts BEGIN
    INSERT INTO transcripts_fts(rowid, content, role, provider)
    VALUES (new.id, new.content, new.role, new.provider);
END;

CREATE TRIGGER IF NOT EXISTS transcripts_ad AFTER DELETE ON transcripts BEGIN
    DELETE FROM transcripts_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS transcripts_au AFTER UPDATE ON transcripts BEGIN
    DELETE FROM transcripts_fts WHERE rowid = old.id;
    INSERT INTO transcripts_fts(rowid, content, role, provider)
    VALUES (new.id, new.content, new.role, new.provider);
END;

COMMIT;
