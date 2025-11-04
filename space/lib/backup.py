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
        backup(quiet_output=False)


def _backup_data_snapshot(timestamp: str, quiet_output: bool) -> dict:
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


def _backup_sessions(quiet_output: bool) -> dict:
    src = paths.sessions_dir()
    backup_path = paths.backup_sessions_dir()

    def count_provider_files(path: Path, provider: str) -> int:
        """Count JSONL files for a provider."""
        provider_dir = path / provider
        if not provider_dir.exists():
            return 0
        return len(list(provider_dir.glob("*.jsonl")))

    before = {p: count_provider_files(backup_path, p) for p in ["claude", "codex", "gemini"]}

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

    after = {p: count_provider_files(backup_path, p) for p in ["claude", "codex", "gemini"]}
    return {
        "before": before,
        "after": after,
        "added": {p: after[p] - before[p] for p in ["claude", "codex", "gemini"]},
    }


def _get_backup_stats(backup_path: Path) -> dict:
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _backup_data_snapshot(timestamp, quiet_output)
    session_stats = _backup_sessions(quiet_output)

    if not quiet_output:
        providers = ["claude", "codex", "gemini"]
        after = session_stats.get("after", {})
        counts = ", ".join(f"{p} ({after.get(p, 0)})" for p in providers)
        typer.echo(f"✓ Data: {paths.backup_snapshot(timestamp)}")
        typer.echo(f"✓ Sessions: {counts}")


def main() -> None:
    """Entry point for poetry script."""
    app()
