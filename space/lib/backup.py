import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import typer

from space.lib import paths, store

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(backup)


def _backup_data_snapshot(timestamp: str, quiet_output: bool) -> dict:
    """Backup ~/.space/data to timestamped snapshot."""
    src = paths.space_data()
    if not src.exists():
        if not quiet_output:
            typer.echo("No data directory found")
        return {}

    backup_path = paths.backup_snapshot(timestamp)
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    store.close_all()
    store.resolve(src)
    shutil.copytree(src, backup_path, dirs_exist_ok=False)
    os.chmod(backup_path, 0o555)

    return _get_backup_stats(backup_path)


def _backup_sessions_latest(quiet_output: bool) -> None:
    """Backup ~/.space/sessions to ~/.space_backups/sessions (mirrored structure, additive)."""
    src = paths.sessions_dir()
    if not src.exists():
        return

    backup_path = paths.backup_sessions_dir()
    backup_path.mkdir(parents=True, exist_ok=True)

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


def _get_backup_stats(backup_path: Path) -> dict:
    """Get row counts for all databases in backup."""
    stats = {}
    for db_file in backup_path.glob("*.db"):
        if db_file.name == "cogency.db":
            continue
        try:
            with sqlite3.connect(db_file) as conn:
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
        except sqlite3.DatabaseError:
            stats[db_file.name] = {"error": "corrupted"}

    return stats


def _format_backup_stats(backup_stats: dict) -> str:
    """Format backup statistics for display."""
    lines = ["\nBackup stats:", "  Database               Tables  Rows", "  " + "─" * 40]
    for db_name in sorted(backup_stats.keys()):
        stats = backup_stats[db_name]
        if "error" in stats:
            lines.append(f"  {db_name:22} error")
        else:
            tables = stats.get("tables", "?")
            rows = stats.get("rows", "?")
            lines.append(f"  {db_name:22} {tables:6}  {rows}")
    return "\n".join(lines)


@app.command()
def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup ~/.space/data and ~/.space/sessions to ~/.space_backups/.

    Data backups are immutable and timestamped: ~/.space_backups/data/{timestamp}/
    Session backups mirror structure: ~/.space_backups/sessions/{provider}/*.jsonl (additive)
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_stats = _backup_data_snapshot(timestamp, quiet_output)
    _backup_sessions_latest(quiet_output)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "data_backup": str(paths.backup_snapshot(timestamp)),
                    "sessions_backup": str(paths.backup_sessions_dir()),
                    "stats": backup_stats,
                }
            )
        )
    elif not quiet_output:
        typer.echo(f"✓ Backed up data to {paths.backup_snapshot(timestamp)}")
        typer.echo(f"✓ Backed up sessions to {paths.backup_sessions_dir()}")
        if backup_stats:
            typer.echo(_format_backup_stats(backup_stats))


def main() -> None:
    """Entry point for poetry script."""
    app()
