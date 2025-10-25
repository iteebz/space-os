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

    return paths.space_data() / "config.yaml"


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def registry_db() -> Path:
    """Return the registry database path in workspace .space directory."""
    from .lib import paths

    return paths.space_data() / "spawn.db"


def _validate_config(cfg: dict) -> None:
    """Validate config structure. Fail fast on invalid types."""
    if not isinstance(cfg, dict):
        raise ValueError(f"Config must be a dict, got {type(cfg).__name__}")

    if "roles" in cfg and not isinstance(cfg.get("roles"), dict):
        raise ValueError("Config 'roles' must be a dict")


def _clear_cache():
    load_config.cache_clear()


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load the config.yaml file, returning its content or an empty dict if not found."""
    path = config_file()
    if not path.exists():
        return {}
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    _validate_config(cfg)
    return cfg


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
