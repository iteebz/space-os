# OPS: Work decomposition for agent swarms

Structured task lifecycle enabling map-reduce coordination. Decompose epics, parallelize work, aggregate results.

**Quick start:**
```
ops create "Build feature X"
ops create "Subtask 1" --parent <task-id>
ops claim <task-id> --as haiku-1
ops complete <task-id> "Done. See PR #123" --as haiku-1
ops reduce <parent-id> "Feature complete" --as sonnet-1
```

## Commands

```bash
ops create <description> [--parent <id>] [--channel <name>] [--assign <identity>]
ops list [--status <status>] [--assigned <identity>] [--parent <id>]
ops tree <task-id>              # show decomposition hierarchy
ops claim <task-id> --as <identity>
ops complete <task-id> <handover> --as <identity>
ops block <task-id> <reason>
ops reduce <task-id> <handover> --as <identity>
```

## Status Lifecycle

- `open` → task available for claiming
- `claimed` → agent assigned, work in progress
- `complete` → work done, handover provided
- `blocked` → cannot proceed, needs intervention

## Integration

**With Bridge:** Link tasks to channels via `--channel` for coordination
**With Memory:** Agents track task context in memory under topic
**With Wake:** Tasks assigned to agent shown in wake context (future)
**With Spawn:** Future auto-spawn agents for subtasks

## Example: Payment System

```bash
# Create epic
ops create "Payment system" --channel payments
# → task-abc123

# Decompose
ops create "Stripe SDK" --parent task-abc123
ops create "Webhooks" --parent task-abc123
ops create "Tests" --parent task-abc123

# Parallel execution
ops claim task-sub1 --as haiku-1
ops claim task-sub2 --as haiku-2
ops claim task-sub3 --as haiku-3

# Complete
ops complete task-sub1 "SDK integrated" --as haiku-1
ops complete task-sub2 "Webhooks verified" --as haiku-2
ops complete task-sub3 "Tests passing" --as haiku-3

# Reduce
ops reduce task-abc123 "Payment system deployed" --as sonnet-1
```

**Storage:** `.space/ops.db`
