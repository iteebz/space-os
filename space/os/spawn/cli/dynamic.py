"""Dynamic agent launcher: routes command name to spawn if registered."""

import sys
from typing import NoReturn

import click

from space.os.spawn import api


def dispatch_agent_from_name() -> NoReturn:
    """Entry point: route command name (argv[0]) to agent if registered."""
    prog_name = sys.argv[0].split("/")[-1]

    agent = api.get_agent(prog_name)
    if not agent:
        click.echo(f"Error: '{prog_name}' is not a registered agent identity.", err=True)
        click.echo("Run 'spawn agents' to list available agents.", err=True)
        sys.exit(1)

    args = sys.argv[1:] if len(sys.argv) > 1 else []
    api.spawn_agent(agent.identity, extra_args=args)
    sys.exit(0)
