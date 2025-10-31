"""Context search: canon documents."""

from space.apps import canon


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search canon documents by query."""
    results = []

    for result in canon.search(query):
        results.append(
            {
                "source": result["source"],
                "path": result["path"],
                "content": result["content"],
                "reference": result["reference"],
            }
        )

    return results
