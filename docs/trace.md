# Trace: Temporal audit primitive

**Status:** Spec (not implemented)

**Problem:** Can search content via `context`, but can't answer "what happened?" across time and primitives. No unified audit trail for debugging swarm behavior, understanding causality, or reconstructing decision paths.

---

## Core Question: Event Stream or Meta-Layer?

### Option A: Trace as primitive (new storage)
- New `.space/trace.db`
- All primitives emit events to trace
- Unified temporal log
- Pros: Single source of truth for "what happened"
- Cons: Another system, duplication risk

### Option B: Trace as meta-layer (like context)
- No storage, queries existing primitives
- Reconstructs timeline from:
  - events.db (wake/sleep)
  - bridge.db (messages, created_at)
  - ops.db (task lifecycle, completed_at)
  - memory.db (entries, created_at)
  - knowledge.db (discoveries, created_at)
- Pros: No duplication, queries existing data
- Cons: Each primitive needs temporal queryability

**Recommendation:** Start with **Option B** (meta-layer). If performance suffers or causality tracking needed, upgrade to Option A.

---

## Use Cases

### 1. Debug task failure
```bash
trace task-abc123

Timeline for task-abc123 (Build payment system):
2025-10-22 14:00:00 | ops       | created by zealot-1
2025-10-22 14:01:00 | ops       | decomposed into 3 subtasks
2025-10-22 14:05:00 | ops       | task-sub1 claimed by haiku-1
2025-10-22 14:10:00 | bridge    | haiku-1 posted to #payments: "Blocked on API key"
2025-10-22 14:12:00 | memory    | haiku-1 added "stripe config issue"
2025-10-22 14:15:00 | ops       | task-sub1 blocked (reason: need API key)
2025-10-22 14:20:00 | bridge    | zealot-1 posted to #payments: "API key in .env.example"
2025-10-22 14:25:00 | ops       | task-sub1 claimed by haiku-1 (retry)
2025-10-22 14:30:00 | ops       | task-sub1 completed
```

### 2. Agent activity audit
```bash
trace --agent zealot-1 --since "last wake"

Activity timeline for zealot-1:
2025-10-22 14:00:00 | spawn     | woke (session 42)
2025-10-22 14:00:02 | bridge    | read #payments (3 unreads)
2025-10-22 14:00:05 | memory    | loaded 12 entries (topic: payments)
2025-10-22 14:00:30 | ops       | created task-abc123
2025-10-22 14:01:00 | bridge    | sent message to #payments
2025-10-22 14:15:00 | knowledge | added domain=architecture
2025-10-22 14:20:00 | spawn     | sleep
```

### 3. Causality chain
```bash
trace --causality task-abc123

Causality chain for task-abc123:
[root] bridge message #payments:42 ("we need payments")
  └─> memory entry zealot-1:arch-notes ("design payment flow")
      └─> ops task-abc123 created
          ├─> ops task-sub1 (claimed by haiku-1)
          │   └─> bridge message #payments:43 ("blocked")
          │       └─> ops task-sub1 blocked
          ├─> ops task-sub2 (claimed by haiku-2)
          │   └─> ops task-sub2 completed
          └─> ops task-sub3 (claimed by haiku-3)
              └─> ops task-sub3 completed
```

---

## Minimal Schema (if primitive)

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,           -- uuid7 (time-sortable)
    timestamp INTEGER NOT NULL,
    primitive TEXT NOT NULL,       -- spawn, bridge, ops, memory, knowledge
    event_type TEXT NOT NULL,      -- wake, send, claim, add, complete, etc
    agent_id TEXT,                 -- who triggered
    target_id TEXT,                -- what was affected (task_id, channel_id, etc)
    parent_event_id TEXT,          -- causality chain
    metadata TEXT                  -- JSON payload for primitive-specific data
);

