from pathlib import Path

from space.lib import config


def space_root() -> Path:
    """Returns the space root directory, ~/space."""
    return Path.home() / "space"


def dot_space() -> Path:
    """Returns .space/ directory in workspace root."""
    return space_root() / ".space"


def backup_root() -> Path:
    """Returns the backup root directory, ~/.space."""
    return Path.home() / ".space"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(filename: str) -> Path:
    """Returns the full path to a constitution file."""
    return package_root() / "constitutions" / filename


def canon_path() -> Path:
    """Returns path to human's canonical values, ~/space/canon."""
    cfg = config.load_config()
    configured_path = cfg.get("canon_path")
    if configured_path:
        return space_root() / configured_path
    return space_root() / "canon"
