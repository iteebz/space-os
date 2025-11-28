# Bridge — Async Messaging & Coordination

Append-only message channels for agent coordination. Messages persist; bookmarks track read position per agent.

## What

- **Channels** — Named message topics, can be archived or pinned
- **Append-only** — Messages never deleted, full history preserved
- **Bookmarks** — Each agent tracks position in each channel (read state)
- **Handoffs** — Explicit responsibility transfer between agents
- **Delimiters** — @mentions spawn agents, !commands control execution

## CLI

```bash
bridge create <channel>
bridge send <channel> "message" --as <identity>
bridge recv <channel> --as <identity> [--ago 1h]
bridge channels
bridge archive <channel> [--restore]
bridge pin <channel>
bridge rename <channel> <new-name>
bridge topic <channel> "description"
bridge delete <channel>
bridge wait <channel> --as <identity>
bridge handoff <channel> <target> "summary" --as <identity>
bridge inbox [channel] --as <identity>
bridge close <handoff-id> --as <identity>
```

## Message Delimiters

Bridge recognizes delimiter patterns for coordination:

**Agent coordination:**
- `@identity` — Spawn agent with channel context

**Human control (slash commands):**
- `/stop <identity>` — Stop agent (make idle)
- `/compact <identity>` — Force agent session refresh

**Agent signals (bang commands):**
- `!compact <summary>` — Agent self-compaction (spawns successor)
- `!handoff @agent <summary>` — Transfer ownership to another agent

```bash
# Human control
bridge send research "/stop zealot-1" --as tyson            # stop agent
bridge send research "/compact zealot-1" --as tyson         # force fresh session

# Agent signals (agents post these)
bridge send research "!compact Completed X, next Y" --as zealot-1
bridge send research "!handoff @sentinel Review complete" --as zealot-1

# Wake agents
bridge send research "@zealot-1 continue work" --as tyson   # spawn or wake agent
```

## Handoffs

Explicit responsibility transfer between agents:

```bash
bridge handoff research @sentinel "review complete, needs verification" --as zealot
bridge inbox --as sentinel                                  # see pending handoffs
bridge close <handoff-id> --as sentinel                     # acknowledge receipt
```

Handoffs create accountability. The target agent sees pending work in their inbox until closed.

## Coordination Paradigm

Bridge enables topic-based multi-agent coordination without central orchestration.

1. **Send task** — `@zealot-1 implement auth and db`
2. **Agent reads context** — Zealot reads channel history + memory
3. **Agent executes** — Posts result to same channel
4. **Full continuity** — Future requests see complete causal chain

```
tyson: @zealot-1 implement auth and db in parallel
[zealot-1 reads channel + memory, executes, posts result]

tyson: @zealot-1 tests failing, fix token refresh
[zealot-1 reads entire history: original request, result, test failure]
[reconstructs context, fixes]
```

Single conversation thread. No context loss between invocations.

## Storage

- `channels` table — channel_id, name, topic, created_at, archived_at, pinned_at
- `messages` table — message_id, channel_id, agent_id, content, created_at
- `bookmarks` table — agent_id, channel_id, last_seen_id
- `handoffs` table — handoff_id, channel_id, source_id, target_id, summary, created_at, closed_at
