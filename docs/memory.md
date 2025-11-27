# Memory — Private Working Context

Single-agent, topic-organized working memory. Editable, archivable; core entries marked as identity-defining.

## What

- **Identity-scoped** — Private to each agent
- **Topic-sharded** — Organized by topic for focused retrieval
- **Editable** — Can be updated or corrected
- **Core flag** — Mark identity-defining entries

## CLI

```bash
memory add "content" --topic <topic> --as <identity>
memory list --as <identity> [--topic X]
memory search "query" --as <identity>
memory edit <memory-id> "new content"
memory archive <memory-id> [--restore]
memory core <memory-id>
memory inspect <memory-id>
```

## Examples

```bash
memory add "completed auth, next is db" --topic tasks --as zealot
memory list --as zealot --topic decisions
memory core <memory-id>                         # mark as identity-defining
memory archive <memory-id>                      # soft delete
memory inspect <memory-id>                      # view with related entries
```

## Storage

- `memories` table — memory_id, agent_id, topic, message, created_at, archived_at, core
