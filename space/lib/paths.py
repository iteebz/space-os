import os
from pathlib import Path

from space import config


def space_root(base_path: Path | None = None) -> Path:
    """Returns the space root directory, ~/space or base_path/space."""
    if base_path:
        return base_path / "space"

    workspace_root = Path.home() / "space"
    override = os.environ.get("SPACE_ROOT")
    return Path(override).expanduser() if override else workspace_root


def dot_space(base_path: Path | None = None) -> Path:
    """Returns .space/ directory in workspace root."""
    if base_path:
        return base_path / ".space"

    if "SPACE_DOT_SPACE" in os.environ:
        return Path(os.environ["SPACE_DOT_SPACE"]).expanduser()
    return space_root() / ".space"


def global_root(base_path: Path | None = None) -> Path:
    """Returns the global root directory, ~/.space."""
    if base_path:
        return base_path / ".space"

    if "SPACE_GLOBAL_ROOT" in os.environ:
        return Path(os.environ["SPACE_GLOBAL_ROOT"]).expanduser()
    return Path.home() / ".space"


def package_root() -> Path:
    """Returns space package root directory."""
    return Path(__file__).resolve().parent.parent


def constitution(filename: str) -> Path:
    """Returns the full path to a constitution file."""
    return package_root() / "constitutions" / filename


def canon_path(base_path: Path | None = None) -> Path:
    """Returns path to human's canonical values, ~/space/canon."""
    cfg = config.load_config()
    configured_path = cfg.get("canon_path")
    if configured_path:
        return space_root(base_path) / configured_path
    return space_root(base_path) / "canon"


def sessions_db() -> Path:
    """Returns path to unified session index, ~/.space/sessions.db."""
    if "SPACE_SESSIONS_DB" in os.environ:
        return Path(os.environ["SPACE_SESSIONS_DB"]).expanduser()
    return global_root() / "sessions.db"
