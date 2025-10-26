import json
from pathlib import Path

from space.lib import store


def export(session_id: str, cli: str, include_tools: bool = False) -> list[dict] | None:
    """Export chat messages as list. Optionally filter tool calls."""
    with store.ensure("chats") as conn:
        row = conn.execute(
            "SELECT file_path FROM sessions WHERE cli = ? AND session_id = ?",
            (cli, session_id),
        ).fetchone()

    if not row:
        return None

    vault_path = Path(row["file_path"])
    if not vault_path.exists():
        return None

    messages = []
    try:
        with open(vault_path) as f:
            for line in f:
                if not line.strip():
                    continue
                msg = json.loads(line)

                if not include_tools and msg.get("role") == "tool":
                    continue

                messages.append(msg)
    except Exception:
        return None

    return messages
