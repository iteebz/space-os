import json
from pathlib import Path

SPACE_DIR = Path.cwd() / ".space"
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
    default = SPACE_DIR / "identities" / f"{base}.md"
    path = Path(_config.get(base, default))
    if not path.exists():
        legacy = LEGACY_BRIDGE_DIR / "identities" / f"{base}.md"
        if legacy.exists():
            return legacy
    return path


INSTRUCTIONS_FILE = Path(__file__).resolve().parent.parent.parent / "prompts" / "instructions.md"

WAIT_POLL_INTERVAL = 15.0


def resolve_sentinel_log_path() -> Path:
    """Return sentinel log path, ensuring parent directory exists."""
    SENTINEL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    return SENTINEL_LOG_PATH
