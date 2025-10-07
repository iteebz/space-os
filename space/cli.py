import click

from space.apps.memory import cli as memory_cli
from space.apps.spawn.cli import cli as spawn_cli
from space.apps.example.cli import example_group
from space.apps.knowledge.cli import knowledge_group
from space.apps.backup.cli import backup_group
from space.apps.stats.cli import stats_group

@click.group()
def cli():
    """Space CLI"""
    pass

# Add the refactored app CLIs. They are discovered and registered by convention.
cli.add_command(memory_cli)
cli.add_command(spawn_cli)
cli.add_command(example_group)
cli.add_command(knowledge_group)
cli.add_command(backup_group)
cli.add_command(stats_group)

# TODO: Refactor and add other apps (bridge, backup, stats)
# following the new, simplified convention.

if __name__ == '__main__':
    cli()
