from __future__ import annotations

import logging
import sqlite3

from space.lib import paths, store

logger = logging.getLogger(__name__)

DB_NAME = "space.db"
REGISTRY = "space"
EXPECTED_TABLES = {
    "agents",
    "sessions",
    "channels",
    "messages",
    "bookmarks",
    "memories",
    "knowledge",
    "chats",
}
IGNORED_TABLES = {"sqlite_sequence", "_migrations"}


def _database_exists() -> bool:
    return (paths.space_data() / DB_NAME).exists()


def _check_foreign_keys(conn: sqlite3.Connection) -> list[str]:
    """Run PRAGMA foreign_key_check and format issues."""
    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    issues = []
    for row in fk_rows:
        table = row["table"]
        rowid = row["rowid"]
        parent = row["parent"]
        issues.append(f"❌ {table} row {rowid} violates FK to {parent}")
    return issues


def check_db() -> tuple[bool, list[str], dict[str, int]]:
    """Validate schema integrity and return (healthy, issues, counts)."""
    issues: list[str] = []
    counts: dict[str, int] = {}

    if not _database_exists():
        issues.append(f"❌ {DB_NAME} missing")
        return False, issues, counts

    try:
        with store.ensure(REGISTRY) as conn:
            actual_tables = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            missing = EXPECTED_TABLES - actual_tables
            extra = actual_tables - EXPECTED_TABLES - IGNORED_TABLES
            if missing:
                issues.append(f"❌ {DB_NAME}: missing tables {sorted(missing)}")
            if extra:
                issues.append(f"⚠️  {DB_NAME}: unexpected tables {sorted(extra)}")

            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                issues.append(f"❌ {DB_NAME}: integrity_check={integrity}")

            fk_issues = _check_foreign_keys(conn)
            issues.extend(fk_issues)

            for table in sorted(EXPECTED_TABLES & actual_tables):
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    except sqlite3.Error as exc:
        issues.append(f"❌ {DB_NAME}: {exc}")
        return False, issues, counts

    return not issues, issues, counts


def run_all_checks() -> tuple[list[str], dict[str, dict[str, int]]]:
    """Run health checks for consumers expecting legacy signature."""
    ok, issues, counts = check_db()
    summaries = {DB_NAME: counts} if ok else {}
    return issues, summaries
