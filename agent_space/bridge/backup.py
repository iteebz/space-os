"""Bridge backup utility. Can be run as a standalone script."""

import shutil
from datetime import datetime
from pathlib import Path

# Adjust imports to be absolute from the project root
from bridge.config import SPACE_DIR
from bridge.storage.db import ensure_bridge_dir


def backup_bridge_data():
    """Backup complete .bridge folder with timestamp."""
    ensure_bridge_dir()

    if not SPACE_DIR.exists():
        print("No .space directory found to backup")
        raise FileNotFoundError("No .space directory found to backup")

    # Create backup directory
    backup_base = Path.home() / ".bridge_backups"
    backup_base.mkdir(exist_ok=True)

    # Generate timestamped backup name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_base / timestamp

    # Copy entire .space folder
    shutil.copytree(SPACE_DIR, backup_path)

    return backup_path


if __name__ == "__main__":
    try:
        backup_path = backup_bridge_data()
        print(f"Backup created: {backup_path}")
    except FileNotFoundError as e:
        print(f"Backup failed: {e}")
    except Exception as e:
        print(f"Backup failed: {e}")
