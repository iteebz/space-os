"""Context search: provider session logs."""

from space.os import sessions


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search provider session logs directly (stateless, ephemeral discovery)."""
    return sessions.api.operations.search(query, identity, all_agents)
