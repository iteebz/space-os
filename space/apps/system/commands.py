import contextlib
import json
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import typer

from space.lib import paths, store
from space.os import spawn
from space.os.spawn.api import symlinks

logger = logging.getLogger(__name__)

system = typer.Typer(invoke_without_command=True)

ORPHAN_CHECKS = [
    ("spawn.db", "tasks", "agent_id", "agents", "agent_id"),
    ("bridge.db", "messages", "channel_id", "channels", "channel_id"),
    ("bridge.db", "notes", "channel_id", "channels", "channel_id"),
    ("bridge.db", "bookmarks", "channel_id", "channels", "channel_id"),
    ("memory.db", "memories", "agent_id", None, None),
    ("knowledge.db", "knowledge", "agent_id", None, None),
]

DEFS = {
    "spawn.db": ["constitutions", "agents", "tasks"],
    "bridge.db": ["channels", "messages", "notes", "bookmarks"],
    "memory.db": ["memories", "links"],
    "knowledge.db": ["knowledge"],
}


def _copytree_exclude_chats(src: Path, dst: Path) -> None:
    """Copy tree excluding chats.db + WAL artifacts (queryable from provider dirs, not backed up)."""

    def ignore(directory: str, contents: list) -> set:
        excluded = set()
        if "chats.db" in contents:
            excluded.add("chats.db")
            excluded.add("chats.db-shm")
            excluded.add("chats.db-wal")
        return excluded

    shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=False)


def _backup_data_snapshot(timestamp: str, quiet_output: bool) -> dict:
    """Backup ~/.space/data to timestamped snapshot."""
    src = paths.space_data()
    if not src.exists():
        if not quiet_output:
            typer.echo("No data directory found")
        return {}

    backup_path = paths.backup_snapshot(timestamp)
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    if not paths.validate_backup_path(backup_path):
        typer.echo("ERROR: Backup path validation failed (possible path traversal)", err=True)
        raise typer.Exit(code=1)

    store.close_all()
    shutil.copytree(src, backup_path, dirs_exist_ok=False)
    os.chmod(backup_path, 0o555)

    return _get_backup_stats(backup_path)


def _backup_chats_latest(quiet_output: bool) -> None:
    """Backup ~/.space/chats to ~/.space_backups/chats/latest (overwrites)."""
    src = paths.chats_dir()
    if not src.exists():
        return

    backup_path = paths.backup_chats_latest()
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    if not paths.validate_backup_path(backup_path):
        typer.echo("ERROR: Backup path validation failed (possible path traversal)", err=True)
        raise typer.Exit(code=1)

    if backup_path.exists():
        shutil.rmtree(backup_path)

    shutil.copytree(src, backup_path, dirs_exist_ok=False)
    os.chmod(backup_path, 0o555)


def _check_orphans() -> list[str]:
    """Check for orphaned references across DBs."""
    issues = []
    registry_map = {
        "spawn.db": "spawn",
        "bridge.db": "bridge",
        "memory.db": "memory",
        "knowledge.db": "knowledge",
    }

    for src_db, src_table, src_col, ref_db, ref_col in ORPHAN_CHECKS:
        db_path = paths.space_data() / src_db
        if not db_path.exists():
            continue
        if ref_db and not (paths.space_data() / ref_db).exists():
            continue

        registry_name = registry_map.get(src_db)
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


def _check_db(db_name: str, tables: list[str]) -> tuple[bool, list[str], dict]:
    """Check single DB. Return (healthy, issues, counts)."""
    issues = []
    db_path = paths.space_data() / db_name

    if not db_path.exists():
        issues.append(f"❌ {db_name} missing")
        return False, issues, {}

    registry_map = {
        "spawn.db": "spawn",
        "bridge.db": "bridge",
        "memory.db": "memory",
        "knowledge.db": "knowledge",
    }
    registry_name = registry_map.get(db_name)
    if not registry_name:
        issues.append(f"❌ {db_name}: unknown database")
        return False, issues, {}

    try:
        with store.ensure(registry_name) as conn:
            # Schema check
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


def _get_backup_stats(backup_path: Path) -> dict:
    """Get row counts for all databases in backup."""
    stats = {}
    for db_file in backup_path.glob("*.db"):
        if db_file.name == "cogency.db":
            continue
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != '_migrations'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            total = (
                sum(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables)
                if tables
                else 0
            )

            stats[db_file.name] = {
                "tables": len(tables),
                "rows": total,
            }
            conn.close()
        except sqlite3.DatabaseError:
            stats[db_file.name] = {"error": "corrupted"}

    return stats


