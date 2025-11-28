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
    last_error: sqlite3.OperationalError | None = None

    for attempt in range(5):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = None

        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")  # 5s timeout for lock contention
            conn.execute("PRAGMA journal_mode = WAL")
            break
        except sqlite3.OperationalError as err:
            last_error = err
            conn.close()
            if "locked" in str(err).lower() and attempt < 4:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise
    else:
        # Defensive: should never hit because loop either breaks or raises
        raise last_error or sqlite3.OperationalError("Failed to initialize SQLite connection")

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
