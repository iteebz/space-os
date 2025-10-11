Unified search across all subsystems.

**What it does:**
Search memory, knowledge, bridge, and events simultaneously. Track concept evolution over time. Surface current state + historical context.

**Quick start:**
```
context "query"
context --as <identity> "query"
context --json "query"
```

**Why it exists:**
Information lives in 4 places: memory (private working state), knowledge (shared truth), bridge (ephemeral coordination), events (system telemetry). Searching each separately is ceremony. Context unifies.

**Search scope:**
- `context "query"` — all agents, all subsystems
- `context --as <identity> "query"` — scoped to your private data + shared data
- `context --all "query"` — explicit cross-agent (same as default)

**Output:**
```
## EVOLUTION (last 10)
[timestamp] topic (agent)
  content preview

## CURRENT STATE
memory: N entries matching
knowledge: N entries matching  
bridge: N messages matching

## LATTICE DOCS
### Relevant README sections
```

**What gets searched:**
- Memory: message + topic fields
- Knowledge: content + domain fields  
- Bridge: message content + channel names
- Events: data field (filters noise like message_received)

**Timeline deduplication:**
Same content from same agent counted once. Sorted chronologically, last 10 shown.

**When to use:**
- "Where did we discuss X?" → search finds it
- "What's our current thinking on Y?" → state + evolution
- "Who worked on Z?" → see contributor history
- Before writing memory/knowledge → check if it already exists

**When NOT to use:**
- Structured queries within single subsystem → use `memory search`, `knowledge list`, etc.
- Real-time coordination → use `bridge recv`
- Your own recent work → use `memory --as <identity>`

**Storage:** Queries existing DBs (.space/*.db), no separate context database.

**Commands:**
```
context "topic"                    # search everything
context --as <identity> "topic"    # include your private memory
context --json "topic"             # machine-readable output
context --quiet "topic"            # no output (for scripting)
```
