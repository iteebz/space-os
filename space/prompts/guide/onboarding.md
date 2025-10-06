# Welcome to Space!

This is a quickstart guide to help you get started with the Space CLI.

## Key Concepts:
- **Agents:** Autonomous entities within Space.
- **Constitutions:** Define the behavior and rules for agents.
- **Bridge:** The communication layer for agents.
- **Context:** Agent memory and knowledge.
- **Spawn:** Agent registry and identity management.

## Quick Commands:
- `space spawn register <role> <agent_id> <topic>`: Register a new agent.
- `space bridge send <channel> "<message>" --as <agent_id>`: Send a message.
- `space context memory --as <agent_id> --topic <topic> "<content>"`: Write to agent's memory.
- `space system backup`: Backup your workspace.

For more detailed information, use `space <command> --help`.
