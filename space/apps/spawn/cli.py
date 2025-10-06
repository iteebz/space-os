import click

from . import api

@click.group()
def spawn_group():
    """Commands for spawning and managing agents."""
    pass

@spawn_group.command("spawn")
@click.argument("agent_id")
@click.option("--role", required=True, help="The role of the agent.")
@click.option("--channels", required=True, help="Comma-separated list of channels the agent operates on.")
@click.option("--constitution-hash", required=True, help="The hash of the agent's constitution.")
@click.option("--provider", help="The provider of the agent (e.g., 'openai', 'anthropic').")
@click.option("--model", help="The model used by the agent (e.g., 'gpt-4', 'claude-3').")
def spawn_agent(agent_id, role, channels, constitution_hash, provider, model):
    """Spawns an agent and registers it with the system."""
    api.spawn(
        agent_id=agent_id,
        role=role,
        channels=channels.split(","),
        constitution_hash=constitution_hash,
        provider=provider,
        model=model,
    )
    click.echo(f"Agent '{agent_id}' spawned and registered successfully.")