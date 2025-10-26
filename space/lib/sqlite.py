"""SQLite storage backend implementation."""

import contextlib
import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def connect(db_path: Path) -> sqlite3.Connection:
    """Open connection to SQLite database."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    return conn


def ensure_schema(
    db_path: Path,
    migs: list[tuple[str, str | Callable]] | None = None,
) -> None:
    """Ensure schema exists and apply migrations."""
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        if migs:
            migrate(conn, migs)
        conn.commit()


def migrate(conn: sqlite3.Connection, migs: list[tuple[str, str | Callable]]) -> None:
    """Apply migrations to connection with data loss safeguards."""
    from space.lib import store

    conn.execute("CREATE TABLE IF NOT EXISTS _migrations (name TEXT PRIMARY KEY)")
    conn.commit()

    for name, migration in migs:
        applied = conn.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,)).fetchone()
        if applied:
            continue
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_migrations' AND name != 'sqlite_sequence'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            before = {t: store._get_table_count(conn, t) for t in tables}

            if callable(migration):
                migration(conn)
            else:
                if isinstance(migration, str) and ";" in migration:
                    conn.executescript(migration)
                else:
                    conn.execute(migration)

            for table, count_before in before.items():
                try:
                    store._check_migration_safety(conn, table, count_before, allow_loss=0)
                except ValueError as e:
                    logger.error(f"Migration '{name}' data loss detected: {e}")
                    raise

            conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (name,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration '{name}' failed: {e}")
            raise


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
