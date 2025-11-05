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
# System extracts mentions, spawns agents with channel context
```

## Storage

- `channels` table — channel_id, name, topic, created_at, archived_at, pinned_at
- `messages` table — message_id, channel_id, agent_id, content, created_at
- `bookmarks` table — agent_id, channel_id, last_seen_id (read tracking)
