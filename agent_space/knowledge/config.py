from pathlib import Path


def workspace_root() -> Path:
    """Find workspace root by looking for .space directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".space").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def knowledge_db() -> Path:
    """Return knowledge database path."""
    return workspace_root() / ".space" / "knowledge.db"
