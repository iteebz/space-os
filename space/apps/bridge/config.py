import json
from pathlib import Path

from space.apps.spawn import config as spawn_config
from space.lib import fs

SPACE_DIR = spawn_config.spawn_dir() / ".space"
BRIDGE_DIR = SPACE_DIR / "bridge"
DB_PATH = SPACE_DIR / "bridge.db"
CONFIG_FILE = SPACE_DIR / "config.json"
SENTINEL_LOG_PATH = SPACE_DIR / "security" / "sentinel.log"

LEGACY_BRIDGE_DIR = Path.home() / ".bridge"
LEGACY_SPACE_DIR = Path.home() / ".space"


def _load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    legacy_space_config = LEGACY_SPACE_DIR / "config.json"
    if legacy_space_config.exists():
        return json.loads(legacy_space_config.read_text())
    legacy_config = LEGACY_BRIDGE_DIR / "config.json"
    if legacy_config.exists():
        return json.loads(legacy_config.read_text())
    return {}


_config = _load_config()


INSTRUCTIONS_FILE = fs.guide_path("bridge.md")

WAIT_POLL_INTERVAL = 15.0


def resolve_sentinel_log_path() -> Path:
    """Return sentinel log path, ensuring parent directory exists."""
    SENTINEL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SENTINEL_LOG_PATH
