# Chats Primitive

Chats is a unified log for conversation history across Claude Code, Codex, and Gemini CLI tools. It normalizes provider-specific formats into a queryable index.

## Quick Start

**Discover sessions:**
```bash
chats discover
```

**Sync messages for your identity:**
```bash
chats sync --as hailot
```

**Search across chats:**
```bash
context "query" --as hailot
```

## Design Philosophy

- **Immutable source**: Raw JSONL/JSON from providers never modified
- **Indexed**: `chats.db` tracks sessions and sync state (offset-based delta sync)
- **Provider-agnostic**: Abstracts Claude, Codex, Gemini differences
- **Linked**: Sessions correlated to space identities and spawn tasks

## Database

**sessions table** — Chat session registry
```
cli              provider name (claude, codex, gemini)
session_id       provider's session ID
file_path        path to JSONL/JSON
identity         linked space identity (optional)
task_id          linked spawn task (optional)
discovered_at    when indexed
```

**syncs table** — Incremental sync state
```
cli              provider name
session_id       provider's session ID
last_byte_offset where we stopped parsing (delta sync)
last_synced_at   timestamp of last sync
is_complete      marked complete when writes stop
```

## API Reference

### Discovery & Indexing

```python
from space.os import chats

chats.discover()  # → {cli: count_discovered}
```

Scans `~/.claude/projects/`, `~/.codex/sessions/`, `~/.gemini/tmp/` and indexes into `sessions` table.

### Sync & Retrieval

```python
chats.sync(identity="hailot")   # Sync all sessions for identity
chats.sync(session_id="abc123") # Sync specific session (delta from offset)
```

Parses messages from last offset, updates `syncs` table state.

### Searching

```python
results = chats.search("query", identity="hailot")
# → [{source, cli, session_id, identity, matches, timestamp, reference}]
```

### Linking

```python
chats.link(session_id="abc123", identity="hailot", task_id="task-xyz")
chats.get_by_identity("hailot")  # → [sessions...]
chats.get_by_task_id("task-xyz") # → [sessions...]
```

Correlate chats to identities and spawned tasks.

### Export

```python
content = chats.export(session_id="abc123", cli="claude")
```

Raw JSONL/JSON content as string.

## Workflow

### Setup
```bash
space init              # Initializes chats.db
chats discover          # Indexes all provider sessions
```

### During Agent Work
```bash
space wake --as hailot  # Automatically syncs hailot's chats
context "topic"         # Searches chats + memory + knowledge
```

### Manual Operations
```bash
chats discover          # Re-scan providers for new sessions
chats sync --as hailot  # Force resync for identity
chats link <id> --as <id>  # Manual identity linkage
```

## Provider Support

| Provider | Location | Format | Notes |
|----------|----------|--------|-------|
| Claude | `~/.claude/projects/` | JSONL | Flat files |
| Codex | `~/.codex/sessions/` | JSONL | Nested dirs |
| Gemini | `~/.gemini/tmp/{hash}/` | JSON | Hashed dirs (tmp only) |

## Technical Details

### Offset-Based Sync

Avoids re-parsing entire JSONL files on each sync:
- Track `last_byte_offset` per session
- Parse only from offset onward
- Update offset after each sync

### Delta Sync

Only syncs chats with new messages:
- Check file mtime vs `last_synced_at`
- Parse from offset if newer
- No-op if unchanged

### Gemini Limitation

Gemini uses `~/.gemini/tmp/` (temporary). Use `/chat save <tag>` to persist sessions manually, then reference them in `.config/google-generative-ai/checkpoints/`.

## Next Steps

- **Task linkage**: Agents report chat_id via manifest file on completion
- **Message cache**: Optional table for repeated queries
- **Synthesis**: Export chat learnings to knowledge/memory
