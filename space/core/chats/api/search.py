from pathlib import Path

from space.lib import providers, store


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search chat sessions by query. Returns metadata + matched line count."""
    results = []

    with store.ensure("chats") as conn:
        sql = "SELECT cli, session_id, file_path, identity FROM sessions WHERE 1=1"
        params = []

        if identity and not all_agents:
            sql += " AND identity = ?"
            params.append(identity)

        sessions = conn.execute(sql, params).fetchall()

    for session_row in sessions:
        cli = session_row["cli"]
        session_id = session_row["session_id"]
        file_path = session_row["file_path"]
        sess_identity = session_row["identity"]

        if not Path(file_path).exists():
            continue

        provider = getattr(providers, cli, None)
        if not provider:
            continue

        try:
            messages = provider.parse_messages(Path(file_path))
            matched = 0

            for msg in messages:
                if query.lower() in (msg.get("content") or "").lower():
                    matched += 1

            if matched > 0:
                results.append(
                    {
                        "source": "chats",
                        "cli": cli,
                        "session_id": session_id,
                        "identity": sess_identity,
                        "matches": matched,
                        "timestamp": messages[-1].get("timestamp") if messages else None,
                        "reference": f"chats:{cli}:{session_id}",
                    }
                )
        except Exception:
            pass

    return results
