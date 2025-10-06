import click

from space.apps.memory.app import memory_app
from space.apps.bridge.app import bridge_app
from space.apps.spawn.app import spawn_app
from space.apps.backup.app import backup_app # Import backup_app
from space.apps.stats.app import stats_app # Import stats_app
from space.os.core.storage import Repo

from space.apps.spawn.app import spawn_app # Assuming a spawn app will exist

@click.group()
def cli():
    """Space CLI"""
    pass

@cli.group()
def db():
    """Database management commands."""
    pass

@db.command()
@click.argument("app_name")
def migrate(app_name: str):
    """Applies pending database migrations for a given app.

    APP_NAME: The name of the application to migrate (e.g., 'memory', 'knowledge').
    """
    click.echo(f"Applying migrations for app: {app_name}...")
    try:
        # Instantiating Repo triggers its __init__ which applies migrations
        Repo(app_name)
        click.echo(f"Migrations for {app_name} applied successfully.")
    except Exception as e:
        click.echo(f"Error applying migrations for {app_name}: {e}", err=True)
        raise click.Abort()

cli.add_command(memory_app.cli_group(), name="memory")
cli.add_command(bridge_app.cli_group(), name="bridge")

cli.add_command(backup_app.cli_group(), name="backup") # Add backup_app's cli_group
cli.add_command(stats_app.cli_group(), name="stats") # Add stats_app's cli_group
cli.add_command(spawn_app.cli_group(), name="spawn") # Assuming a spawn app will exist

if __name__ == '__main__':
    cli()