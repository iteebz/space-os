# Sessions — Provider Chat History

Sync and query chat histories from external LLM providers (Claude, Gemini, Codex).

## What

- **Provider-native** — Raw session metadata from Claude/Gemini/Codex
- **Session linking** — Spawns reference sessions via session_id
- **Transcript indexing** — FTS5 search across all session content

## CLI

```bash
sessions sync                                 # discover + sync all providers
sessions query <identity>                     # list agent's recent spawns
sessions query <spawn-id>                     # session details
sessions query <session-id>                   # session details
```

## Sync

Discovers sessions from provider CLI directories and syncs to space-os:

```bash
sessions sync
```

Providers: Claude (`~/.claude/projects/`), Gemini, Codex.

## Query

```bash
sessions query zealot                         # zealot's recent spawns
sessions query <spawn-id>                     # full session for spawn
```

## Storage

**sessions table:**
```sql
session_id TEXT PRIMARY KEY,    -- provider native UUID
provider TEXT NOT NULL,         -- claude, gemini, codex
model TEXT NOT NULL,
message_count INTEGER,
input_tokens INTEGER,
output_tokens INTEGER,
tool_count INTEGER,
source_path TEXT,
source_mtime REAL,
first_message_at TEXT,
last_message_at TEXT
```

**Linking:** Spawns reference sessions via `spawns.session_id`.