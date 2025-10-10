import shutil
from pathlib import Path

from . import paths

DEFAULT_CONFIG = paths.package_root() / "config.yaml"


def workspace_root() -> Path:
    """Return workspace root containing .space/"""
    current = Path.cwd()

    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists():
            return candidate

    for parent in _MODULE_DIR.parents:
        if (parent / ".git").exists():
            return parent

    for parent in _MODULE_DIR.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    return current


def space_root() -> Path:
    """Return .space/ directory in workspace."""
    return workspace_root() / ".space"


def config_file() -> Path:
    """Return config file path in .space/"""
    return space_root() / "config.yaml"


def init_config() -> None:
    """Initialize .space/config.yaml from defaults if missing."""
    target = config_file()
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if not DEFAULT_CONFIG.exists():
        raise FileNotFoundError(f"Default config not found at {DEFAULT_CONFIG}")

    shutil.copy(DEFAULT_CONFIG, target)
