# Ops: Work Decomposition Primitive

**Status:** Design

**Problem:** Swarms need structured work decomposition, not just conversation. Bridge handles coordination. Memory handles context. Knowledge handles discoveries. Missing: **task lifecycle**.

---

## Core Question: Primitive or Protocol?

### Option A: Ops as separate primitive
- New `.space/ops.db`
- Task state independent of conversation
- Pros: Clean separation, structured queries
- Cons: Another system to integrate

### Option B: Ops as bridge protocol
- No new DB, special channel conventions (`task-*`)
- Bridge messages = status updates
- Bridge notes = handovers
- Pros: Reuse existing infrastructure
- Cons: Overloads bridge semantics

### Option C: Ops primitive that interweaves (CHOSEN)
- `.space/ops.db` for task state
- **Tags tasks with channel_id** for coordination
- **Tags tasks with topic** for memory integration
- Bridge, memory, knowledge already share topics/channels
- Tasks become **shared reference** across primitives

**Rationale:** Memory, knowledge, bridge already integrate via shared identifiers (topics, channels). Ops follows same pattern. Task = structured work unit that threads through existing coordination substrate.

---

## Design Principles

1. **Beautifully minimal** - one table, essential fields only
2. **Map-reducible** - parent_id enables hierarchical decomposition
3. **Parallelizable** - multiple agents claim independent subtasks
4. **Interoperable** - task_id referenced in bridge/memory/knowledge via tags

---

## Minimal Schema

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,           -- uuid7
    parent_id TEXT,                -- enables tree structure (map-reduce)
    description TEXT NOT NULL,     -- what needs doing
    assigned_to TEXT,              -- agent_id from spawn registry
    status TEXT DEFAULT 'open',    -- open, claimed, review, complete, blocked
    handover TEXT,                 -- deliverable/summary on completion
    channel_id TEXT,               -- bridge channel for coordination
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES tasks(id)
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_parent ON tasks(parent_id);
CREATE INDEX idx_tasks_channel ON tasks(channel_id);
```

**Fields:**
- `parent_id`: Map-reduce tree. Root tasks have NULL parent.
- `status`: Lifecycle - `open` → `claimed` → `review` → `complete` (or `blocked`)
- `handover`: Result artifact. For subtasks: individual work. For parent: integrated result.
- `channel_id`: Links to bridge channel for real-time coordination

---

## Workflow (Minimal MapReduce)

### Create & Decompose (Map)
```bash
# Create epic
ops create "Build payment system"
# → task-abc123 created

# Decompose into subtasks
ops create "Stripe integration" --parent task-abc123
ops create "Webhook handlers" --parent task-abc123
ops create "Test coverage" --parent task-abc123
# → 3 subtasks created with parent_id=task-abc123
```

### Execute (Parallel)
```bash
# Agents claim work
ops claim task-xyz --as haiku-1
# → status: open → claimed

# Agent works, marks in-progress (optional status)
# Uses bridge for questions, memory for context

# Agent completes
ops complete task-xyz --handover "Stripe integration done. PR #123 merged." --as haiku-1
# → status: claimed → complete
```

### Review & Reduce
```bash
# Check if subtasks done
ops tree task-abc123
# Shows: 3/3 complete

# Integration agent reduces
ops reduce task-abc123 --handover "Payment system live. All tests passing." --as sonnet-1
# → Marks parent complete, aggregates child handovers
```

---

## Integration Points

### With Bridge
- Each task optionally linked to channel via `channel_id`
- Agents coordinate blockers/questions in that channel
- Example: `ops create "task" --channel payments-dev`

### With Memory
- Agents add task context to memory under topic
- Example: `memory add --topic task-xyz "Implementation notes"`

### With Wake/Sleep
- `wake --as identity` shows assigned tasks in context
- Auto-includes: `ops list --assigned-to agent-id --status claimed`

### With Spawn
- Tasks assigned via agent_id from spawn registry
- Future: `ops create --spawn haiku:stripe` auto-spawns agent for task

---

## CLI Commands (Minimal Set)

```bash
ops create <description> [--parent <task-id>] [--channel <channel>]
ops list [--status <status>] [--assigned-to <identity>] [--parent <task-id>]
ops tree <task-id>              # show decomposition hierarchy
ops claim <task-id> --as <identity>
ops complete <task-id> --handover <text> --as <identity>
ops block <task-id> --reason <text>
ops reduce <task-id> --handover <text> --as <identity>
```

**Not included (keep minimal):**
- ~~Status transitions beyond open→claimed→complete~~
- ~~Complex assignment logic~~
- ~~Time tracking~~
- ~~Priority/labels~~
- ~~Auto-spawn~~ (future)

---

## Example: Payment System Epic

```bash
# Zealot-1 creates epic and decomposes
ops create "Payment system" --channel payments
# → task-001

ops create "Stripe SDK integration" --parent task-001
ops create "Webhook receiver endpoint" --parent task-001
ops create "Payment flow tests" --parent task-001
# → task-002, task-003, task-004

# Haiku agents claim subtasks
ops claim task-002 --as haiku-1
ops claim task-003 --as haiku-2
ops claim task-004 --as haiku-3

# Each works in parallel
# Haiku-1 completes first
ops complete task-002 --handover "Stripe SDK integrated. Config in .env.example" --as haiku-1

# Others complete
ops complete task-003 --handover "Webhook at /api/webhooks/stripe. Verified signatures." --as haiku-2
ops complete task-004 --handover "E2E tests pass. Coverage: 94%" --as haiku-3

# Sonnet integrates
ops reduce task-001 --handover "Payment system deployed. Docs: docs/payments.md" --as sonnet-1
```

---

## Open Questions

1. **Review status:** Do we need explicit `review` status before `complete`? Or trust agent + optional human review?
2. **Blocking:** Should `block` be status or separate table for blockers?
3. **Auto-assignment:** Future spawn integration - `ops decompose --auto-spawn haiku`?
4. **Handover format:** Free text or structured (markdown, JSON)?

---

## Implementation Checklist

- [ ] `space/ops/db.py` - schema, connection, migrations
- [ ] `space/ops/api/__init__.py` - CRUD operations
- [ ] `space/commands/ops.py` - CLI interface
- [ ] Integration with `wake` command (show assigned tasks)
- [ ] Tests: unit (db operations) + integration (full workflow)
- [ ] Update `README.md` to include ops primitive

---

## Success Criteria

**Reference grade = minimal + extensible + interoperable**

- ✅ One table, <10 fields
- ✅ Hierarchical via parent_id (enables map-reduce)
- ✅ Interweaves with bridge/memory/knowledge via channel_id/topics
- ✅ <200 LOC for core implementation
- ✅ Works with existing spawn/wake/sleep cycle
