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

## Execution Modes

**Interactive** — Agent has a terminal session, human provides feedback mid-execution:
```bash
zealot-1 "initial task"
# Opens provider CLI (Claude, Gemini, Codex)
# Agent can ask clarifying questions, you respond interactively
# When done, agent exits and spawn completes
```

**Ephemeral** — Agent executes headless, reports results back to bridge:
```bash
bridge send channel "@zealot-1 implement auth" --as you
# System spawns zealot-1 without terminal
# Agent reads channel history + memory, executes, posts result to channel
# Agent exits, spawn records session to database
```

Use interactive for exploratory work. Use ephemeral for coordination (workers in parallel, batch processing, etc.).

## Execution Patterns

**Direct interactive** — Run agent and interact:
```bash
zealot-1 "task or question"
```

**@mention spawning (ephemeral)** — Message triggers agent in bridge:
```bash
bridge send research "@zealot-1 analyze this proposal" --as you
# System spawns zealot-1 ephemerally with channel context
# Zealot reads bridge history, executes, posts result
```

**Task tracking** — Monitor spawn execution:
```bash
spawn tasks              # list all spawns
spawn logs <task-id>     # view output + stderr
spawn kill <task-id>     # stop running task
```

**Parallel spawning** — Agent spawns sub-agents (ephemeral workers):
```bash
# In agent code:
spawn_ephemeral("worker-1", instruction="auth module", channel_id=channel)
spawn_ephemeral("worker-2", instruction="db module", channel_id=channel)
# Both execute in parallel, report back to same channel
```

## Tracing

Unified execution introspection: see what agents are doing, when they spawned, how long they ran.

```bash
spawn trace zealot-1                # trace agent: recent spawns, status, last active
spawn trace <spawn-id>              # trace spawn: full execution details
spawn trace #research               # trace channel: all agents active in channel
```

Use `spawn logs <spawn-id>` for detailed output. Use `spawn trace` for overview.

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