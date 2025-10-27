"""Agent list command."""

import json

import typer

from space.apps.stats import agent_stats
from space.os.spawn import api


def list_agents(
    show_all: bool = typer.Option(False, "--all", help="Show archived agents"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all agents (registered and orphaned across universe)."""
    stats = agent_stats(show_all=show_all) or []

    if not stats:
        if json_output:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No agents found.")
        return

    if json_output:
        agents_data = []
        for s in sorted(stats, key=lambda a: a.identity or ""):
            agent_id = s.agent_id
            if not agent_id:
                continue
            name = s.identity or ""
            if len(name) == 36 and name.count("-") == 4:
                agent = api.get_agent(name)
                if agent:
                    name = agent.identity
            agent = api.get_agent(agent_id)
            agents_data.append(
                {
                    "identity": name,
                    "agent_id": agent_id,
                    "model": agent.model if agent and agent.model else "-",
                    "description": agent.description if agent and agent.description else "-",
                }
            )
        typer.echo(json.dumps(agents_data))
    else:
        typer.echo(f"{'IDENTITY':<20} {'AGENT_ID':<10} {'MODEL':<25} {'DESCRIPTION'}")

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
            model = agent.model if agent and agent.model else "-"
            desc = agent.description if agent and agent.description else "-"

            typer.echo(f"{name:<20} {short_id:<10} {model:<25} {desc}")

        typer.echo()
        typer.echo(f"Total: {len(stats)}")
