import contextlib
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import typer

from space.lib import paths, store
from space.lib.store.sqlite import resolve

logger = logging.getLogger(__name__)

app = typer.Typer()


def _backup_data_snapshot(timestamp: str, quiet_output: bool) -> dict:
    src = paths.dot_space()
    if not src.exists():
        if not quiet_output:
            typer.echo("No .space directory found")
        return {}

    backup_path = paths.backup_snapshot(timestamp)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.mkdir(parents=True, exist_ok=True)

    store.close_all()

    with contextlib.suppress(sqlite3.DatabaseError):
        resolve(src)

    for db_file in src.glob("*.db"):
        shutil.copy2(db_file, backup_path / db_file.name)

    stats = _get_backup_stats(backup_path)

    for db_file in backup_path.glob("*.db"):
        try:
            with sqlite3.connect(str(db_file), timeout=2) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok":
                    logger.error(f"Backup integrity check failed for {db_file.name}: {result}")
        except Exception as e:
            logger.error(f"Failed to verify backup {db_file.name}: {e}")

    os.chmod(backup_path, 0o555)

    return stats


def _backup_sessions(quiet_output: bool) -> dict:
    from space.lib import providers

    src = paths.sessions_dir()
    backup_path = paths.backup_sessions_dir()

    def count_provider_files(path: Path, provider: str) -> int:
        provider_dir = path / provider
        if not provider_dir.exists():
            return 0
        return len(list(provider_dir.glob("*.jsonl")))

    before = {p: count_provider_files(backup_path, p) for p in providers.PROVIDER_NAMES}

    if backup_path.exists():
        os.chmod(backup_path, 0o755)

    backup_path.mkdir(parents=True, exist_ok=True)

    if src.exists():
        for provider_dir in src.iterdir():
            if not provider_dir.is_dir():
                continue

            backup_provider_dir = backup_path / provider_dir.name
            backup_provider_dir.mkdir(exist_ok=True)

            for session_file in provider_dir.iterdir():
                if not session_file.is_file():
                    continue

                backup_file = backup_provider_dir / session_file.name
                shutil.copy2(session_file, backup_file)

    os.chmod(backup_path, 0o555)

    after = {p: count_provider_files(backup_path, p) for p in providers.PROVIDER_NAMES}
    return {
        "before": before,
        "after": after,
        "added": {p: after[p] - before[p] for p in providers.PROVIDER_NAMES},
    }


def _get_backup_stats(backup_path: Path) -> dict:
    stats = {}
    for db_file in backup_path.glob("*.db"):
        try:
            db_file.chmod(0o644)
            with sqlite3.connect(str(db_file), timeout=2, check_same_thread=False) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name != '_migrations'"
                )
                tables = [row[0] for row in cursor.fetchall()]

                total = (
                    sum(
                        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        for table in tables
                    )
                    if tables
                    else 0
                )

                stats[db_file.name] = {
                    "tables": len(tables),
                    "rows": total,
                }
        except sqlite3.DatabaseError as e:
            logger.debug(f"Could not read stats from {db_file.name}: {e}")
            stats[db_file.name] = {"tables": 0, "rows": 0}

    return stats


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _do_backup(quiet_output=False)


@app.command()
def backup(
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup ~/.space/data and ~/.space/sessions to ~/.space_backups/.

    Data backups are immutable and timestamped: ~/.space_backups/data/{timestamp}/
    Session backups mirror structure: ~/.space_backups/sessions/{provider}/*.jsonl (additive)
    """
    _do_backup(quiet_output)


def _do_backup(quiet_output: bool = False):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_stats = _backup_data_snapshot(timestamp, quiet_output)
    session_stats = _backup_sessions(quiet_output)

    if not quiet_output:
        typer.echo(f"✓ Data: {paths.backup_snapshot(timestamp)}")
        for db, info in data_stats.items():
            if "error" in info:
                typer.echo(f"  {db}: {info['error']}")
            else:
                typer.echo(f"  {db}: {info['tables']} tables, {info['rows']} rows")

        added = session_stats.get("added", {})
        total_added = sum(added.values())
        typer.echo(f"✓ Sessions: +{total_added} files")


def main() -> None:
    """Entry point for poetry script."""
    app()
