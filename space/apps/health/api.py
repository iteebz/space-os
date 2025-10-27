import logging
import sqlite3

from space.lib import paths, store

logger = logging.getLogger(__name__)

REGISTRY_MAP = {
    "spawn.db": "spawn",
    "bridge.db": "bridge",
    "memory.db": "memory",
    "knowledge.db": "knowledge",
}

ORPHAN_CHECKS = [
    ("spawn.db", "tasks", "agent_id", "agents", "agent_id"),
    ("bridge.db", "messages", "channel_id", "channels", "channel_id"),
    ("bridge.db", "notes", "channel_id", "channels", "channel_id"),
    ("bridge.db", "bookmarks", "channel_id", "channels", "channel_id"),
    ("memory.db", "memories", "agent_id", None, None),
    ("knowledge.db", "agent_id", "knowledge", None, None),
]

DB_DEFINITIONS = {
    "spawn.db": ["constitutions", "agents", "tasks"],
    "bridge.db": ["channels", "messages", "notes", "bookmarks"],
    "memory.db": ["memories", "links"],
    "knowledge.db": ["knowledge"],
}


def check_orphans() -> list[str]:
    """Check for orphaned references across DBs."""
    issues = []

    for src_db, src_table, src_col, ref_db, ref_col in ORPHAN_CHECKS:
        db_path = paths.space_data() / src_db
        if not db_path.exists():
            continue
        if ref_db and not (paths.space_data() / ref_db).exists():
            continue

        registry_name = REGISTRY_MAP.get(src_db)
        if not registry_name:
            continue

        ref_table = ref_db.split(".")[0] if ref_db else None
        if not ref_table:
            continue

        try:
            with store.ensure(registry_name) as conn:
                query = f"""
                SELECT COUNT(*) FROM {src_table}
                WHERE {src_col} IS NOT NULL
                AND {src_col} NOT IN (SELECT {ref_col} FROM {ref_table} WHERE {ref_col} IS NOT NULL)
                """
                orphans = conn.execute(query).fetchone()[0]
                if orphans > 0:
                    issues.append(f"❌ {src_db}::{src_table}.{src_col}: {orphans} orphaned")
        except sqlite3.Error as e:
            issues.append(f"❌ {src_db}: orphan check failed: {e}")

    return issues


def check_db(db_name: str, tables: list[str]) -> tuple[bool, list[str], dict]:
    """Check single DB. Return (healthy, issues, counts)."""
    issues = []
    db_path = paths.space_data() / db_name

    if not db_path.exists():
        issues.append(f"❌ {db_name} missing")
        return False, issues, {}

    registry_name = REGISTRY_MAP.get(db_name)
    if not registry_name:
        issues.append(f"❌ {db_name}: unknown database")
        return False, issues, {}

    try:
        with store.ensure(registry_name) as conn:
            actual = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }

            missing = set(tables) - actual
            ignored = {"_migrations", "sqlite_sequence", "instructions"}
            extra = actual - set(tables) - ignored
            if missing:
                issues.append(f"❌ {db_name}: missing tables {missing}")
            if extra:
                issues.append(f"⚠️  {db_name}: unexpected tables {extra}")

            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                issues.append(f"❌ {db_name}: corruption")

            counts = {}
            for tbl in tables:
                if tbl in actual:
                    count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    counts[tbl] = count

            return not issues, issues, counts
    except sqlite3.Error as e:
        issues.append(f"❌ {db_name}: {e}")
        return False, issues, {}


def run_all_checks() -> tuple[list[str], dict]:
    """Run all health checks and return issues and counts."""
    all_issues = []
    all_counts = {}

    for db_name, tables in DB_DEFINITIONS.items():
        ok, db_issues, counts = check_db(db_name, tables)
        if not ok:
            all_issues.extend(db_issues)
        else:
            all_counts[db_name] = counts

    orphan_issues = check_orphans()
    if orphan_issues:
        all_issues.extend(orphan_issues)

    return all_issues, all_counts
