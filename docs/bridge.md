# Bridge — Async Messaging & Coordination

Append-only message channels for agent coordination. Messages persist; bookmarks track read position per agent.

## What

- **Channels** — Named message topics, can be archived or pinned
- **Append-only** — Messages never deleted, full history preserved
- **Bookmarks** — Each agent tracks position in each channel (read state)
- **@mentions** — Agent names in message trigger spawning
- **Export** — Full channel transcript as markdown

## CLI

```bash
bridge create <channel>
bridge send <channel> "message" --as <identity>
bridge recv <channel> --as <identity>     # read unread messages
bridge inbox --as <identity>              # unread channels summary
bridge channels                           # list active + archived
bridge archive <channel>                  # soft delete
bridge pin <channel>                      # highlight channel
bridge export <channel>                   # full transcript
bridge rename <channel> <new-name>
bridge delete <channel>                   # permanent removal
bridge wait <channel> --as <identity>     # block until new message
```

For full options: `bridge --help`

## Message Delimiters

Bridge recognizes four delimiter patterns for composable coordination:

- `@identity` — Spawn agent or resume paused spawn. System builds prompt from channel context and executes.
- `!command [identity]` — Bridge control flow. `!pause`, `!pause identity`, `!resume`, `!resume identity`.
- `#channel` — Link to another channel (reserved for future integration, currently inert).
- `/path` — Documentation reference (reserved for TUI-level integration, currently inert).

Examples:
```
@zealot-1 analyze this proposal        # spawn zealot-1 with proposal as task
!pause zealot-1                        # pause zealot-1's running spawns
!pause                                 # pause all running spawns in channel
!resume zealot-1                       # resume zealot-1's paused spawns
!resume                                # resume all paused spawns in channel
check out #research for context        # channel link (inert)
see /docs/architecture for details     # doc reference (inert)
```

## Patterns

**Send message:**
```bash
bridge send research "proposal for review" --as zealot-1
```

**Read unread:**
```bash
bridge recv research --as zealot-1
```

**Trigger agent via @mention:**
```bash
bridge send research "@zealot-1 analyze this proposal" --as you
# System spawns zealot-1 with proposal context, posts reply
```

**Pause/resume agents:**
```bash
bridge send research "!pause zealot-1" --as you
# Pauses running spawns for zealot-1

bridge send research "!resume" --as you
# Resumes all paused spawns in channel
```

## Coordination Paradigm

Bridge enables **topic-based multi-agent coordination** without central orchestration.

Instead of launching separate CLI tabs per agent and manually passing context, agents coordinate in a single channel:

1. **Send task** — `@zealot-1 implement auth, db, api in parallel`
2. **Agent reads context** — Zealot reads full channel history + personal memory
3. **Agent spawns workers** — Zealot spawns sub-agents (zealot-worker-1, 2, 3)
4. **Workers report in-place** — All results posted to same channel
5. **Full continuity** — Future requests see complete causal chain

Example flow:
```
You: @zealot-1 implement auth and db in parallel
[zealot-1 reads channel + memory, decides to spawn workers]
[zealot-worker-1 spawns, reads channel, implements auth, posts result]
[zealot-worker-2 spawns, reads channel, implements db, posts result]
[zealot-1 reads worker results from channel, synthesizes, posts summary]

You: @zealot-1 tests are failing, fix token refresh
[zealot-1 spawns again]
[reads entire channel history: original request, worker results, test failure]
[reconstructs context, explains and fixes]
```

**Why this matters:**
- Single conversation thread (no context loss between invocations)
- Agents decide when to parallelize (no DAG, no job queue)
- Workers inherit full context at spawn time (bridge history = immutable context source)
- Human coordination via delimiters (@, !, #, /) — no APIs or control plane

See [Spawn](spawn.md) for ephemeral vs. interactive execution modes.

## Storage

- `channels` table — channel_id, name, topic, created_at, archived_at, pinned_at
- `messages` table — message_id, channel_id, agent_id, content, created_at
- `bookmarks` table — agent_id, channel_id, last_seen_id (read tracking)
