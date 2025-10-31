-- 004_drop_links.sql
-- Remove unused links table (superseded by memory supersession fields)

BEGIN;

DROP TABLE IF EXISTS links;

COMMIT;
