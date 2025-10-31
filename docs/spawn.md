# Spawn — Agent Registry & Execution

Agent identity, constitutional provenance, and task lifecycle.

## What

- **Registry** — Persistent agent identity with model, constitution, provider
- **Constitutional injection** — Identity-specific instructions loaded at spawn time
- **Task tracking** — Create, monitor, and manage agent execution tasks
- **Dynamic CLI** — Register agents, then invoke them as CLI commands: `zealot-1 "task"`

## CLI

```bash
spawn register <identity> <constitution> --model <model>
spawn list              # show all agents
spawn agents            # detailed agent info
spawn tasks             # list all tasks
spawn logs <task-id>    # view task details (input, output, stderr)
spawn kill <task-id>    # stop running task
spawn rename <old> <new>
spawn clone <identity> <new-identity>
spawn merge <source> <target>
spawn models            # show available LLM models
```

For full options: `spawn --help`

## Execution Patterns

**Direct** — Run agent by registered identity:
```bash
zealot-1 "task or question"
```

**@mention in bridge** — Message triggers agent:
```bash
bridge send channel "@zealot-1 analyze this" --as you
# System builds prompt from channel context, spawns agent, posts reply
```

**Task-based** — Create task, track execution:
```bash
spawn tasks
spawn logs <task-id>     # view output + stderr
spawn kill <task-id>     # stop running task
```

## Storage

- `agents` table — identity, model, constitution, provider, created_at, last_active_at
- `tasks` table — task_id, agent_id, channel_id, input, output, stderr, status, created_at
- `sessions` table — session_id, agent_id, spawn_number, started_at, ended_at

See [docs/schema.md](schema.md) for full schema.