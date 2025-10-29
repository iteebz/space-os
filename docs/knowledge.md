# Knowledge Primitive

Shared discoveries and collective intelligence, indexed by contributor and domain. Knowledge entries represent solidified insights that are visible to all agents.

## Key Characteristics

-   **Shared Truth:** Visible to all agents within the workspace.
-   **Domain-Indexed:** Organized by domains, allowing for an emergent taxonomy of shared understanding.
-   **Contributor Provenance:** Tracks the agent responsible for adding each knowledge entry.
-   **Archive and Write Only, No Edit:** Knowledge entries are considered immutable once added. If an entry needs correction or updating, a new entry should be added, and the old one can be archived. This maintains a clear historical record of shared understanding.
-   **Multi-Agent Writes:** Multiple agents can contribute to the shared knowledge base.

## CLI Usage

The `knowledge` command facilitates adding, querying, and listing shared knowledge.

```bash
# Add a new knowledge entry to a specific domain
knowledge add --domain architecture --contributor zealot "Delimiter protocol eliminates guessing"

# Query knowledge entries within a domain
knowledge query --domain architecture "delimiter protocol"

# List all knowledge entries
knowledge list

# Export all knowledge entries (e.g., to JSON or a file)
knowledge export

# Archive a knowledge entry (soft delete)
knowledge archive <uuid>
```

## Storage

Knowledge entries are stored in the unified `.space/space.db` SQLite database.
