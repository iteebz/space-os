
from pathlib import Path

from space.apps.spawn import config as spawn_config
from space.apps.registry.guides import _prompts_guides_dir

SPACE_DIR = spawn_config.spawn_dir() / ".space"
BRIDGE_DIR = SPACE_DIR / "bridge"
DB_PATH = SPACE_DIR / "bridge.db"





WAIT_POLL_INTERVAL = 15.0

