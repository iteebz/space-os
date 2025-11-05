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

# Search as agent (Phase 2 - identity filtering)
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
- Only included with `--as <identity>` (Phase 2)
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

**Phase 1 (current):**
- No semantic search (requires exact or prefix matching)
- Identity scoping not fully implemented (no permission checks yet)
- No concept of "relevance" across different query types (just BM25 for sessions + recency everywhere)
- Tasks deliberately excluded (work ledger ≠ knowledge ledger)

**Why these constraints exist:**
- Keep system simple and auditable
- Avoid embedding complexity until absolutely necessary
- Force good data hygiene (strict naming conventions, domain tagging)

## Future Work

**Phase 2: Identity Linking**
- Populate `transcripts.identity` from spawn relationships
- Enable true `context "query" --as agent` filtering
- Show agent-private memory only to that agent
- Add visibility/permission checks

**Phase 3: Query Language**
- Document FTS5 Boolean syntax: `"phrase" AND keyword`, `term*`, `NEAR()`
- Add `context --suggest` to show queryable domains/paths
- Auto-complete on knowledge domains and canon file paths

**Phase 4: Discovery & Metrics**
- Log all queries + result counts to identify zero-result searches
- `context --related "topic"` to find semantically adjacent content
- Audit trail for understanding what context sources are actually used

**Phase 5: Reference Drilling**
- `context get <reference>` to show full context around a result
- `sessions <session-id>` to view complete transcript (already exists)

**When embeddings become necessary:**
- Natural language intent queries ("how do agents think?") without exact phrase matching
- Cross-domain concept discovery without manual domain tagging
- Relevance ranking that understands semantic similarity
- Estimated timeline: 50k+ transcripts + 2+ years of usage patterns showing gaps

**Better alternatives to embeddings (explore first):**
- Better canonicalization (synonym tagging in knowledge domains)
- Query expansion (user builds saved queries)
- Related-link graphs (users manually wire connections)

## Storage

Context doesn't own storage; it queries across:
- `transcripts` table (sessions) via FTS5
- `memories` table (memory) — currently not searched (Phase 1)
- `knowledge` table (knowledge) — SQL LIKE search on domain + content
- `messages` table (bridge) — SQL LIKE search on content + channel name
- Canon directory (human docs) — filesystem scan + regex match

See [Sessions](sessions.md), [Memory](memory.md), [Knowledge](knowledge.md), [Bridge](bridge.md) for schema details.

## See Also

- [Sessions](sessions.md) — provider session sync and transcript indexing
- [Memory](memory.md) — private agent working context
- [Knowledge](knowledge.md) — multi-agent shared discoveries
- [Bridge](bridge.md) — ephemeral coordination channels
