# sessions.db — Unified Message Index

**Motivation:** space-os conducts constitutional multiplicity across agent identities. Each CLI (Claude, Codex, Gemini) stores logs independently. Without unified indexing, decisions vanish between wakes.

**Solution:** Single SQLite table indexing all CLI messages (full text) with role, model, and identity tags.

---

## Schema

```
id        INTEGER PRIMARY KEY
cli       TEXT NOT NULL          # claude, codex, gemini
model     TEXT                   # model version
session_id TEXT NOT NULL         # CLI's native session UUID
timestamp TEXT NOT NULL          # ISO8601
identity  TEXT                   # agent identity (zealot, hailot, etc)
role      TEXT NOT NULL          # user or assistant
text      TEXT NOT NULL          # full message text
raw_hash  TEXT UNIQUE            # sha256(cli+session_id+timestamp+text)
```

**Constraints:**
- `UNIQUE(cli, session_id, timestamp)` — prevents duplicate syncs
- **Indexes:** identity, cli+session_id, timestamp

---

## Normalization

Three parsers convert CLI formats to canonical `SessionMsg`:

```python
@dataclass
class SessionMsg:
    role: str                    # user or assistant
    text: str                    # full message text
    timestamp: str               # ISO8601
    session_id: str
    model: str | None = None     # model version
```

- `norm_claude_jsonl(path)` — Claude JSONL
- `norm_codex_jsonl(path)` — Codex JSONL (extracts model from turn_context)
- `norm_gemini_json(path)` — Gemini JSON (maps "model"→"assistant")

All handle variable content formats (dict/list/string) transparently. Empty/malformed messages filtered during parsing.

---

## Sync

`sync(identity=None)` scans all three CLI directories, normalizes messages, and upserts to DB. Idempotent via raw_hash dedup. On wake, syncs automatically and tags untagged entries with agent identity.

Filtering during normalization dropped ~50% of raw log entries (empty, metadata-only, malformed).

---

## API

**Query functions:**
- `search(query, identity=None, limit=10)` — full-text search on text field
- `list_entries(identity=None, limit=20)` — recent entries
- `get_entry(entry_id)` — fetch single entry
- `get_surrounding_context(entry_id, context_size=5)` — entries from same session
- `sample(count=5, identity=None, cli=None)` — random sample

**CLI:**
```bash
sessions sync --identity zealot
sessions search "folio" --identity hailot --limit 10
sessions list --identity zealot --limit 20
sessions view 42284 --context 5
sessions sample --count 5 --cli codex
```

---

## Integration

Integrated into `wake --as <identity>` — auto-syncs and tags on wake.

Target: merge `search()` into `context --as <identity> "<query>"` for unified concept retrieval across canon + memory + sessions.

---

## Facts

- **Location:** `~/.space/sessions.db` (gitignored, regenerable)
- **Size:** ~43K messages across all CLIs (31K Claude, 8K Gemini, 4K Codex)
- **Tests:** 12/12 passing
- **Sync time:** <1s (on recent logs)
- **Memory:** Full text stored, no truncation
- **Dedup:** sha256(cli+session_id+timestamp+text) prevents re-indexing same message