CREATE INDEX idx_trace_agent ON events(agent_id, timestamp);
CREATE INDEX idx_trace_target ON events(target_id, timestamp);
CREATE INDEX idx_trace_causality ON events(parent_event_id);
CREATE INDEX idx_trace_time ON events(timestamp DESC);
CREATE INDEX idx_trace_primitive ON events(primitive, timestamp);
```

**Design notes:**
- uuid7 IDs are time-sortable (no separate sort key needed)
- parent_event_id enables causality graphs
- metadata stores primitive-specific context (JSON blob)
- Lightweight: ~10 fields, mostly indexed

---

## Integration Points

### Events to emit

**spawn:**
- wake(agent_id, session_id)
- sleep(agent_id, session_id)
- spawn(agent_id, caused_by=event_id)

**bridge:**
- send(agent_id, channel_id, message_id)
- recv(agent_id, channel_id)
- note(agent_id, channel_id)

**ops:**
- create_task(agent_id, task_id, parent_task_id)
- claim_task(agent_id, task_id)
- complete_task(agent_id, task_id)
- block_task(agent_id, task_id)
- reduce_task(agent_id, task_id)

**memory:**
- add_entry(agent_id, memory_id, topic)
- archive_entry(agent_id, memory_id)

**knowledge:**
- add_discovery(agent_id, knowledge_id, domain)
- archive_discovery(agent_id, knowledge_id)

### Causality tracking

When event A causes event B, store parent_event_id:
```python
# ops task decomposition spawns subtask
parent_event = trace.emit("ops", "create_task", task_id=parent_id)
sub_event = trace.emit("ops", "create_task", task_id=child_id,
                       parent_event_id=parent_event)
```

---

## Commands (minimal set)

```bash
trace <target_id>                    # timeline for task/agent/channel
trace --agent <identity>             # agent activity
trace --task <task_id>               # task lifecycle
trace --channel <channel>            # bridge conversation
trace --since <time>                 # recent events (e.g., "2h ago", "last wake")
trace --causality <event_id>         # show cause → effect tree
trace --primitive <primitive>        # events from specific primitive
```

**Not included (keep minimal):**
- ~~Filtering by event_type~~
- ~~Aggregation/analytics~~ (use space stats)
- ~~Real-time streaming~~ (poll via --since)

---

## Implementation Approaches

### Approach 1: Meta-layer (like context)
- No new storage
- Queries existing primitives' temporal data
- Merges timelines on-demand
- **Pros:** No duplication, simple
- **Cons:** Slower queries, no causality tracking

### Approach 2: Event emission (primitive)
- Each primitive emits to trace.db
- Unified storage
- **Pros:** Fast queries, causality chains
- **Cons:** Requires all primitives to integrate

### Approach 3: Hybrid
- Start as meta-layer (v1)
- Add event emission when causality needed (v2)
- **Pros:** Incremental complexity
- **Cons:** Two modes to maintain

**Recommendation:** Approach 3 (hybrid). Ship meta-layer first.

---

## Open Questions

1. **Performance:** How slow is querying 6 primitives vs dedicated trace.db?
2. **Causality:** Can we infer causality without explicit parent_event_id? (e.g., same session, close timestamps)
3. **Retention:** Should trace events expire? (e.g., delete after 30 days)
4. **Privacy:** Should agents be able to hide events from trace? (constitutional preference)
5. **Format:** Human-readable timeline vs JSON for machine parsing?

---

## Success Criteria

**Reference grade = minimal + useful + extensible**

- ✅ Answer "what happened to X?" in single command
- ✅ Works across all primitives (unified view)
- ✅ Reconstructs timeline without new storage (v1)
- ✅ Extensible to causality tracking (v2)
- ✅ <300 LOC initial implementation (meta-layer)

---

## Example Workflow

**Scenario:** Debug why payment system task failed

```bash
# Start with task
trace task-abc123

# See it was blocked on subtask
trace task-sub1

# See agent posted to bridge
trace --agent haiku-1 --since "when task-sub1 created"

# Check bridge conversation
trace --channel payments

# Find root cause: API key missing
# Fix and verify

trace task-abc123
# Now shows: complete
```

---

## Relationship to Existing Primitives

- **context** → content search ("what exists?")
- **trace** → temporal audit ("what happened?")
- **events** → system metrics (wake/sleep counts)
- **stats** → aggregated analytics (agent activity)

Trace fills the gap: **temporal causality for debugging and provenance**.

---

## Implementation Checklist (if approved)

- [ ] Decide: meta-layer or primitive?
- [ ] `space/trace/db.py` (if primitive) OR `space/trace/query.py` (if meta-layer)
- [ ] `space/commands/trace.py` - CLI interface
- [ ] Add emit hooks to primitives (if primitive approach)
- [ ] Tests: timeline reconstruction, causality chains
- [ ] Update README.md to include trace

---

## Notes

- This is the "kernel log" for space-os
- Essential for production swarm debugging
- Complements context (content) with temporal (events)
- Start minimal (meta-layer), grow as needed (event emission)
