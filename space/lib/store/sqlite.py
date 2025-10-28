"""SQLite storage backend implementation."""

import contextlib
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def connect(db_path: Path) -> sqlite3.Connection:
    """Open connection to SQLite database."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def resolve(db_dir: Path) -> None:
    """Resolve WAL files by checkpointing all databases in directory.

    Merges WAL (Write-Ahead Logging) data into main database files,
    creating complete, standalone snapshots suitable for backup/transfer.

    Args:
            db_dir: Directory containing *.db files
    """
    for db_file in sorted(db_dir.glob("*.db")):
        try:
            conn = connect(db_file)
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA wal_checkpoint(RESTART)")
            conn.close()

            for artifact in db_file.parent.glob(f"{db_file.name}-*"):
                with contextlib.suppress(OSError):
                    artifact.unlink()

            logger.info(f"Resolved {db_file.name}")
        except sqlite3.DatabaseError as e:
            logger.warning(f"Failed to resolve {db_file.name}: {e}")
