import shutil
from pathlib import Path

import yaml

from . import paths

DEFAULT_CONFIG = paths.package_root() / "config.yaml"




def config_file() -> Path:
    """Return config file path in .space/"""
    return paths.space_root() / "config.yaml"


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

    if not DEFAULT_CONFIG.exists():
        raise FileNotFoundError(f"Default config not found at {DEFAULT_CONFIG}")

    shutil.copy(DEFAULT_CONFIG, target)
