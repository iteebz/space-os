from pathlib import Path

from space.lib import providers


def export(session_id: str, cli: str) -> str | None:
    """Export raw chat content. Returns raw JSONL/JSON as string."""
    provider = getattr(providers, cli, None)
    if not provider:
        return None

    sessions = provider.discover_sessions()
    file_path = next((s["file_path"] for s in sessions if s["session_id"] == session_id), None)

    if not file_path or not Path(file_path).exists():
        return None

    try:
        with open(file_path) as f:
            return f.read()
    except Exception:
        return None
