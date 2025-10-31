-- 003_chat_tokens.sql
-- Track input and output tokens for cost analysis and saturation detection

BEGIN;

ALTER TABLE chats ADD COLUMN input_tokens INTEGER;
ALTER TABLE chats ADD COLUMN output_tokens INTEGER;

COMMIT;
