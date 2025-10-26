from datetime import datetime

from space.lib import db

from . import providers


def discover() -> dict[str, int]:
    """Scan all providers for chat sessions. Returns {cli: count_discovered}."""
    results = {"claude": 0, "codex": 0, "gemini": 0}

    with db.ensure("chats") as conn:
        for cli_name, provider in providers.PROVIDERS.items():
            sessions = provider.discover_sessions()
            
            for session in sessions:
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO sessions 
                        (cli, session_id, file_path, discovered_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            cli_name,
                            session["session_id"],
                            session["file_path"],
                            datetime.now().isoformat(),
                        ),
                    )
                    
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO syncs 
                        (cli, session_id)
                        VALUES (?, ?)
                        """,
                        (cli_name, session["session_id"]),
                    )
                    results[cli_name] += 1
                except Exception:
                    pass

    return results
