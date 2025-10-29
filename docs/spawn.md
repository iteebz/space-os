# Spawn Primitive

Constitutional identity registry for agents. Spawn manages agent lifecycle, constitutional provenance, and provides the human interface for interacting with agents.

## Key Characteristics

-   **Constitutional Identity:** Registers agents with unique identities and links them to immutable, content-addressed constitutions.
-   **Agent Lifecycle Management:** Tracks agent instances, their roles, and associated models.
-   **Human Interface:** Provides commands for registering, listing, and managing agents.
-   **Provenance:** Ensures immutable provenance by mapping identities to constitutional hashes and tracking spawn counts.
-   **Task Tracking:** Can be used for tracking tasks associated with agents.

## CLI Usage

The `spawn` command is used to register new agents, list existing ones, and manage their state.

```bash
# Register a new agent with a specific role, identity, channel, and model
spawn register zealot zealot-1 research --model claude-sonnet-4

# List all registered agents
spawn list

# List archived agents
spawn list --archived

# Archive an agent (soft delete)
spawn archive <identity>

# Restore an archived agent
spawn restore <identity>
```

## Storage

Agent registrations, constitutions, and session data are stored in the unified `.space/space.db` SQLite database.