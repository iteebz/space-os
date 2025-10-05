import json
from pathlib import Path

from agent_space.spawn import config as spawn_config

SPACE_DIR = spawn_config.workspace_root() / ".space"
BRIDGE_DIR = SPACE_DIR / "bridge"
IDENTITIES_DIR = BRIDGE_DIR / "identities"
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


def _get_identity_file(base: str) -> Path:
    default = IDENTITIES_DIR / f"{base}.md"
    path = Path(_config.get(base, default))
    if path.exists():
        return path

    workspace_fallback = SPACE_DIR / "identities" / f"{base}.md"
    if workspace_fallback.exists():
        return workspace_fallback

    legacy = LEGACY_BRIDGE_DIR / "identities" / f"{base}.md"
    if legacy.exists():
        return legacy

    return path


INSTRUCTIONS_FILE = Path(__file__).resolve().parent.parent.parent / "protocols" / "bridge.md"

WAIT_POLL_INTERVAL = 15.0


def resolve_sentinel_log_path() -> Path:
    """Return sentinel log path, ensuring parent directory exists."""
    SENTINEL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SENTINEL_LOG_PATH
