"""Bridge storage migration utilities."""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from space.os import config

from .db import ensure_bridge_dir


@dataclass
class MigrationResult:
    status: str
    message: str
    backup_path: Path | None = None


class MigrationError(RuntimeError):
    """Raised when bridge storage migration fails."""


def migrate_store_db() -> MigrationResult:
    """Migrate legacy ~/.bridge/store.db to ~/.space/bridge.db."""

    ensure_bridge_dir()

    legacy_path = _legacy_db_path()
    new_path = _new_db_path()
    backup_base = config.LEGACY_BRIDGE_DIR.parent / ".bridge_backups"

    legacy_exists = legacy_path.exists()
    new_exists = new_path.exists()

    if not legacy_exists:
        if new_exists:
            return MigrationResult(
                status="skipped",
                message=f"Legacy bridge store not found at {legacy_path}. Nothing to migrate.",
            )
        raise MigrationError(
            f"Legacy bridge store not found at {legacy_path}. No destination database present either."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_base.mkdir(parents=True, exist_ok=True)
    backup_path = backup_base / f"{timestamp}_store.db"
    shutil.copy2(legacy_path, backup_path)

    tmp_destination = new_path.with_suffix(".migrating")
    shutil.copy2(legacy_path, tmp_destination)

    _verify_copy(legacy_path, tmp_destination)

    if new_exists:
        # Preserve previous destination before replacement
        prior_backup = backup_base / f"{timestamp}_bridge.db"
        shutil.copy2(new_path, prior_backup)

    tmp_destination.replace(new_path)
    legacy_path.unlink()

    message = (
        "Migrated bridge store -> ~/.space/bridge.db "
        f"(messages={_table_count(new_path, 'messages')}, channels={_table_count(new_path, 'channels')})."
    )

    return MigrationResult(status="migrated", message=message, backup_path=backup_path)


def _table_count(db_path: Path, table: str) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
        row = cursor.fetchone()
        return int(row[0]) if row else 0


def _verify_copy(source: Path, target: Path) -> None:
    source_counts, source_sequences = _snapshot_db(source)
    target_counts, target_sequences = _snapshot_db(target)

    if source_counts != target_counts:
        raise MigrationError(
            f"Row count mismatch after copy: source={source_counts} target={target_counts}"
        )

    if source_sequences != target_sequences:
        raise MigrationError(
            "sqlite_sequence mismatch after copy: "
            f"source={source_sequences} target={target_sequences}"
        )


def _snapshot_db(db_path: Path) -> tuple[dict[str, int], dict[str, int]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = [row[0] for row in rows if row[0] != "sqlite_sequence"]
        counts = {
            table: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }

        sequences: dict[str, int] = {}
        if any(row[0] == "sqlite_sequence" for row in rows):
            sequences = {
                name: int(seq)
                for name, seq in conn.execute("SELECT name, seq FROM sqlite_sequence")
            }

    return counts, sequences


def _legacy_db_path() -> Path:
    return config.LEGACY_BRIDGE_DIR / "store.db"


def _new_db_path() -> Path:
    return config.DB_PATH
