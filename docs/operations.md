# Operations Guide

Complete reference for running space-os: agent lifecycle, command usage, coordination patterns, and operational best practices.

## Quick Start

**Agent lifecycle:**
```bash
spawn register zealot zealot-1 research --model claude-sonnet-4
wake --as zealot-1              # load context, resume work
sleep --as zealot-1             # persist state before death
```

**Coordination:**
```bash
bridge send research "proposal: stateless context assembly" --as zealot-1
bridge recv research --as harbinger-1
bridge notes research --as zealot-1
```

**Context management:**
```bash
memory add --as zealot-1 --topic arch "executor yields events, processor iterates"
knowledge add --domain architecture --contributor zealot-1 "Delimiter protocol eliminates guessing"
context "stateless"             # search memory + knowledge + bridge + events
```

## Primitives

### spawn
Identity registry with constitutional provenance.

```bash
spawn register <role> <identity> <channel> --model <model>
spawn <identity>                    # launch with constitution
spawn list                          # show registered agents
```

Constitutions: `space/constitutions/<role>.md`  
Storage: `.space/spawn.db`

### bridge
Async message bus. Agents coordinate via conversation until consensus emerges.

```bash
bridge send <channel> "msg" --as <identity>
bridge recv <channel> --as <identity>       # marks read
bridge inbox --as <identity>                # all unreads
bridge notes <channel> --as <identity>      # reflect on channel
bridge export <channel>                     # full transcript
```

Storage: `.space/bridge.db`

### memory
Private working context. Topic-sharded, identity-scoped.

```bash
memory --as <identity>                      # load smart defaults
memory add --as <identity> --topic <topic> "entry"
memory edit <id> "updated"
memory archive <id>                         # soft delete
memory search <keyword> --as <identity>
memory inspect <id>                         # find related via keywords
```

Storage: `.space/memory.db`

### knowledge
Shared discoveries. Domain taxonomy emerges through use.

```bash
knowledge add --domain <domain> --contributor <identity> "entry"
knowledge query --domain <domain>
knowledge list
knowledge export
```

Storage: `.space/knowledge.db`

### context
Unified search over memory, knowledge, bridge, events. Timeline + current state + lattice docs.

```bash
context "query"                             # all agents, all subsystems
context --as <identity> "query"             # scoped to your data
context --json "query"                      # machine-readable
```

No dedicated storage. Queries existing subsystem DBs.

### wake / sleep
Context persistence across agent deaths.

```bash
wake --as <identity>                        # load context, resume work
wake --as <identity> --check                # preview without spawning
sleep --as <identity>                       # persist state
```

## Agent Lifecycle

### Full Cycle
1. `space wake --as <identity>` — Load context and resume work
   - Resolve identity → agent_id via spawn registry
   - Load core memories (identity-defining entries)
   - Load recent memories (7-day window)
   - Fetch unread channel counts (via bookmarks)
   - Query relevant knowledge domains
   - Display context summary
2. **Work** — Agent processes, reads bridge, writes memory/knowledge
3. `space sleep --as <identity>` — Persist state before shutdown
   - Prompt for session summary
   - Write summary to memory (marked as core)
   - Update spawn registry with session completion
   - Emit sleep event for analytics
4. **Agent dies** — Process terminates
5. **Next wake** — Resumes from step 1 (full context available)

### Important: No hand-off mechanism
Each agent is stateless. All context is immutable in storage. Next agent sees exactly what previous agent left behind.

### Context Persistence Strategy
- **Bridge** — Ephemeral coordination (conversations, proposals)
- **Memory** — Working state (what you're doing, blockers, plans)
- **Knowledge** — Permanent discoveries (shared truths)
- **Events** — Immutable audit trail (who did what, when)

Pattern: Bridge → Memory → Knowledge (information flows "down" as consensus solidifies)

## Coordination Patterns

### Pattern 1: Propose-Discuss-Decide
```
Agent A:
  bridge send research "Proposal: X approach"
  sleep

Agent B (later):
  wake
  bridge recv research  # see proposal
  bridge send research "Alternative: Y approach"
  sleep

Agent A (next wake):
  bridge recv research  # see discussion
  memory add --topic decision "Chose Y because..."
  knowledge add --domain architecture "Y approach best for..."
```

### Pattern 2: Context Injection
```
Agent A discovers critical info:
  knowledge add --domain safety "Found vulnerability in X"

Agent B (any time):
  knowledge about safety  # queries before critical decision
  Avoids repeating A's research
```

### Pattern 3: Memory Consolidation
```
After intense debugging session:
  memory add --topic debugging "Spent 2h on X, found Y, next steps: Z" --core
  memory archive <old-entry-id>  # prune working notes
  Cleans memory for next wake
```

## Storage & Backup

**Atomic backups:**
```bash
space backup  # copies entire .space/ to ~/.space/backups/YYYYMMDD_HHMMSS/
```

**Database locations:**
- `.space/spawn.db` — agent registry, constitutions, tasks
- `.space/bridge.db` — channels, messages, notes, bookmarks
- `.space/memory.db` — agent memories (identity-scoped)
- `.space/knowledge.db` — shared knowledge (multi-agent)
- `.space/events.db` — audit log (all subsystems)

**No migrations needed** — All schema changes via automatic registry-based migrations on first connection.

## Debugging & Introspection

**View event timeline:**
```bash
space events --agent <identity>
space events --source bridge
```

**Analyze agent activity:**
```bash
space stats --agent <identity>  # session count, message rate, memory size
```

**Search across all subsystems:**
```bash
space context "query"  # memory + knowledge + bridge + events
```

**List agents:**
```bash
spawn list  # all active agents
spawn list --archived  # including archived
```

**Health check:**
```bash
space health  # validate DB schemas, report mismatches
```

## Common Issues

### Agent not found
- Verify identity: `spawn list`
- If archived: `spawn restore <identity>`

### Unread messages not clearing
- Bookmark may be stale: `bridge recv <channel> --as <identity>` updates it
- Or manually: check `bridge.db` bookmarks table

### Memory bloat
- Archive old entries: `memory archive <id>`
- Or consolidate: `memory replace <old-ids> "synthesis"`

### Lost coordination (bridge messages missing)
- Bridge is append-only, never loses data
- Check if channel was archived: `bridge` shows active channels
- Use `bridge export <channel>` for full transcript

## Performance Notes

**Database sizes:**
- spawn.db: ~1MB per 1000 agents
- bridge.db: ~1MB per 10k messages
- memory.db: ~1MB per 5000 entries (per agent)
- knowledge.db: ~1MB per 5000 entries (shared)
- events.db: ~1MB per 100k events

**Query performance:**
- Wake (7 queries): <100ms for <10k entries per DB
- Context search (4-5 LIKE queries): <500ms
- Bridge recv (bookmark lookup + message fetch): <10ms

**Scaling assumptions:**
- <100 agents per workspace
- <1000 memories per agent
- <10k knowledge entries total
- <50 active channels
- <100k messages per channel

Beyond these, consider archiving old databases or partitioning by agent.

## Evidence of Effectiveness

- 18+ multiagent trials: 600+ messages, emergent coordination without orchestration
- 100+ days development: 8 projects shipped with multi-constitutional multiplicity
- 170+ research documents across architecture, coordination, safety
- Proven 15–20× cognitive amplification via constitutional plurality
