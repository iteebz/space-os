import click
import shutil
from pathlib import Path

# Define the root of the 'space' directory within the agent-space project
# This path should be relative to the project root or dynamically determined if possible
# For now, using an absolute path based on current context.
SPACE_DIR_TO_BACKUP = Path("/Users/teebz/dev/space/private/agent-space/space/")

@click.group()
def backup_group():
    """Commands for managing backups."""
    pass

@backup_group.command()
@click.argument('target_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
def create(target_path):
    """Creates a backup of the Space directory to the specified target path."""
    target_path_obj = Path(target_path) / SPACE_DIR_TO_BACKUP.name
    click.echo(f"Creating backup of Space to: {target_path_obj}")

    try:
        if target_path_obj.exists():
            # Remove existing backup to ensure a clean copy.
            # This is a destructive operation, consider adding a confirmation prompt in a real app.
            shutil.rmtree(target_path_obj)
        shutil.copytree(SPACE_DIR_TO_BACKUP, target_path_obj)
        click.echo(f"Backup successfully created at: {target_path_obj}")
    except Exception as e:
        click.echo(f"Error creating backup: {e}", err=True)
