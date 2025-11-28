-- Add parent_channel_id for channel compaction lineage
ALTER TABLE channels ADD COLUMN parent_channel_id TEXT REFERENCES channels(channel_id);

CREATE INDEX IF NOT EXISTS idx_channels_parent ON channels(parent_channel_id);
