from pathlib import Path


def space_root() -> Path:
    return Path.home() / "space"


def dot_space() -> Path:
    return Path.home() / ".space"


def package_root() -> Path:
    return Path(__file__).resolve().parent.parent


def constitution(constitution_file: str) -> Path:
    canon = canon_path() / "constitutions" / constitution_file
    if canon.exists():
        return canon
    return package_root() / "core" / "spawn" / "constitutions" / constitution_file


def canon_path() -> Path:
    return space_root() / "canon"


def sessions_dir() -> Path:
    return dot_space() / "sessions"


def spawns_dir() -> Path:
    return dot_space() / "spawns"


def identity_dir(identity: str) -> Path:
    return spawns_dir() / identity


def backups_dir() -> Path:
    return Path.home() / ".space_backups"


def backup_snapshot(timestamp: str) -> Path:
    return backups_dir() / "data" / timestamp


def backup_sessions_dir() -> Path:
    return backups_dir() / "sessions"


def validate_domain_path(domain: str) -> tuple[bool, str]:
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
