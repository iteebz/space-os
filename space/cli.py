import click

from space.apps.memory import cli as memory_cli
from space.apps.spawn.cli import cli as spawn_cli

@click.group()
def cli():
    """Space CLI"""
    pass

# Add the refactored app CLIs. They are discovered and registered by convention.
cli.add_command(memory_cli)
cli.add_command(spawn_cli)

# TODO: Refactor and add other apps (bridge, backup, stats)
# following the new, simplified convention.

if __name__ == '__main__':
    cli()
