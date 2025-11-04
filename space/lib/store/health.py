
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def check_backup_has_data(backup_path: Path, db_name: str, min_rows: int = 1) -> bool:
    """Check if backup database has data (excluding schema tables).

    Args:
        backup_path: Path to backup directory
        db_name: Database filename (e.g., 'space.db')
        min_rows: Minimum expected rows
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


def get_backup_stats(backup_path: Path, db_name: str) -> dict:
    """Get row counts for all tables in backup database."""
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


def compare_snapshots(before: dict, after: dict, threshold: float = 0.8) -> list[str]:
    """Find data loss between snapshots exceeding threshold (default 80%).

    Args:
        before: {'db_name': row_count, ...}
        after: {'db_name': row_count, ...}
        threshold: Max allowed loss fraction (0.8 = 80%)
    """
    warnings = []

    for db_name, before_count in before.items():
        after_count = after.get(db_name, 0)
        if before_count == 0:
            continue

        if after_count == 0:
            warnings.append(f"{db_name}: completely emptied ({before_count} → 0 rows)")
        else:
            loss_pct = (before_count - after_count) / before_count
            if loss_pct > threshold:
                warnings.append(
                    f"{db_name}: {loss_pct * 100:.0f}% data loss ({before_count} → {after_count} rows)"
                )

    return warnings
