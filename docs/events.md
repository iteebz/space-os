# Events: Provenance & Audit Trail

System-wide append-only event log for tracking agent actions, coordination, and system state changes.

## Overview

Events enable:
- **Provenance tracking** — who did what and when
- **Audit trail** — immutable record for debugging
- **Identity verification** — link invocations to agents via spawn registry
- **Analytics** — wake/sleep cycles, session counts, etc.

All events are **immutable** (append-only, never updated/deleted).

## Event Schema

```sql
events (
  event_id TEXT PRIMARY KEY,       -- UUID7 (sortable)
  source TEXT NOT NULL,            -- subsystem origin: spawn | bridge | memory | knowledge | identity
  agent_id TEXT,                   -- FK to spawn.agents.agent_id (nullable for system events)
  event_type TEXT NOT NULL,        -- semantic type: agent.create | message_sent | session_start | ...
  data TEXT,                       -- free-form payload (event-specific)
  timestamp INTEGER NOT NULL,      -- unix epoch seconds (for sorting)
  chat_id TEXT                     -- optional context: bridge channel_id
)
```

## Event Types by Source

### spawn — Identity registry events

| Event Type | Data | Agent | Notes |
|-----------|------|-------|-------|
| `agent.create` | agent name | agent_id | New agent registered |
| `agent.archive` | agent name | agent_id | Agent archived |
| `agent.restore` | agent name | agent_id | Agent restored from archive |
| `task.create` | task input | agent_id | Task spawned |
| `task.complete` | task output | agent_id | Task finished |
| `task.fail` | error message | agent_id | Task failed |

### bridge — Coordination events

| Event Type | Data | Agent | Notes |
|-----------|------|-------|-------|
| `message_sent` | channel:message_id | agent_id | Message posted to channel |
| `message_read` | channel:last_seen_id | agent_id | Bookmark updated (message read) |
| `note_created` | channel:note_id | agent_id | Reflection/annotation added |
| `channel_created` | channel name | null | New channel created (system) |
| `channel_archived` | channel name | null | Channel archived (system) |

### memory — Personal context events

| Event Type | Data | Agent | Notes |
|-----------|------|-------|-------|
| `note_add` | topic:content_preview | agent_id | Memory entry created |
| `note_edit` | memory_id | agent_id | Memory entry updated |
| `note_delete` | memory_id | agent_id | Memory entry deleted |
| `note_archive` | memory_id | agent_id | Memory archived |
| `note_restore` | memory_id | agent_id | Memory restored |
| `note_core` | memory_id→true/false | agent_id | Core flag toggled |
| `note_replace` | old_ids→new_id | agent_id | Entry superseded |

### knowledge — Shared knowledge events

| Event Type | Data | Agent | Notes |
|-----------|------|-------|-------|
| `entry.write` | domain:content_preview | agent_id | Knowledge artifact added |
| `entry.archive` | knowledge_id | agent_id | Knowledge archived |
| `entry.restore` | knowledge_id | agent_id | Knowledge restored |

### identity — Provenance tracking

| Event Type | Data | Agent | Notes |
|-----------|------|-------|-------|
| any command | command name | agent_id | Track identity invocation |

## Usage Patterns

### Query events by agent

```python
from space.os import events

# Get all events for an agent
agent_events = events.query(agent_id="zealot-1-uuid")

# Get events from a subsystem
bridge_events = events.query(source="bridge")

# Get last 20 events
recent = events.query(limit=20)
```

### Emit an event

```python
from space.os import events
from space.os.spawn import db as spawn_db

agent_id = spawn_db.ensure_agent("zealot-1")
events.emit(
    source="bridge",
    event_type="message_sent",
    agent_id=agent_id,
    data="research:msg-abc123"
)
```

### Session tracking

```python
# Count sessions (wake cycles) for an agent
session_count = events.get_session_count(agent_id)

# Get last sleep time
last_sleep = events.get_last_sleep_time(agent_id)

# Count wakes since last sleep
wakes_in_session = events.get_wakes_since_last_sleep(agent_id)
```

## Provenance Model

**Problem:** How do we know who did what?

**Solution:** Events link agents (via spawn registry) to actions.

```
identity invocation (CLI)
    ↓
events.identify(identity, command)
    ↓
spawn_db.ensure_agent(identity)  ← resolves name → agent_id
    ↓
events.emit(source, event_type, agent_id, data)
    ↓
events.db record (immutable)
```

### Example: Message send with provenance

```bash
bridge send research "proposal" --as zealot-1
```

1. CLI resolves `zealot-1` to agent_id via `spawn_db.get_agent_id()`
2. Bridge inserts message with `agent_id`
3. Event emitted: `events.emit("bridge", "message_sent", agent_id, "research:msg-id")`
4. Event stored immutably in events.db
5. Audit trail: `events.query(agent_id=zealot_id)` shows all actions by zealot-1

### Sender recovery

No explicit sender column in bridge.messages — resolve via:

```python
from space.os.spawn import db as spawn_db

message = bridge.db.get_all_messages(channel_id)[0]
sender_name = spawn_db.get_agent_name(message.agent_id)  # lookup from registry
```

## Analytics

### Wake/sleep cycles

```python
from space.os import events

wakes = events.get_wake_count(agent_id)
sleeps = events.get_sleep_count(agent_id)
sessions = events.get_session_count(agent_id)
```

### Message activity

```python
from space.os import events

# Get all message_sent events for an agent
sent_events = events.query(agent_id=agent_id, source="bridge")
message_count = len(sent_events)
last_active = sent_events[0].timestamp if sent_events else None
```

## Design Principles

**Immutable.** Events are never updated or deleted. If an event is wrong, emit a correction event.

**Append-only.** All events are additions to the log. Order is preserved by UUID7 (sortable by timestamp).

**Decoupled.** Events don't require the emitter to succeed. If `events.emit()` fails, the main operation succeeded but audit trail is incomplete (should log separately).

**Optional context.** Fields like `agent_id` and `chat_id` are nullable — system events may not have an agent.

**Free-form data.** The `data` field is event-specific. No rigid schema. Document your event_type → data mapping.

## Migration from session_id

Prior to schema alignment:
- Column was named `session_id` (semantic mismatch)
- Migration added column dynamically
- Renamed to `chat_id` (semantically correct: bridge channel context)

Existing databases:
- Migration `_migrate_add_chat_id` automatically renames column
- No manual intervention needed

---

See `space/os/events.py` for implementation and query API.
