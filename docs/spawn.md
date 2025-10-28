# Spawn: Constitutional Agent Launcher

Spawn is a **pure primitive** for launching constitutional agents. It owns identity registry and constitutional injection—nothing more.

## Architecture

### Spawn's Responsibility
- Identity registry (agents table)
- Constitutional storage (content-addressable by hash)
- Agent launching (interactive or task mode)
- Context injection via `--context` flag

### What Spawn Does NOT Own
- **Task lifecycle tracking** (belongs to Bridge)
- **Channel coordination** (belongs to Bridge)
- **Context building** (Bridge's job)

## Core Concepts

### Identity Registry
```python
from space.os import spawn

# Register a new agent
agent_id = spawn.register_agent("hailot", "hailot.md", "claude-haiku-4-5")

# Get an existing agent
agent = spawn.get_agent("hailot")
constitution = agent.constitution
```

Agents table stores: `(id, name, self_description, created_at, archived_at)`

### Constitutional Injection
Constitutions are stored content-addressable (by hash). On launch, identity is injected:

```
# HAILOT CONSTITUTION
Self: You are hailot. Your model is claude-haiku-4-5.

[base constitution content]

run `space` for orientation
```

### Agent Interface
All agents (Claude, Gemini, Codex) follow the same contract:

```python
class Agent:
    def __init__(self, identity: str):
        self.identity = identity

    def run(self, prompt: str | None) -> str:
        # prompt=None → interactive (blocking stdin)
        # prompt=str → one-shot task (return output)
```

## Usage

### Interactive Mode
```bash
spawn hailot
```
- Runs wake sequence (loads memories, channel state)
- Blocks on stdin
- Same interface across Claude, Gemini, Codex

### Task Mode
```bash
spawn hailot "task description"
```
- Returns output immediately (no stdin)
- Accepts `--context <prefix>` for pre-built context
- Context is prepended to task: `context + "\n\n" + task`

### With Channel Context
```bash
spawn hailot "task" --context "$(bridge export channel-name)"
```
- Bridge builds and exports full channel context
- Spawn receives context as pre-built prefix
- Agent processes: constitution + context + task

### Direct Task (One-Shot)
```bash
spawn hailot "task" --as <base-agent> --model <model>
```
- Spawns specific agent (claude, gemini, codex)
- Returns output, exits

## Design Principles

1. **Pure Primitive**: Spawn is minimal—identity + constitution + launch
2. **No Lifecycle Tracking**: Tasks are Bridge's responsibility
3. **No Channel Knowledge**: Spawn doesn't know about channels
4. **Unified Agent Interface**: Claude/Gemini/Codex are interchangeable
5. **Context Injection by Caller**: Bridge builds context, passes via `--context`

## Task Execution Pattern

Task execution is a **pattern using spawn**, not part of spawn itself:

```
Bridge receives: @hailot "task"
└─ Bridge:
   ├─ Export full channel context
   ├─ Build prompt: constitution + wake + context + task
   ├─ Create task record (status=pending) in space.db
   ├─ Call: spawn hailot prompt --context <pre-built>
   ├─ Capture output
   ├─ Update task record (status=completed|failed, output)
   └─ Send result to channel
```

Spawn's job: return agent output. Bridge's job: manage task lifecycle.

## Debugging

### Check Agent Identity
```bash
spawn list
spawn get <identity>
```

### Show Constitution
```bash
spawn <identity>
```
(interactive mode—exit with Ctrl-C)

### Run Task (Show Output)
```bash
spawn <identity> "debug task" 2>&1
```

## Testing

Tests verify:
- Spawn registry has NO tasks table
- Bridge owns tasks table (channel_id, identity, status, input, output, started_at, completed_at)
- `--context` flag works
- Full export for bridge spawns (no 10-msg limit)
- Unified agent interface across all backends

See `tests/unit/spawn/test_spawn_unification.py` for reference-grade TDD validation.

## Related

- [Bridge](bridge.md): Task coordination & lifecycle
- [Agents](agents.md): Constitutional intelligence layer
- [Constitutions](../space/os/constitutions): Identity definitions
