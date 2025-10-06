from pathlib import Path

from space.lib import fs

_MODULE_DIR = Path(__file__).resolve()
CONFIG_FILE = _MODULE_DIR.parent.parent.parent / "config.yaml"


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def registry_db() -> Path:
    """Return the registry database path in workspace .space directory."""
    return fs.root() / ".space" / "spawn.db"


__all__ = [
    "CONFIG_FILE",
    "spawn_dir",
    "registry_db",
]
