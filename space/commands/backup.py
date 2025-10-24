import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import typer

from space.os import db
from space.os.lib import paths

logger = logging.getLogger(__name__)


def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup ~/.space/data to ~/.space/backups/ (immutable, timestamped)"""

    src = paths.space_data()
    if not src.exists():
        if not quiet_output:
            typer.echo("No data directory found")
        raise typer.Exit(code=1)

    backup_dir = paths.backups_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = paths.backup_snapshot(timestamp)

    if not paths.validate_backup_path(backup_path):
        typer.echo("ERROR: Backup path validation failed (possible path traversal)", err=True)
        raise typer.Exit(code=1)

    db.resolve(src)
    shutil.copytree(src, backup_path, dirs_exist_ok=False)
    db.resolve(backup_path)

    os.chmod(backup_path, 0o555)

    backup_stats = _get_backup_stats(backup_path)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "backup_path": str(backup_path),
                    "stats": backup_stats,
                }
            )
        )
    elif not quiet_output:
        typer.echo(f"✓ Backed up to {backup_path}")
        _show_backup_stats(backup_stats)


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