def _show_backup_stats(backup_stats: dict) -> None:
    """Display backup statistics."""
    typer.echo("\nBackup stats:")
    typer.echo("  Database               Tables  Rows")
    typer.echo("  " + "─" * 40)

    for db_name in sorted(backup_stats.keys()):
        stats = backup_stats[db_name]
        if "error" in stats:
            typer.echo(f"  {db_name:22} error")
        else:
            tables = stats.get("tables", "?")
            rows = stats.get("rows", "?")
            typer.echo(f"  {db_name:22} {tables:6}  {rows}")


def archive_old_config():
    """Archive old provider config files with .old suffix."""
    old_configs = [
        Path.home() / ".claude" / "CLAUDE.md",
        Path.home() / ".gemini" / "GEMINI.md",
        Path.home() / ".codex" / "AGENTS.md",
    ]

    for old_path in old_configs:
        if old_path.exists():
            timestamp = int(time.time())
            new_path = old_path.parent / f"{old_path.stem}.{timestamp}.old"
            old_path.rename(new_path)
            typer.echo(f"✓ Archived {old_path.name} → {new_path.name}")


def init_default_agents():
    """Auto-discover and register agents from canon/constitutions/.

    Agents are created with identity matching constitution filename (without .md).
    """
    constitutions_dir = paths.canon_path() / "constitutions"
    if not constitutions_dir.exists():
        return

    constitution_files = sorted(constitutions_dir.glob("*.md"))
    if not constitution_files:
        return

    with spawn.db.connect():
        for const_file in constitution_files:
            identity = const_file.stem
            constitution = const_file.name

            with contextlib.suppress(ValueError):
                spawn.register_agent(identity, "claude-haiku-4-5", constitution)


@system.command()
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


@system.command()
def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup ~/.space/data and ~/.space/chats to ~/.space_backups/.

    Data backups are immutable and timestamped: ~/.space_backups/data/{timestamp}/
    Chat backups are latest-only: ~/.space_backups/chats/latest/ (overwrites)
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_stats = _backup_data_snapshot(timestamp, quiet_output)
    _backup_chats_latest(quiet_output)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "data_backup": str(paths.backup_snapshot(timestamp)),
                    "chats_backup": str(paths.backup_chats_latest()),
                    "stats": backup_stats,
                }
            )
        )
    elif not quiet_output:
        typer.echo(f"✓ Backed up data to {paths.backup_snapshot(timestamp)}")
        typer.echo(f"✓ Backed up chats to {paths.backup_chats_latest()}")
        if backup_stats:
            _show_backup_stats(backup_stats)


@system.command()
def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.space_data().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
    constitutions_dir = paths.canon_path() / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    chats_dir = paths.chats_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)
    for cli in ["claude", "codex", "gemini"]:
        (chats_dir / cli).mkdir(exist_ok=True)

    spawn.db.register()

    with spawn.db.connect():
        pass
    with store.ensure("bridge"):
        pass
    with store.ensure("memory"):
        pass
    with store.ensure("knowledge"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")

    archive_old_config()
    init_default_agents()

    bin_dir = Path.home() / ".local" / "bin"
    launch_script = paths.package_root().parent / "bin" / "launch"
    if launch_script.exists():
        bin_dir.mkdir(parents=True, exist_ok=True)
        if symlinks._setup_launch_symlink(launch_script):
            typer.echo("✓ Agent launcher configured (~/.local/bin/launch)")

    typer.echo()
    typer.echo("  ~/space/")
    typer.echo("    ├── canon/      → your persistent context (edit here)")
    typer.echo("    └── (code)")
    typer.echo()
    typer.echo("  ~/.space/")
    typer.echo("    ├── data/       → runtime databases")
    typer.echo("    └── chats/      → chat history")
    typer.echo()
    typer.echo("  ~/.space_backups/")
    typer.echo("    ├── data/{timestamp}/ → immutable data snapshots")
    typer.echo("    └── chats/latest/     → latest chat backup (overwrites)")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  space wake --as <identity>")


def main() -> None:
    """Entry point for poetry script."""
    system()
