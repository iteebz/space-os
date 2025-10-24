from pathlib import Path

from space.os import config


def space_root() -> Path:
    """Returns the space root directory, ~/space."""
    return Path.home() / "space"


def dot_space() -> Path:
    """Returns the .space directory, ~/.space."""
    return Path.home() / ".space"


def space_data() -> Path:
    """Returns the data directory, ~/.space/data."""
    return Path.home() / ".space" / "data"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(filename: str) -> Path:
    """Returns the full path to a constitution file."""
    return package_root().parent / "constitutions" / filename


def canon_path() -> Path:
    """Returns path to human's canonical values, ~/space/canon."""
    cfg = config.load_config()
    configured_path = cfg.get("canon_path")
    if configured_path:
        return space_root() / configured_path
    return space_root() / "canon"


def chats_db() -> Path:
    """Returns path to unified chat history, ~/.space/data/chats.db."""
    return space_data() / "chats.db"


def backups_dir() -> Path:
    """Returns the backups directory, ~/.space/backups (read-only)."""
    return Path.home() / ".space" / "backups"


def backup_snapshot(timestamp: str) -> Path:
    """Returns immutable path to timestamped backup snapshot.

    Args:
        timestamp: ISO format or YYYYMMDDhhmmss format

    Returns:
        Path like ~/.space/backups/20251025_001530/
    """
    return backups_dir() / timestamp


def validate_backup_path(backup_path: Path) -> bool:
    """Validate backup path is within backups/ to prevent traversal."""
    try:
        backup_path.resolve().relative_to(backups_dir().resolve())
        return True
    except ValueError:
        return False
