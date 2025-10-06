from pathlib import Path
from space.os.lib import fs

SPACE_DIR = fs.root() / ".space"

def data_for(app_name: str) -> Path:
    """Returns the path to the app's dedicated database."""
    db_path = SPACE_DIR / "apps" / f"{app_name}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
