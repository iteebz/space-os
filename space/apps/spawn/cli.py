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
@click.option("--constitution-file", required=True, type=click.Path(exists=True, dir_okay=False), help="Path to the agent's constitution file.")
@click.option("--provider", required=True, help="The AI provider to use for the agent.")
@click.option("--model", required=True, help="The AI model to use for the agent.")
def spawn_agent(agent_id, role, channels, constitution_file, provider, model):
    """Spawns an agent and registers it with the system."""
    with open(constitution_file, "r") as f:
        constitution_content = f.read()

    api.spawn(
        agent_id=agent_id,
        role=role,
        channels=channels.split(","),
        constitution_content=constitution_content,
        provider=provider,
        model=model,
    )
    click.echo(f"Agent '{agent_id}' spawned and registered successfully.")