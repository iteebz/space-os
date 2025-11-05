# Sessions — Provider-Native Chat History

First-class data primitive for ingesting and querying chat histories from external LLM providers (Claude, Gemini, Codex).

## What

- **Provider-native** — Raw session metadata from Claude/Gemini/Codex
- **Schema-separated** — Distinct from spawn tracking (see [spawn.md](spawn.md))
- **Session linking** — Spawns reference sessions via session_id (optional for interactive, required for task spawns)
- **File-based** — Chat files synced to `~/.space/sessions/{provider}/...`

## CLI

```bash
sessions sync                    # discover + sync all provider sessions
sessions <identity>              # list agent's recent spawns (20 most recent)
sessions <spawn-id>              # display full JSONL session log + metadata
```

For full options: `sessions --help`

## Patterns

**Sync provider sessions:**
```bash
sessions sync
```

**List agent's recent spawns:**
```bash
sessions zealot-1
```

**View full session transcript:**
```bash
sessions <spawn-id>
```

## Storage

**sessions table:**
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,    -- provider native UUID
    provider TEXT NOT NULL,         -- claude, gemini, codex
    model TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    source_path TEXT,               -- provider file location
    source_mtime REAL,              -- file modification time
    first_message_at TEXT,
    last_message_at TEXT
);
```

**Files:** `~/.space/sessions/{provider}/{path}/...` (synced on-demand)

**Linking:** Spawns reference sessions via foreign key (`spawns.session_id`)
- Optional for interactive spawns
- Required for task spawns (bridge mentions, headless)
