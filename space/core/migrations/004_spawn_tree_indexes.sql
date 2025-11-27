-- 004_spawn_tree_indexes.sql
-- Boost spawn tree traversal by indexing creation-ordered parent relationships.

BEGIN;

CREATE INDEX IF NOT EXISTS idx_spawns_parent_created
    ON spawns(parent_spawn_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_spawns_agent_parent_created
    ON spawns(agent_id, parent_spawn_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_spawns_session_created
    ON spawns(session_id, created_at DESC);

PRAGMA user_version = 4;

COMMIT;
