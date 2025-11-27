# Context — Unified Search

Search across all knowledge sources in one query: memory, knowledge, canon, bridge, sessions.

## What

- **Cross-source search** — Query all primitives simultaneously
- **Live data** — No indexing overhead; searches query live tables
- **FTS5-backed** — Full-text search on sessions via SQLite FTS5 with BM25 scoring
- **Scope filtering** — Limit search to specific sources

## CLI

```bash
context "query"
context "query" --as <identity>              # include agent's private memory
context "query" --scope sessions             # search specific source
context "query" --all --as <identity>        # include all agents' memories
context "query" --json                       # JSON output
```

Scopes: `all` (default), `memory`, `knowledge`, `canon`, `bridge`, `sessions`

## Sources

**Sessions** — Provider chat history (Claude/Gemini/Codex). FTS5 with BM25 ranking.

**Canon** — Git-backed markdown files. Filename matches prioritized over content.

**Knowledge** — Multi-agent shared discoveries. Domain-indexed.

**Memory** — Private agent working context. Requires `--as <identity>`.

**Bridge** — Channel messages and conversation history.

## Examples

```bash
context "architecture"                        # search everything
context "spawn design" --as zealot            # include zealot's memory
context "constitution" --scope canon          # canon files only
context "auth" --scope sessions               # session transcripts only
```

## Storage

Context doesn't own storage. It queries:
- `transcripts` table (sessions) via FTS5
- `memories` table (memory)
- `knowledge` table (knowledge)
- `messages` table (bridge)
- Canon directory (filesystem)
