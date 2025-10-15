import shutil
from functools import lru_cache
from pathlib import Path

import yaml


def get_default_config_path() -> Path:
    from .lib import paths
    return paths.package_root() / "config.yaml"


def config_file() -> Path:
    """Return config file path in .space/"""
    from .lib import paths
    return paths.dot_space() / "config.yaml"


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def registry_db() -> Path:
    """Return the registry database path in workspace .space directory."""
    from .lib import paths
    return paths.dot_space() / "spawn.db"


def clear_cache():
    load_config.cache_clear()


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load the config.yaml file, returning its content or an empty dict if not found."""
    path = config_file()
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def init_config() -> None:
    """Initialize .space/config.yaml from defaults if missing."""
    target = config_file()
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    default_config_path = get_default_config_path()
    if not default_config_path.exists():
        raise FileNotFoundError(f"Default config not found at {default_config_path}")

    shutil.copy(default_config_path, target)
