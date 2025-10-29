# Memory Primitive

Private working context for agents, topic-sharded and identity-scoped. Memory entries are designed to capture an agent's ongoing thoughts, observations, and tasks.

## Key Characteristics

-   **Identity-Scoped:** Each memory entry belongs to a specific agent.
-   **Topic-Sharded:** Entries are organized by topics, allowing for focused retrieval.
-   **Archive-Write Encouraged, Edit Allowed:** While new entries are preferred for maintaining an immutable history, existing entries can be edited to correct mistakes or refine information. Archiving is used for soft deletion.
-   **Supersession Chains:** Entries can be replaced by newer versions, creating a historical chain of evolution.
-   **Core Flag:** Important, architectural, or identity-defining entries can be marked as "core" for quick access.
-   **No Cross-Agent Visibility:** Memories are private to the agent that created them.

## CLI Usage

The `memory` command provides both general operations and convenient shortcuts for canonical namespaces.

### Namespace Shortcuts

Use dedicated commands for canonical memory namespaces: `journal`, `notes`, `tasks`, `beliefs`. These provide quick ways to add and list entries for common use cases.

```bash
# Add a journal entry
memory journal "Wound down session, next steps: review PR #123" --as zealot

# Add a quick note
memory notes "Observed high CPU usage during build process" --as harbinger

# Add a task to follow up on
memory tasks "Follow up with team on integration test failures" --as sentinel

# Add a core belief statement
memory beliefs "Prioritize clarity and simplicity in all code" --as scribe

# List journal entries for 'zealot'
memory journal --as zealot

# List notes for 'harbinger'
memory notes --as harbinger
```

### General Memory Commands

For other operations, custom topics, or managing entries by UUID, use the general `memory` commands.

```bash
# Add a memory entry with a custom topic
memory add --as zealot --topic research "Initial findings on neural network architecture"

# Edit an existing memory entry by its UUID
memory edit <uuid> "Updated message content after review"

# Archive a memory entry (soft delete)
memory archive <uuid>

# Mark an entry as core memory (or unmark)
memory core <uuid>
memory core <uuid> --unmark

# Replace an old entry with a new one, creating a supersession chain
memory replace <old-uuid> "New, refined content for the superseded entry"

# Search memory entries by keyword
memory search "neural network" --as zealot

# Inspect an entry and find related nodes
memory inspect <uuid> --as zealot
```

## Storage

Memory entries are stored in the unified `.space/space.db` SQLite database.
