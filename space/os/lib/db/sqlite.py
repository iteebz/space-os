"""SQLite storage backend implementation."""

import contextlib
import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

from space.os.lib import paths

from . import safeguards

logger = logging.getLogger(__name__)

_registry: dict[str, tuple[str, str]] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}


def connect(db_path: Path) -> sqlite3.Connection:
    """Open connection to SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    return conn


def ensure_schema(
    db_path: Path,
    schema: str,
    migs: list[tuple[str, str | Callable]] | None = None,
) -> None:
    """Ensure schema exists and apply migrations."""
    with connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(schema)
        if migs:
            migrate(conn, migs)
        conn.commit()


def register(name: str, db_file: str, schema: str) -> None:
    """Register database in global registry.

    Args:
        name: Database identifier
        db_file: Filename for database
        schema: SQL schema definition
    """
    _registry[name] = (db_file, schema)


def add_migrations(name: str, migs: list[tuple[str, str | Callable]]) -> None:
    """Register migrations for database."""
    _migrations[name] = migs


def ensure(name: str) -> sqlite3.Connection:
    """Ensure registered database exists and return connection.

    Raises ValueError if database not registered.
    """
    if name not in _registry:
        raise ValueError(f"Database '{name}' not registered. Call db.register() first.")
    db_file, schema = _registry[name]
    db_path = paths.space_data() / db_file
    db_path.parent.mkdir(parents=True, exist_ok=True)
    migs = _migrations.get(name)
    if not db_path.exists():
        ensure_schema(db_path, schema, migs)
    else:
        with connect(db_path) as conn:
            if migs:
                migrate(conn, migs)
    return connect(db_path)


def migrate(conn: sqlite3.Connection, migs: list[tuple[str, str | Callable]]) -> None:
    """Apply migrations to connection with data loss safeguards."""
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
            tables_before = [row[0] for row in cursor.fetchall()]
            guard = {t: safeguards.MigrationSafeguard(conn, t) for t in tables_before}

            if callable(migration):
                migration(conn)
            else:
                if isinstance(migration, str) and ";" in migration:
                    conn.executescript(migration)
                else:
                    conn.execute(migration)

            for _table, sg in guard.items():
                try:
                    sg.after(allow_loss=0)
                except ValueError as e:
                    logger.error(f"Migration '{name}' data loss detected: {e}")
                    raise

            conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (name,))
            conn.commit()
            logger.info(f"Migration '{name}' applied successfully")
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


def registry() -> dict[str, tuple[str, str]]:
    """Return registry of all registered databases."""
    return _registry.copy()


def _reset_for_testing() -> None:
    """Reset registry and migrations state (test-only)."""
    _registry.clear()
    _migrations.clear()
