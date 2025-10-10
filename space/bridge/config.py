import json

from ..lib import paths

SPACE_DIR = paths.space_root()
BRIDGE_DIR = SPACE_DIR / "bridge"
DB_PATH = SPACE_DIR / "bridge.db"
CONFIG_FILE = SPACE_DIR / "config.json"


def _load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


_config = _load_config()
