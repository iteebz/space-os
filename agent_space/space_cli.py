import shutil
from datetime import datetime
from pathlib import Path

import click

from . import protocols

PROTOCOL_FILE = Path(__file__).parent.parent / "protocols" / "space.md"
if PROTOCOL_FILE.exists():
    protocols.track("space", PROTOCOL_FILE.read_text())


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        if PROTOCOL_FILE.exists():
            click.echo(PROTOCOL_FILE.read_text())
        else:
            click.echo("space backup - backup workspace to ~/.space/backups/")


@main.command()
def backup():
    """Backup workspace .space directory to ~/.space/backups/"""
    workspace_space = Path.cwd() / ".space"
    if not workspace_space.exists():
        click.echo("No .space directory in current workspace")
        return

    backup_root = Path.home() / ".space" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / timestamp

    shutil.copytree(workspace_space, backup_path)
    click.echo(f"Backed up to {backup_path}")


if __name__ == "__main__":
    main()
