import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import typer

from space.lib import paths, sqlite, store

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(backup)


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
    sqlite.resolve(src)
    shutil.copytree(src, backup_path, dirs_exist_ok=False)
    os.chmod(backup_path, 0o555)

    return _get_backup_stats(backup_path)


def _backup_chats_latest(quiet_output: bool) -> None:
    """Backup ~/.space/chats to ~/.space_backups/chats/latest (append-only, never deletes)."""
    src = paths.chats_dir()
    if not src.exists():
        return

    backup_path = paths.backup_chats_latest()
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    if not paths.validate_backup_path(backup_path):
        typer.echo("ERROR: Backup path validation failed (possible path traversal)", err=True)
        raise typer.Exit(code=1)

    backup_path.mkdir(parents=True, exist_ok=True)

    for provider_dir in src.iterdir():
        if not provider_dir.is_dir():
            continue
        
        backup_provider_dir = backup_path / provider_dir.name
        backup_provider_dir.mkdir(exist_ok=True)
        
        for chat_file in provider_dir.rglob("*"):
            if not chat_file.is_file():
                continue
            
            rel_path = chat_file.relative_to(provider_dir)
            backup_file = backup_provider_dir / rel_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            if not backup_file.exists() or chat_file.stat().st_mtime > backup_file.stat().st_mtime:
                shutil.copy2(chat_file, backup_file)
    
    os.chmod(backup_path, 0o555)


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


@app.command()
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


def main() -> None:
    """Entry point for poetry script."""
    app()
