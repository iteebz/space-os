"""Agent list command."""

import typer

from space.apps.stats import agent_stats
from space.core.spawn import api


def list_agents(show_all: bool = typer.Option(False, "--all", help="Show archived agents")):
    """List all agents (registered and orphaned across universe)."""
    stats = agent_stats(show_all=show_all) or []

    if not stats:
        typer.echo("No agents found.")
        return

    typer.echo(f"{'IDENTITY':<20} {'AGENT_ID':<10} {'S-B-M-K':<20} {'DESCRIPTION'}")
    typer.echo("-" * 100)

    for s in sorted(stats, key=lambda a: a.identity or ""):
        name = s.identity or ""
        agent_id = s.agent_id
        if not agent_id:
            continue
        short_id = agent_id[:8]

        if len(name) == 36 and name.count("-") == 4:
            agent = api.get_agent(name)
            if agent:
                name = agent.identity

        agent = api.get_agent(agent_id)
        desc = agent.description if agent and agent.description else "-"
        sbmk = f"{s.spawns}-{s.msgs}-{s.mems}-{s.knowledge}"

        typer.echo(f"{name:<20} {short_id:<10} {sbmk:<20} {desc}")

    typer.echo()
    typer.echo(f"Total: {len(stats)}")
