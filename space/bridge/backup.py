"""Utilities for backing up Bridge state to the local filesystem."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from . import config

BACKUP_CANDIDATES = [
    Path.home() / ".space" / "backups",
    Path.home() / ".bridge_backups",
]


def _resolve_backup_root() -> Path:
    """Pick or create the first usable backup root directory."""
    for candidate in BACKUP_CANDIDATES:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        return candidate
    raise RuntimeError("Unable to create a backup directory in any known location.")


def _copy_path(src: Path, dest: Path):
    """Copy a file or directory, skipping missing sources."""
    if not src.exists():
        return

    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def backup_bridge_data(timestamp: datetime | None = None) -> Path:
    """Persist Bridge databases and artefacts into a timestamped backup."""
    ts = (timestamp or datetime.now()).strftime("%Y%m%d-%H%M%S")
    root = _resolve_backup_root()
    target = root / ts
    target.mkdir(exist_ok=False)

    _copy_path(config.DB_PATH, target / "bridge.db")
    _copy_path(config.CONFIG_FILE, target / "config.json")
    _copy_path(config.BRIDGE_DIR, target / "bridge")

    # Legacy locations are kept for migrations from the standalone Bridge CLI.
    _copy_path(config.LEGACY_BRIDGE_DIR, target / "legacy_bridge")

    return target
