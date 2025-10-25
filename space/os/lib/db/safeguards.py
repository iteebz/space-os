"""Migration and backup safeguards to prevent data loss."""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class MigrationSafeguard:
    """Ensures migrations don't silently lose data."""

    def __init__(self, conn: sqlite3.Connection, table: str):
        self.conn = conn
        self.table = table
        self.before_count = self._get_count()

    def _get_count(self) -> int:
        """Get row count for table, returns 0 if table doesn't exist."""
        try:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                (self.table,),
            )
            if not cursor.fetchone()[0]:
                return 0
            result = self.conn.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()
            return result[0] if result else 0
        except sqlite3.OperationalError:
            return 0

    def after(self, allow_loss: int = 0) -> bool:
        """Verify row count after migration.

        Args:
            allow_loss: Max rows permitted to be lost (e.g., duplicates removed)

        Returns:
            True if safe, raises ValueError if data loss detected
        """
        after_count = self._get_count()
        lost = self.before_count - after_count

        if lost > allow_loss:
            msg = f"Migration {self.table}: {lost} rows lost (before: {self.before_count}, after: {after_count})"
            logger.error(msg)
            raise ValueError(msg)

        if lost > 0:
            logger.warning(
                f"Migration {self.table}: {lost} rows removed (expected for allow_loss={allow_loss})"
            )
        else:
            logger.info(f"Migration {self.table}: safe (count unchanged: {after_count})")

        return True


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
