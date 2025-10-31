# Memory — Private Working Context

Single-agent, topic-organized working memory. Editable, archivable; marked entries promoted to "core".

## What

- **Identity-scoped** — Private to each agent
- **Topic-sharded** — Organized by topic for focused retrieval
- **Editable** — Can be updated or corrected
- **Core flag** — Mark identity-defining entries for quick access
- **Supersession** — Entries can reference prior versions

## CLI

```bash
memory add --as <identity> --topic <topic> "content"
memory list --as <identity>                        # all memories
memory list --as <identity> --topic <topic>        # filtered by topic
memory search "query" --as <identity>
memory edit <memory-id> "new content"
memory archive <memory-id>                         # soft delete
memory core <memory-id>                            # mark as identity-defining
memory inspect <memory-id> --as <identity>         # view + related entries
```

For full options: `memory --help`

## Examples

```bash
# Add working note
memory add --as zealot-1 --topic tasks "completed X, next is Y"

# Mark as core (identity-defining)
memory core <memory-id>

# Search by topic
memory list --as zealot-1 --topic decisions

# Archive old entries
memory archive <memory-id>
```

## Storage

- `memories` table — memory_id, agent_id, topic, message, created_at, archived_at, core

See [docs/schema.md](schema.md) for full schema.
