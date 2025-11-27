-- 003_spawn_parent_index.sql
-- Index for parent_spawn_id to optimize tree queries (get_spawn_children, get_all_root_spawns).

BEGIN;

CREATE INDEX IF NOT EXISTS idx_spawns_parent ON spawns(parent_spawn_id);

PRAGMA user_version = 3;

COMMIT;
