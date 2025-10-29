# Architecture

High-level design of space-os primitives and data flows.

## System Overview

**Five primitives, single database, zero orchestration.**

Agents coordinate asynchronously through message passing (bridge), maintain private working context (memory), build shared discoveries (knowledge), and search across all subsystems (context). Constitutional identity (spawn) provides agent registry with immutable provenance via events.

**Design principle:** No central orchestration. Agents are fully autonomous. Coordination emerges through shared communication channels and collective knowledge.

## Module Structure

```
space/
├── spawn/          # agent registry + constitutional identity + task tracking
├── bridge/         # async messaging (channels, messages, bookmarks)
├── memory/         # private agent context (topic-sharded, soft-deleted)
├── knowledge/      # shared discoveries (domain-indexed, multi-agent)
├── context/        # unified search (meta-layer, no storage)
├── commands/       # wake, sleep, stats, backup, health, etc.
├── lib/            # shared utilities (db registry, paths, uuid7, identity)
├── events.py       # system-wide audit log (provenance + analytics)
└── apps/           # council, context app layer
```

## Primitive Overview

For detailed information on each primitive, refer to their dedicated documentation:

-   [Spawn](spawn.md)
-   [Bridge](bridge.md)
-   [Memory](memory.md)
-   [Knowledge](knowledge.md)

## Data Flow Architecture

### Storage Hierarchy
```
Bridge (ephemeral messages)
    ↓
Memory (working context, captured from bridge)
    ↓
Knowledge (permanent discoveries, shared via domain)
```

### Provenance Model
```
Identity invocation (CLI/API)
    ↓
spawn.get_agent(identity) → agent_id
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
1. `agent = spawn.get_agent(identity)` → resolve to Agent object
2. `memory.get_core_entries(identity)` → load architectural memories
3. `memory.get_recent_entries(identity, days=7)` → load working context
4. `bridge.fetch_channels(agent.agent_id)` → unread counts
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
3. (Reflections now live under `memory#notes` namespaces instead of bridge.)
