from pathlib import Path

from space.lib import config


def _resolve_path(default_component: str, base_path: Path | None = None) -> Path:
    if base_path:
        return base_path / default_component
    return Path.home() / default_component


def space_root(base_path: Path | None = None) -> Path:
    """Returns the space root directory, ~/space or base_path/space."""
    return _resolve_path("space", base_path)


def dot_space(base_path: Path | None = None) -> Path:
    """Returns .space/ directory in workspace root."""
    return space_root(base_path) / ".space"


def global_root(base_path: Path | None = None) -> Path:
    """Returns the global root directory, ~/.space."""
    return _resolve_path(".space", base_path)


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
