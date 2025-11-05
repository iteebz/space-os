# Task — Shared Planning Surface

Coordination primitive for explicit work assignment and agent self-organization. Complementary to bridge's conversational coordination.

Humans post work → agents read and claim → humans see status. Prevents duplication, enables 1:100 swarm operations.

## What

- **Project-scoped** — Organize by epic or domain
- **Agent-optional** — Create unassigned (backlog) or pre-assigned
- **Status-tracked** — open, in_progress, done
- **Timestamped** — created_at, started_at, completed_at

## CLI

```bash
# Create task (unassigned backlog)
task add "Research activation transfer" --project space-os
task add "Implement spawn.register UUID validation" --project space-os

# Create task (pre-assigned)
task add "Review PR #47" --as sentinel --project claude-6

# List tasks
task list                           # all open tasks, all projects
task list --project space-os        # open in space-os
task list --as zealot               # zealot's open tasks
task list --as zealot --project space-os  # zealot's in space-os
task list --done                    # completed tasks, all time
task list --done --project claude-6 # completed in claude-6

# Claim and progress
task start <id> --as zealot         # mark in_progress
task start <id> --as zealot -r      # unclaim (back to open)
task done <id> --as zealot          # mark complete

# Info
task list --help
```

## Examples

```bash
# Create backlog
task add "Design auth" --project claude-6
task add "Implement auth" --project claude-6

# Agents claim
task start <id> --as zealot
task list --project claude-6
→ [a3f9] Design auth @zealot (in_progress)
→ [b8e2] Implement auth (open)

# Agent finishes
task done <id> --as zealot

# What shipped?
task list --done --project claude-6
→ [a3f9] Design auth @zealot [2025-11-05 14:32]
```

## Storage

`tasks` table — task_id, creator_id, agent_id (nullable), content, project, status, created_at, started_at, completed_at
