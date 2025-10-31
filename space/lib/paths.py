from pathlib import Path


def space_root() -> Path:
    """Returns the space root directory, ~/space."""
    return Path.home() / "space"


def dot_space() -> Path:
    """Returns the .space directory, ~/.space."""
    return Path.home() / ".space"


def space_data() -> Path:
    """Returns the data directory, ~/.space/data."""
    return dot_space() / "data"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(constitution_name: str) -> Path:
    """Returns the full path to a constitution file.

    Checks canon first (SSOT), falls back to local.
    Accepts constitution name (e.g., "zealot") and appends .md extension.
    """
    filename = f"{constitution_name}.md"
    canon = canon_path() / "constitutions" / filename
    if canon.exists():
        return canon
    return package_root() / "core" / "spawn" / "constitutions" / filename


def canon_path() -> Path:
    """Returns path to human's canonical values, ~/space/canon."""
    return space_root() / "canon"


def chats_db() -> Path:
    """Returns path to unified chat history, ~/.space/data/chats.db."""
    return space_data() / "chats.db"


def chats_dir() -> Path:
    """Returns the chats directory, ~/.space/chats."""
    return dot_space() / "chats"


def backups_dir() -> Path:
    """Returns the backups directory, ~/.space_backups (read-only)."""
    return Path.home() / ".space_backups"


def backup_snapshot(timestamp: str) -> Path:
    """Returns immutable path to timestamped backup snapshot.

    Args:
        timestamp: ISO format or YYYYMMDDhhmmss format

    Returns:
        Path like ~/.space_backups/data/20251025_001530/
    """
    return backups_dir() / "data" / timestamp


def backup_chats_latest() -> Path:
    """Returns path to latest chat backup (single copy, overwrites).

    Returns:
        Path like ~/.space_backups/chats/latest/
    """
    return backups_dir() / "chats" / "latest"


def validate_backup_path(backup_path: Path) -> bool:
    """Validate backup path is within backups/ to prevent traversal."""
    try:
        backup_path.resolve().relative_to(backups_dir().resolve())
        return True
    except ValueError:
        return False


def validate_domain_path(domain: str) -> tuple[bool, str]:
    """Validate domain/topic path format.

    Returns:
        (is_valid, error_message)
    """
    if not domain:
        return False, "Domain/topic cannot be empty"
    if domain.startswith("/") or domain.endswith("/"):
        return False, "Domain/topic cannot start or end with '/'"
    if "//" in domain:
        return False, "Domain/topic cannot contain consecutive '/'"
    if not all(
        part.isidentifier() or part.replace("-", "").replace("_", "").isalnum()
        for part in domain.split("/")
    ):
        return False, "Domain/topic parts must be alphanumeric (with - and _ allowed)"
    return True, ""
