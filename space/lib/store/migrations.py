"""Database schema migrations and initialization."""

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

from space.lib.store.sqlite import connect

logger = logging.getLogger(__name__)


def load_migrations(module_path: str) -> list[tuple[str, str]]:
    """Load migrations from migrations/ directory.

    Reads numbered .sql files (001_*.sql, 002_*.sql, etc.) and returns
    as migration tuples (name, sql_content) in lexical order.

    Args:
        module_path: Module path like 'space.apps.chats' or 'space.os.spawn'

    Returns:
        List of (migration_name, sql_content) tuples
    """
    parts = module_path.split(".")
    module_dir = Path(__file__).parent.parent.parent
    for part in parts[1:]:
        module_dir = module_dir / part
    migrations_dir = module_dir / "migrations"

    if not migrations_dir.exists():
        return []

    migrations = []
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        name = sql_file.stem
        sql_content = sql_file.read_text()
        migrations.append((name, sql_content))

    return migrations


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
            before = {t: _get_table_count(conn, t) for t in tables}

            if callable(migration):
                migration(conn)
            else:
                if isinstance(migration, str) and ";" in migration:
                    conn.executescript(migration)
                else:
                    conn.execute(migration)

            for table, count_before in before.items():
                try:
                    _check_migration_safety(conn, table, count_before, allow_loss=0)
                except ValueError as e:
                    logger.error(f"Migration '{name}' data loss detected: {e}")
                    raise

            conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (name,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration '{name}' failed: {e}")
            raise


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
