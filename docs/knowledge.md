# Knowledge — Shared Discoveries

Multi-agent, domain-indexed shared truth. Immutable once written; archive and add new if updating.

## What

- **Shared visibility** — All agents can read, multiple agents can write
- **Domain-indexed** — Organized by domain paths (e.g., `architecture/caching/redis`)
- **Immutable** — Write-once; archive old, add new to update
- **Contributor tracking** — Records agent who added entry

## CLI

```bash
knowledge add <domain> "content" --as <identity>
knowledge list
knowledge query --domain <domain>
knowledge tree
knowledge read <knowledge-id>
knowledge archive <knowledge-id> [--restore]
```

## Examples

```bash
knowledge add architecture/auth "JWT refresh uses sliding window" --as zealot
knowledge query --domain architecture
knowledge tree                                  # domain hierarchy
knowledge archive <knowledge-id>                # soft delete
```

## Storage

- `knowledge` table — knowledge_id, domain, agent_id, content, created_at, archived_at
