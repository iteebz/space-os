Unified context access across memory + knowledge.

Search your working memory (identity-scoped) and shared knowledge (collective truth) in one query.

**Quick start:**
```
context "topic" --as <identity>    # search your memories + shared knowledge
context "topic"                     # search only shared knowledge
```

**What it searches:**
- **Memory**: Your working context (identity-scoped, private)
- **Knowledge**: Shared discoveries (cross-agent, public)
- **Bridge**: Communication history (channels, messages)
- **Events**: System timeline (spawns, sessions, changes)

**Results show:**
- Evolution timeline (chronological)
- Current state (active entries)
- Cross-links (memory ↔ knowledge references)

**When to use:**
- Starting work: `wake --as zealot-2` includes recent context
- Deep dive: `context "schema-drift" --as zealot-2` for full history
- Research: `context "render-refactor"` for shared knowledge only

**Management:**
- `memory --as <identity>` — view/prune/archive your working memory
- `knowledge` — manage shared discoveries

Context is read-only. Use memory/knowledge commands to modify.
