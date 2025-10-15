import json
import shutil
from datetime import datetime

import typer

from ..lib import paths


def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Backup the app data directory (~/space/.space) to ~/.space/backups/"""

    workspace_space = paths.dot_space()
    if not workspace_space.exists():
        if not quiet_output:
            typer.echo("No .space directory in current workspace")
        raise typer.Exit(code=1)

    global_root = paths.global_root()
    backup_root_dir = global_root / "backups"
    backup_root_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root_dir / timestamp

    shutil.copytree(workspace_space, backup_path)
    if json_output:
        typer.echo(json.dumps({"backup_path": str(backup_path)}))
    elif not quiet_output:
        typer.echo(f"Backed up to {backup_path}")
