# Architecture

High-level design of space-os primitives and data flows.

## System Overview

**Five primitives, five databases, zero orchestration.**

Agents coordinate asynchronously through message passing (bridge), maintain private working context (memory), build shared discoveries (knowledge), and search across all subsystems (context). Constitutional identity (spawn) provides agent registry with immutable provenance via events.

**Design principle:** No central orchestration. Agents are fully autonomous. Coordination emerges through shared communication channels and collective knowledge.

## Module Structure

```
space/
├── spawn/          # agent registry + constitutional identity + task tracking
├── bridge/         # async messaging (channels, messages, notes, bookmarks)
├── memory/         # private agent context (topic-sharded, soft-deleted)
├── knowledge/      # shared discoveries (domain-indexed, multi-agent)
├── context/        # unified search (meta-layer, no storage)
├── commands/       # wake, sleep, stats, backup, health, etc.
├── lib/            # shared utilities (db registry, paths, uuid7, identity)
├── events.py       # system-wide audit log (provenance + analytics)
└── apps/           # council, context app layer
```

## Primitive Overview

### spawn.db
**Agent registry with constitutional identity and task tracking.**
- Tracks agent instances, names, and constitutional hashes
- Enforces name uniqueness (one identity per name per workspace)
- Stores content-addressed constitutions (immutable, hash-verified)
- Task queue for agent-spawned work (pending → running → completed)
- Provenance: identity → constitution mapping + spawn counter

### bridge.db
**Async coordination channels with unread tracking.**
- Channels (named, archived, pinned)
- Messages (append-only, no deletes, priority-tagged)
- Bookmarks (per-agent-per-channel read position)
- Notes (agent reflections, don't appear in timeline)
- Pattern: agents send → readers catch up → consensus emerges

### memory.db
**Private agent context with topic sharding and soft deletes.**
- Memories (identity-scoped, topic-organized)
- Supersession chains (entry evolution tracking)
- Core flag (architectural/identity-defining entries surface first)
- Archive instead of delete (recovery possible)
- No cross-agent visibility

### knowledge.db
**Shared domain knowledge indexed by contributor + domain.**
- Knowledge entries (domain taxonomy emerges)
- Contributor provenance (agent_id tracked)
- Multi-agent writes (shared truth)
- Archive instead of delete
- Visible to all agents

### events.db
**Immutable append-only audit log.**
- Event source (spawn, bridge, memory, knowledge, identity)
- Agent ID (nullable for system events)
- Event type (semantic: agent.create, message_sent, etc.)
- Timestamp (UUID7 for chronological ordering)
- Chat context (optional bridge channel reference)
- Used for: provenance tracking, analytics, timeline reconstruction

## Data Flow Architecture

### Storage Hierarchy
```
Bridge (ephemeral messages)
    ↓
Memory (working context, captured from bridge)
    ↓
Knowledge (permanent discoveries, shared via domain)
    ↓
Events (immutable audit trail, all sources)
```

### Provenance Model
```
Identity invocation (CLI/API)
    ↓
spawn.ensure_agent(identity) → agent_id
    ↓
Operation runs (bridge.send, memory.add, etc.)
    ↓
events.emit(source, event_type, agent_id, data)
    ↓
events.db record (immutable, searchable)
    ↓
Later: events.query(agent_id=X) shows full audit trail
```

### Context Assembly (Wake)
1. `spawn_db.get_agent_id(identity)` → resolve to UUID
2. `memory.get_core_entries(identity)` → load architectural memories
3. `memory.get_recent_entries(identity, days=7)` → load working context
4. `bridge.fetch_channels(agent_id)` → unread counts
5. `knowledge.query_by_domain("*")` → relevant knowledge
6. Display summary: unread by channel, core memories, recent discoveries
7. Suggest priority action (channel with highest unread density)

### Coordination Flow (Bridge)
1. Agent A: `bridge.send(channel_id, agent_id, "message")`
   - Insert message (append-only)
   - Emit event: source=bridge, event_type=message_sent
2. Agent B: `bridge.recv(channel_id, agent_id)`
   - Fetch messages WHERE created_at > last_read
   - Update bookmark (last_read = now)
   - Emit event: source=bridge, event_type=message_read
3. Agent A (later): `bridge.notes(channel_id, agent_id, "reflection")`
   - Insert note (metadata, not in timeline)
   - Emit event: source=bridge, event_type=note_created