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
spawn agents            # list all agents (registered and orphaned)
spawn models            # show available LLM models
spawn inspect <identity>
spawn rename <old> <new>
spawn clone <identity> <new-identity>
spawn update <identity> [--constitution X] [--model Y] [--role Z]
spawn merge <source> <target>
spawn tasks             # list all spawns (filter by status/identity)
spawn logs <spawn-id>   # view spawn details
spawn kill <spawn-id>   # stop running spawn
spawn trace <identity|spawn-id|channel>  # trace execution
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

**Agents:**
- `agents` table — identity, model, constitution, provider, created_at, last_active_at, archived_at

**Spawns (execution instances):**
- `spawns` table — spawn_id, agent_id, session_id (nullable), channel_id, constitution_hash, is_task, status, pid, created_at, ended_at
- Status: pending, running, paused, completed, failed, timeout
- `is_task`: True for bridge mentions / headless, False for interactive terminal spawns
- `session_id`: Links to provider session (Claude/Gemini/Codex) — optional for interactive spawns, required for task spawns

**Sessions (provider-native):**
- `sessions` table — session_id, provider, model, message_count, input_tokens, output_tokens, tool_count, source_path, source_mtime, first_message_at, last_message_at
- Provider: claude, gemini, or codex
- One session per agent execution (spawns link to sessions)

See [sessions.md](sessions.md) for details.