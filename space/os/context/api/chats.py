"""Context search: provider chat logs."""

from space.os import chats


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search provider chat logs directly (stateless, ephemeral discovery)."""
    return chats.api.operations.search(query, identity, all_agents)
