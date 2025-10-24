import sqlite3

import typer

from space.os import db
from space.os.lib import paths

app = typer.Typer(invoke_without_command=True)

ORPHAN_CHECKS = [
    ("spawn.db", "tasks", "identity", "agents", "name"),
    ("bridge.db", "tasks", "channel_id", "channels", "id"),
    ("bridge.db", "messages", "channel_id", "channels", "id"),
    ("bridge.db", "notes", "channel_id", "channels", "id"),
    ("bridge.db", "bookmarks", "channel_id", "channels", "id"),
    ("memory.db", "memories", "agent_id", None, None),
    ("knowledge.db", "knowledge", "agent_id", None, None),
]

DEFS = {
    "spawn.db": ["constitutions", "agents", "tasks"],
    "bridge.db": ["channels", "messages", "notes", "bookmarks"],
    "memory.db": ["memories", "memory_links"],
    "knowledge.db": ["knowledge"],
    "events.db": ["events"],
}


def _check_orphans() -> list[str]:
    """Check for orphaned references across DBs."""
    issues = []
    spawn_db_path = paths.dot_space() / "spawn.db"
    bridge_db_path = paths.dot_space() / "bridge.db"
    memory_db_path = paths.dot_space() / "memory.db"
    knowledge_db_path = paths.dot_space() / "knowledge.db"

    db_conns = {}
    if spawn_db_path.exists():
        db_conns["spawn.db"] = db.connect(spawn_db_path)
    if bridge_db_path.exists():
        db_conns["bridge.db"] = db.connect(bridge_db_path)
    if memory_db_path.exists():
        db_conns["memory.db"] = db.connect(memory_db_path)
    if knowledge_db_path.exists():
        db_conns["knowledge.db"] = db.connect(knowledge_db_path)

    try:
        for src_db, src_table, src_col, ref_db, ref_col in ORPHAN_CHECKS:
            if src_db not in db_conns or ref_db not in db_conns:
                continue

            src_conn = db_conns[src_db]
            ref_table = ref_db.split(".")[0]

            query = f"""
            SELECT COUNT(*) FROM {src_table}
            WHERE {src_col} IS NOT NULL
            AND {src_col} NOT IN (SELECT {ref_col} FROM {ref_table} WHERE {ref_col} IS NOT NULL)
            """

            orphans = src_conn.execute(query).fetchone()[0]

            if orphans > 0:
                issues.append(f"❌ {src_db}::{src_table}.{src_col}: {orphans} orphaned")
    finally:
        for conn in db_conns.values():
            conn.close()

    return issues


def _check_db(db_name: str, tables: list[str]) -> tuple[bool, list[str], dict]:
    """Check single DB. Return (healthy, issues, counts)."""
    issues = []
    db_path = paths.dot_space() / db_name

    if not db_path.exists():
        issues.append(f"❌ {db_name} missing")
        return False, issues, {}

    try:
        with db.connect(db_path) as conn:
            # Schema check
            actual = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }

            missing = set(tables) - actual
            ignored = {"_migrations", "sqlite_sequence", "instructions"}
            extra = actual - set(tables) - ignored
            if missing:
                issues.append(f"❌ {db_name}: missing tables {missing}")
            if extra:
                issues.append(f"⚠️  {db_name}: unexpected tables {extra}")

            # Integrity check
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                issues.append(f"❌ {db_name}: corruption")

            # Row counts
            counts = {}
            for tbl in tables:
                if tbl in actual:
                    count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    counts[tbl] = count

            return not issues, issues, counts
    except sqlite3.Error as e:
        issues.append(f"❌ {db_name}: {e}")
        return False, issues, {}


@app.callback(invoke_without_command=True)
def health():
    """Verify space-os lattice integrity."""
    issues = []

    for db_name, tables in DEFS.items():
        ok, db_issues, counts = _check_db(db_name, tables)
        if not ok:
            issues.extend(db_issues)
        else:
            for tbl, cnt in counts.items():
                typer.echo(f"✓ {db_name}::{tbl} ({cnt} rows)")

    orphan_issues = _check_orphans()
    if orphan_issues:
        issues.extend(orphan_issues)

    if issues:
        for issue in issues:
            typer.echo(issue)
        raise typer.Exit(1)

    typer.echo("\n✓ Space infrastructure healthy")
