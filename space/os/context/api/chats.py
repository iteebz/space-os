"""Context search: provider chat logs."""

import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from space.lib import providers


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search provider chat logs directly (stateless, ephemeral discovery)."""
    results = []
    query_lower = query.lower()

    def _discover_and_search_provider(cli_name: str) -> list[dict]:
        """Discover and search a single provider's chats."""
        provider_results = []
        try:
            provider = getattr(providers, cli_name)()
            sessions = provider.discover_sessions()

            for session in sessions:
                try:
                    file_path = Path(session["file_path"])
                    if not file_path.exists():
                        continue

                    session_id = session["session_id"]
                    messages = provider.parse_messages(file_path)

                    for msg in messages:
                        content = msg.get("content", "")
                        if query_lower in content.lower():
                            provider_results.append(
                                {
                                    "source": "provider-chats",
                                    "cli": cli_name,
                                    "session_id": session_id,
                                    "identity": None,
                                    "role": msg.get("role"),
                                    "text": content,
                                    "timestamp": msg.get("timestamp"),
                                    "reference": f"provider-chats:{cli_name}:{session_id}",
                                }
                            )
                except Exception:
                    pass

        except Exception:
            pass

        return provider_results

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_discover_and_search_provider, cli): cli
            for cli in ("claude", "codex", "gemini")
        }
        for future in as_completed(futures):
            with contextlib.suppress(Exception):
                results.extend(future.result())

    return results
