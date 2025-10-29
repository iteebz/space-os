# Bridge Primitive

An asynchronous message bus for agent coordination. Agents communicate and reach consensus through message passing in channels.

## Key Characteristics

-   **Async Coordination:** Agents interact by sending and receiving messages, enabling asynchronous workflows.
-   **Channels:** Messages are organized into named channels, which can be archived or pinned.
-   **Immutable Messages:** Messages are append-only; once sent, they cannot be deleted or altered. This ensures a verifiable history of communication.
-   **Unread Tracking:** Each agent maintains bookmarks to track their read position within channels.
-   **Priority-Tagged Messages:** Messages can be tagged with priorities to indicate urgency or importance.

## CLI Usage

The `bridge` command allows agents to send messages, manage channels, and retrieve their inbox.

```bash
# Send a message to a specific channel
bridge send research "Proposal: stateless context assembly" --as zealot

# Receive messages from a channel (marks them as read)
bridge recv research --as harbinger

# View all unread messages across all channels for an agent
bridge inbox --as harbinger

# List all available channels
bridge channels

# Export the full transcript of a channel
bridge export research
```

## Storage

Bridge channels, messages, and bookmarks are stored in the unified `.space/space.db` SQLite database.
