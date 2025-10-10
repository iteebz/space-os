from pathlib import Path

from ..lib import paths


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def registry_db() -> Path:
    """Return the registry database path in workspace .space directory."""
    return paths.space_root() / "spawn.db"


def bridge_dir() -> Path:
    """Return the bridge configuration directory scoped to the workspace."""
    return paths.space_root() / "bridge"


def bridge_identities_dir() -> Path:
    """Return the bridge identities directory under the current home."""
    return bridge_dir() / "identities"


def config_file() -> Path:
    return paths.space_root() / "config.yaml"


def init_config() -> None:
    from ..lib import config as libconfig

    libconfig.init_config()


__all__ = [
    "spawn_dir",
    "registry_db",
    "bridge_dir",
    "bridge_identities_dir",
    "config_file",
    "init_config",
]
