from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from space.lib import providers, store

from . import vault


def _discover_provider(cli_name: str) -> tuple[str, list[dict]]:
    """Discover sessions for a single provider. Returns (cli_name, sessions)."""
    provider = getattr(providers, cli_name)
    sessions = provider.discover_sessions()
    return cli_name, sessions


def discover() -> dict[str, int]:
    """Scan all providers for chat sessions. Copy to vault. Returns {cli: count_discovered}."""
    results = {"claude": 0, "codex": 0, "gemini": 0}

    provider_results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_discover_provider, cli): cli
            for cli in ("claude", "codex", "gemini")
        }
        for future in as_completed(futures):
            cli_name, sessions = future.result()
            provider_results[cli_name] = sessions

    with store.ensure("chats") as conn:
        for cli_name, sessions in provider_results.items():
            for session in sessions:
                try:
                    session_id = session["session_id"]
                    file_path = session["file_path"]
                    
                    vault_path = vault.copy_session_to_vault(cli_name, session_id, file_path)
                    
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO sessions
                        (cli, session_id, file_path, discovered_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            cli_name,
                            session_id,
                            vault_path,
                            datetime.now().isoformat(),
                        ),
                    )

                    conn.execute(
                        """
                        INSERT OR IGNORE INTO syncs
                        (cli, session_id)
                        VALUES (?, ?)
                        """,
                        (cli_name, session_id),
                    )
                    results[cli_name] += 1
                except Exception:
                    pass

    return results
