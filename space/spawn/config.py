from pathlib import Path

_MODULE_DIR = Path(__file__).resolve()
CONFIG_FILE = _MODULE_DIR.parent.parent.parent / "config.yaml"
CONSTITUTIONS_DIR = _MODULE_DIR.parent.parent.parent / "constitutions"


def workspace_root() -> Path:
    """Return the workspace root that owns the spawn project.

    Prefer the directory the user invoked Spawn from when it already
    contains this project, so agents inherit the caller's context. Fall back
    to repository markers when the invocation directory is unrelated.
    """

    current = Path.cwd()

    # Prefer the first directory in the cwd->root chain that exposes the
    # workspace anchors we expect (`AGENTS.md` today). This avoids trapping the
    # runtime inside `private/spawn` when the invocation happens there.
    for candidate in (current, *current.parents):
        if (candidate / "AGENTS.md").exists():
            return candidate

    for parent in _MODULE_DIR.parents:
        if (parent / ".git").exists():
            return parent

    for parent in _MODULE_DIR.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback: assume the standard private/spawn layout under the repo root.
    resolved_config = CONFIG_FILE.resolve()
    return resolved_config.parent.parent.parent


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def registry_db() -> Path:
    """Return the registry database path in workspace .space directory."""
    return workspace_root() / ".space" / "spawn.db"


def bridge_dir() -> Path:
    """Return the bridge configuration directory scoped to the workspace."""
    return workspace_root() / ".space" / "bridge"


def bridge_identities_dir() -> Path:
    """Return the bridge identities directory under the current home."""
    return bridge_dir() / "identities"


__all__ = [
    "CONFIG_FILE",
    "CONSTITUTIONS_DIR",
    "workspace_root",
    "spawn_dir",
    "registry_db",
    "bridge_dir",
    "bridge_identities_dir",
]
