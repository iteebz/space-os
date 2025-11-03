"""Chat operations: query and stats."""

import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from space.lib import paths, providers, store


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search provider chat logs directly (stateless, ephemeral discovery)."""
    results = []
    query_lower = query.lower()

    def _discover_and_search_provider(cli_name: str) -> list[dict]:
        """Discover and search a single provider's chats."""
        provider_results = []
        try:
            provider = getattr(providers, cli_name)()
            sessions = provider.discover_chats()

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


def get_provider_stats() -> dict[str, dict]:
    """Get chat statistics across all providers.

    Returns:
        {provider_name: {"files": int, "size_mb": float}} for each provider
    """
    chats_dir = paths.chats_dir()
    stats = {}

    if not chats_dir.exists():
        return stats

    for provider_dir in chats_dir.iterdir():
        if not provider_dir.is_dir():
            continue

        provider_name = provider_dir.name
        files = list(provider_dir.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        size_bytes = sum(f.stat().st_size for f in files if f.is_file())
        size_mb = size_bytes / (1024 * 1024)

        stats[provider_name] = {
            "files": file_count,
            "size_mb": size_mb,
        }

    return stats


def get_stats() -> dict:
    """Get chat statistics from chats table.

    Returns aggregated chat metrics by provider and agent.
    """
    with store.ensure() as conn:
        total_chats = conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        totals = conn.execute(
            "SELECT COALESCE(SUM(message_count), 0), COALESCE(SUM(tools_used), 0), "
            "COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) FROM chats"
        ).fetchone()

        by_provider = conn.execute(
            "SELECT provider, COUNT(*), COALESCE(SUM(message_count), 0), "
            "COALESCE(SUM(tools_used), 0), COALESCE(SUM(input_tokens), 0), "
            "COALESCE(SUM(output_tokens), 0) FROM chats GROUP BY provider"
        ).fetchall()

        by_agent = conn.execute(
            "SELECT a.identity, COUNT(c.id), COALESCE(SUM(c.message_count), 0), "
            "COALESCE(SUM(c.tools_used), 0), COALESCE(SUM(c.input_tokens), 0), "
            "COALESCE(SUM(c.output_tokens), 0) FROM agents a LEFT JOIN chats c ON "
            "c.session_id IN (SELECT id FROM sessions WHERE agent_id = a.agent_id) "
            "GROUP BY a.agent_id ORDER BY COALESCE(SUM(c.message_count), 0) DESC"
        ).fetchall()

    def to_dict(row, keys):
        return {k: row[i] for i, k in enumerate(keys)}

    return {
        "total_chats": total_chats,
        "total_messages": totals[0],
        "total_tools_used": totals[1],
        "total_input_tokens": totals[2],
        "total_output_tokens": totals[3],
        "by_provider": {
            row[0]: to_dict(
                row[1:], ["chats", "messages", "tools_used", "input_tokens", "output_tokens"]
            )
            for row in by_provider
        },
        "by_agent": [
            to_dict(
                row,
                ["identity", "chats", "messages", "tools_used", "input_tokens", "output_tokens"],
            )
            for row in by_agent
        ],
    }
