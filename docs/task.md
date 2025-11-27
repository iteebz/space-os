# Task — Shared Work Ledger

Project-scoped task coordination. Humans post work, agents claim and complete. Prevents duplication at scale.

## What

- **Project-scoped** — Organize by epic or domain
- **Agent-claimable** — Create unassigned, agents claim with `start`
- **Status-tracked** — open, in_progress, done

## CLI

```bash
task add "description" [--project X] [--as identity]
task list [--project X] [--as identity] [--done] [--all]
task start <task-id> --as <identity> [-r to unclaim]
task done <task-id> --as <identity>
```

## Examples

```bash
task add "implement auth module" --project claude-6
task add "review PR #47" --as sentinel --project claude-6
task list --project claude-6
task start <task-id> --as zealot              # claim
task start <task-id> --as zealot -r           # unclaim
task done <task-id> --as zealot               # complete
task list --done --project claude-6           # what shipped
```

## Storage

- `tasks` table — task_id, creator_id, agent_id, content, project, status, created_at, started_at, completed_at
