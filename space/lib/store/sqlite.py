import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def connect(db_path: Path) -> sqlite3.Connection:
    """Connect to SQLite with write contention monitoring.

    Uses WAL mode + 5s busy timeout to handle concurrent writes.
    SQLite write ceiling: ~1000 writes/sec on SSD.
    """
    start = time.perf_counter()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")  # 5s timeout for lock contention

    elapsed = time.perf_counter() - start
    if elapsed > 0.1:
        logger.warning(f"SQLite connection took {elapsed:.3f}s (possible lock contention)")

    return conn


def resolve(db_dir: Path) -> None:
    """Merge WAL data into main DB files for backup/transfer.

    Args:
        db_dir: Directory containing *.db files
    """
    for db_file in sorted(db_dir.glob("*.db")):
        try:
            conn = connect(db_file)
            conn.execute("PRAGMA wal_checkpoint(RESTART)")
            conn.close()

            logger.info(f"Resolved {db_file.name}")
        except sqlite3.DatabaseError as e:
            logger.warning(f"Failed to resolve {db_file.name}: {e}")
