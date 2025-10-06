import json
from pathlib import Path

from space.lib import fs  # Added import

_MODULE_DIR = Path(__file__).resolve()
CONFIG_FILE = fs.root() / ".space" / "config.json"  # Changed path


def spawn_dir() -> Path:
    """Return the spawn working directory under the current home."""
    return Path.home() / ".spawn"


def read() -> dict:
    """Read the configuration from the JSON file."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def write(config_data: dict) -> None:
    """Write the configuration to the JSON file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
