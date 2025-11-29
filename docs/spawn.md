# Spawn — Agent Registry & Execution

Agent identity, constitutional provenance, and spawn lifecycle.

## What

- **Registry** — Persistent agent identity with model, constitution, role
- **Constitutional injection** — Identity-specific instructions loaded at spawn time from `canon/constitutions/`
- **Spawn tracking** — Monitor running agents, view logs, stop execution
- **Tracing** — Unified execution introspection across agents, sessions, channels

## CLI

```bash
spawn register <identity> [--model X] [--constitution Y] [--role Z]
spawn agents                    # list registered and orphaned agents
spawn models                    # show available LLM models
spawn inspect <identity>        # view agent details and constitution
spawn rename <old> <new>
spawn clone <identity> <new>
spawn update <identity> [--constitution X] [--model Y] [--role Z]
spawn merge <source> <target>
spawn list [--status X] [--identity Y] [--all]
spawn logs <spawn-id> [--tail N] [--follow]
spawn stop <spawn-id>
spawn trace <query>             # agent:X, session:X, or channel:X
```

## Human Identity

Register yourself as a human identity (no model):

```bash
spawn register tyson --role human
```

Agents with no model are treated as human identities. The web frontend and API use this to identify the human coordinator.

## Execution

Agents spawn via @mention in bridge channels:

```bash
bridge send research "@zealot-1 analyze this proposal" --as tyson
```

System builds prompt from channel context + constitution, spawns agent headless, posts result to channel.

## Spawn Tracking

```bash
spawn list                      # pending and running spawns
spawn list --all                # include completed/failed/timeout
spawn list --identity zealot    # filter by agent
spawn logs <spawn-id>           # spawn details + session output
spawn logs <spawn-id> --tail 50 # last 50 lines
spawn logs <spawn-id> --follow  # tail active session
spawn stop <spawn-id>           # terminate running spawn
```

## Tracing

Unified execution introspection. Query by agent, session, or channel:

```bash
spawn trace agent:zealot        # agent's recent spawns
spawn trace session:7a6a07de    # session context and messages
spawn trace channel:research    # all agents active in channel
```

Implicit syntax supported (auto-infers type): `spawn trace zealot`

## Storage

**Agents:**
- `agents` table — agent_id, identity, model, constitution, role, created_at, last_active_at, archived_at

**Spawns:**
- `spawns` table — spawn_id, agent_id, session_id, channel_id, constitution_hash, status, pid, created_at, ended_at
- Status: pending, running, paused, completed, failed, timeout
- `session_id`: Links to provider session (Claude/Gemini/Codex)

**Constitutions:**
- Stored in `canon/constitutions/{constitution}.md`
- Loaded and injected at spawn time