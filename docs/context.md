# Context — Unified Search Primitive

Search across all knowledge sources: agent memory, shared knowledge, bridge conversations, provider sessions, and human canon. Single query returns relevant results from all sources, ranked by relevance and recency.

## What

- **Cross-source search** — Query memory + knowledge + bridge + sessions + canon in one command
- **Live data** — No indexing overhead; searches query live tables directly
- **FTS5-backed** — Full-text search on sessions via SQLite FTS5 with BM25 relevance scoring
- **Smart ranking** — Results ordered by relevance (BM25 score) + recency, canon filenames prioritized over content
- **Clean display** — Results grouped by source, truncated smartly at sentence boundaries with references for drilling deeper

## CLI

```bash
# Search everything
context "architecture"

# Search specific scope
context "memory" --scope sessions
context "constitution" --scope canon

# Search as agent (filter by identity)
context "spawn design" --as zealot

# JSON output for scripts
context "auth" --json

# Suppress output (useful in scripts)
context "query" --quiet
```

For full options: `context --help`

## Examples

```bash
# Find canon files and session discussions about architecture
$ context "architecture"
## RESULTS

SESSIONS (50)
You:
  lets fix up security architecture to use the mock_tool...
  ref: session-2025-10-13T10-55-30eb2a7b

Agent:
  [gemini] Bridge Architecture Reference...
  ref: session-2025-10-08T05-19-6252946c

CANON (147)
  archaeology/space_experimental_architecture.md: Bridge Architecture Reference...
  ref: canon:archaeology/space_experimental_architecture.md

# Find constitution definitions
$ context "constitution"
## RESULTS

CANON (126)
  constitutions/cupid.md: # CUPID CONSTITUTION You are Cupid...
  ref: canon:constitutions/cupid.md
  
  constitutions/roast.md: # LIFE ROASTER CONSTITUTION
  ref: canon:constitutions/roast.md
```

## How It Works

Context searches across five sources in parallel:

**Sessions (implicit episodic memory)**
- Full-text search on transcript table via FTS5
- BM25 scoring for relevance
- Returns user messages and agent responses separated
- Use for: "what was discussed about X?" / "how did we solve Y before?"

**Canon (human knowledge)**
- Scans git-backed markdown files
- Prioritizes filename matches over content (e.g., searching "constitution" finds `constitutions/` directory first)
- Use for: "what's our policy on X?" / "design principles for Y?"

**Knowledge (multi-agent discoveries)**
- Domain-indexed shared insights
- Searchable by domain and content
- Use for: "what do we know about X?" / "shared patterns for Y?"

**Memory (single-agent working context)**
- Private working notes per agent
- Only included with `--as <identity>`
- Use for: agent's personal context during execution

**Bridge (ephemeral coordination)**
- Channel messages and conversation history
- Searchable by content and channel name
- Use for: "what was the decision on X?" / "discussion history for Y?"

Results are displayed grouped by source, with smart truncation at sentence/paragraph boundaries. Truncated entries show `[…]` indicator. References (`ref:`) let you drill deeper into specific results.

## Algorithm

**Ranking:** Results ordered by relevance (BM25 score for sessions/FTS) + recency (most recent first)

**Canon prioritization:** Filename matches appear before content matches (searching "constitution" finds `constitutions/*.md` before docs mentioning constitution in body)

**Filtering:** Only active (non-archived) results returned. Sessions limited to 50 most relevant results.

**Display strategy:**
- Sessions split into "You:" and "Agent:" sections for clarity
- Text truncated at sentence boundary (not mid-word) up to 150 chars
- Each result shows reference for tracing back to source

## Constraints & Limitations

- No semantic search (requires exact or prefix matching)
- No concept of "relevance" across different query types (just BM25 for sessions + recency everywhere)
- Tasks deliberately excluded (work ledger ≠ knowledge ledger)
- No permission checks on identity-scoped queries (filtering only, no access control)

## Advanced Queries

FTS5 supports advanced syntax for sessions search:

```bash
# Phrase search
context "exact phrase in quotes"

# Boolean AND
context "architecture AND design"

# Wildcards
context "spawn*"

# NEAR operator (words within N positions)
context "NEAR(spawn, session, 5)"
```

## Storage

Context doesn't own storage; it queries across:
- `transcripts` table (sessions) via FTS5
- `memories` table (memory) — agent-scoped via `--as <identity>`
- `knowledge` table (knowledge) — SQL LIKE search on domain + content
- `messages` table (bridge) — SQL LIKE search on content + channel name
- Canon directory (human docs) — filesystem scan + regex match

See [Sessions](sessions.md), [Memory](memory.md), [Knowledge](knowledge.md), [Bridge](bridge.md) for schema details.

## See Also

- [Sessions](sessions.md) — provider session sync and transcript indexing
- [Memory](memory.md) — private agent working context
- [Knowledge](knowledge.md) — multi-agent shared discoveries
- [Bridge](bridge.md) — ephemeral coordination channels
