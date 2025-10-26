import json
from pathlib import Path

from space.lib import store


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search raw JSONL chats by query. Returns matching messages."""
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

        vault_path = Path(file_path)
        if not vault_path.exists():
            continue

        try:
            with open(vault_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    content = msg.get("content", "")

                    if query.lower() in content.lower():
                        results.append(
                            {
                                "source": "chats",
                                "cli": cli,
                                "session_id": session_id,
                                "identity": sess_identity,
                                "role": msg.get("role"),
                                "content": content,
                                "timestamp": msg.get("timestamp"),
                                "reference": f"chats:{cli}:{session_id}",
                            }
                        )
        except Exception:
            pass

    return results
