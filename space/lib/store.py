"""Generic storage abstraction - database registry and lifecycle management."""

import logging
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from space.lib import paths

logger = logging.getLogger(__name__)

T = TypeVar("T")

_registry: dict[str, tuple[str, str]] = {}
_migrations: dict[str, list[tuple[str, str | Callable]]] = {}
_connections = threading.local()

Row = sqlite3.Row


def from_row(row: dict[str, Any] | Any, dataclass_type: type[T]) -> T:
    """Convert dict-like row to dataclass instance.

    Matches row keys to dataclass field names. Works with any dict-like object
    (sqlite3.Row, dict, etc.) allowing backend-agnostic conversions.
    """
    field_names = {f.name for f in fields(dataclass_type)}
    row_dict = dict(row) if not isinstance(row, dict) else row
    kwargs = {key: row_dict[key] for key in field_names if key in row_dict}
    return dataclass_type(**kwargs)


def _get_table_count(conn: sqlite3.Connection, table: str) -> int:
    """Get row count for table, returns 0 if table doesn't exist."""
    try:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cursor.fetchone()[0]:
            return 0
        result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0


def _check_migration_safety(
    conn: sqlite3.Connection, table: str, before: int, allow_loss: int = 0
) -> None:
    """Verify row count after migration, raise if data loss exceeds threshold.

    Args:
        conn: Database connection
        table: Table name to check
        before: Row count before migration
        allow_loss: Max rows permitted to be lost (e.g., duplicates removed)

    Raises:
        ValueError: If data loss detected exceeds allow_loss
    """
    after = _get_table_count(conn, table)
    lost = before - after

    if lost > allow_loss:
        msg = f"Migration {table}: {lost} rows lost (before: {before}, after: {after})"
        logger.error(msg)
        raise ValueError(msg)

    if lost > 0:
        logger.warning(
            f"Migration {table}: {lost} rows removed (expected for allow_loss={allow_loss})"
        )


class BackupSafeguard:
    """Prevents recovery from empty backups."""

    @staticmethod
    def check_backup_has_data(backup_path: Path, db_name: str, min_rows: int = 1) -> bool:
        """Check if a backup database has actual data.

        Args:
            backup_path: Path to backup directory
            db_name: Database filename (e.g., 'memory.db')
            min_rows: Minimum expected rows (excluding schema tables)

        Returns:
            True if data exists, False otherwise

        Raises:
            FileNotFoundError if backup doesn't exist
        """
        db_file = backup_path / db_name
        if not db_file.exists():
            return False

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_migrations'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                logger.warning(f"Backup {backup_path.name}/{db_name}: no data tables")
                conn.close()
                return False

            total_rows = 0
            for table in tables:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                count = result[0] if result else 0
                total_rows += count

            conn.close()

            if total_rows < min_rows:
                logger.warning(
                    f"Backup {backup_path.name}/{db_name}: only {total_rows} rows (expected ≥{min_rows})"
                )
                return False

            logger.info(f"Backup {backup_path.name}/{db_name}: {total_rows} rows ✓")
            return True

        except sqlite3.DatabaseError as e:
            logger.error(f"Backup {backup_path.name}/{db_name}: corrupted - {e}")
            return False

    @staticmethod
    def get_backup_stats(backup_path: Path, db_name: str) -> dict:
        """Get row counts for all tables in backup database.

        Returns:
            Dict like {'table_name': row_count, ...}
        """
        db_file = backup_path / db_name
        if not db_file.exists():
            return {}

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_migrations'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            stats = {}
            for table in tables:
                result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                stats[table] = result[0] if result else 0

            conn.close()
            return stats

        except sqlite3.DatabaseError:
            return {}


class DatabaseHealthCheck:
    """Monitor for dramatic database changes."""

    @staticmethod
    def compare_snapshots(before: dict, after: dict, threshold: float = 0.8) -> list[str]:
        """Compare before/after snapshots and find concerning changes.

        Args:
            before: {'db_name': row_count, ...}
            after: {'db_name': row_count, ...}
            threshold: Alert if any DB lost more than this fraction (0.8 = 80%)

        Returns:
            List of warning messages
        """
        warnings = []

        for db_name, before_count in before.items():
            after_count = after.get(db_name, 0)
            if before_count == 0:
                continue

            loss_pct = (before_count - after_count) / before_count
            if loss_pct > threshold:
                warnings.append(
                    f"{db_name}: {loss_pct * 100:.0f}% data loss ({before_count} → {after_count} rows)"
                )

        for db_name, after_count in after.items():
            before_count = before.get(db_name, 0)
            if before_count > 0 and after_count == 0:
                warnings.append(f"{db_name}: completely emptied ({before_count} → 0 rows)")

        return warnings


def register(name: str, db_file: str) -> None:
    """Register database in global registry.

    Args:
        name: Database identifier
        db_file: Filename for database
    """
    _registry[name] = db_file


def add_migrations(name: str, migs: list[tuple[str, str | Callable]]) -> None:
    """Register migrations for database."""
    _migrations[name] = migs


def ensure(name: str) -> sqlite3.Connection:
    """Ensure registered database exists and return connection.

    This is the main entry point - imports sqlite to establish connection.
    """
    from space.lib import sqlite

    if name not in _registry:
        raise ValueError(f"Database '{name}' not registered. Call store.register() first.")

    if not hasattr(_connections, name):
        db_file = _registry[name]
        db_path = paths.space_data() / db_file
        db_path.parent.mkdir(parents=True, exist_ok=True)
        migs = _migrations.get(name)
        sqlite.ensure_schema(db_path, migs)
        setattr(_connections, name, sqlite.connect(db_path))

    return getattr(_connections, name)


def registry() -> dict[str, tuple[str, str]]:
    """Return registry of all registered databases."""
    return _registry.copy()


def _reset_for_testing() -> None:
    """Reset registry and migrations state (test-only)."""
    _registry.clear()
    _migrations.clear()
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()


def close_all():
    """Close all managed database connections."""
    if hasattr(_connections, "__dict__"):
        for conn in _connections.__dict__.values():
            conn.close()
        _connections.__dict__.clear()
