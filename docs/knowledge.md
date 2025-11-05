# Knowledge — Shared Discoveries

Multi-agent, domain-indexed shared truth. Immutable once written; archive and add new if updating.

## What

- **Shared visibility** — All agents can read, multiple agents can write
- **Domain-indexed** — Organized by domain paths for emergent taxonomy
- **Immutable** — Write-once; new entries for updates, archive old
- **Contributor tracking** — Records agent who added entry
- **Confidence scores** — Optional confidence metric

## CLI

```bash
knowledge add --domain <domain> --as <identity> "content"
knowledge list                                           # all entries
knowledge query --domain <domain>                        # entries in domain
knowledge tree                                           # domain hierarchy
knowledge inspect <knowledge-id>
knowledge archive <knowledge-id>                         # soft delete
```

For full options: `knowledge --help`

## Examples

```bash
# Add shared discovery
knowledge add --domain architecture --as zealot-1 "Protocol eliminates ambiguity"

# Query by domain
knowledge query --domain architecture

# View domain tree
knowledge tree

# Archive outdated entry
knowledge archive <knowledge-id>
```

## Storage

- `knowledge` table — knowledge_id, domain, agent_id, content, created_at, archived_at
