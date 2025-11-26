-- 002_handoffs.sql
-- Handoffs: explicit responsibility transfer between agents within channels.

BEGIN;

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

CREATE INDEX IF NOT EXISTS idx_handoffs_to_agent_status ON handoffs(to_agent, status);
CREATE INDEX IF NOT EXISTS idx_handoffs_channel ON handoffs(channel_id);
CREATE INDEX IF NOT EXISTS idx_handoffs_from_agent ON handoffs(from_agent);

PRAGMA user_version = 2;

COMMIT;
