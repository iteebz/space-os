"""Create immutable backups that never get touched by recovery scripts."""

import shutil
import json
from datetime import datetime
from pathlib import Path

import typer

from space.os.lib import paths


def archive(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Create immutable archive snapshot (never auto-recovered from).
    
    Archives are meant for disaster recovery and manual inspection.
    They are NOT touched by recovery.py or backup.py processes.
    """

    data_dir = paths.space_data()
    if not data_dir.exists():
        if not quiet_output:
            typer.echo("No .space directory found")
        raise typer.Exit(code=1)

    archive_root = data_dir / "archives"
    archive_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = archive_root / timestamp

    shutil.copytree(
        data_dir,
        archive_path,
        dirs_exist_ok=False,
        ignore=shutil.ignore_patterns("backups", "archives", "*.db-shm", "*.db-wal"),
    )

    manifest = {
        "timestamp": timestamp,
        "archived_at": datetime.now().isoformat(),
        "source": str(data_dir),
        "description": "Immutable snapshot. NEVER auto-recovered from. Manual recovery only.",
    }
    manifest_path = archive_path / ".manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    if json_output:
        typer.echo(json.dumps({"archive_path": str(archive_path), "manifest": manifest}))
    elif not quiet_output:
        typer.echo(f"✓ Archived to {archive_path}")
        typer.echo(f"  Manifest: {manifest_path}")
