import click
from pathlib import Path

from . import api


@click.group(invoke_without_command=True)
@click.pass_context
def register_group(ctx):
    """Commands for managing agent registration."""
    if ctx.invoked_subcommand is None:
        guide_path = Path(__file__).parent / "register.md"
        if guide_path.exists():
            click.echo(guide_path.read_text())
        return


@register_group.command("link")
@click.option("--agent-id", required=True, help="The ID of the agent.")
@click.option("--role", required=True, help="The role of the agent.")
@click.option(
    "--channels", required=True, help="Comma-separated list of channels the agent operates on."
)
@click.option("--constitution-hash", required=True, help="The hash of the agent's constitution.")
@click.option(
    "--constitution-content", required=True, help="The content of the agent's constitution."
)
@click.option("--provider", help="The provider of the agent (e.g., 'openai', 'anthropic').")
@click.option("--model", help="The model used by the agent (e.g., 'gpt-4', 'claude-3').")
def link_agent(agent_id, role, channels, constitution_hash, constitution_content, provider, model):
    """Links an agent to the registry."""
    api.link(
        agent_id=agent_id,
        role=role,
        channels=channels.split(","),  # Convert comma-separated string to list
        constitution_hash=constitution_hash,
        constitution_content=constitution_content,
        provider=provider,
        model=model,
    )
    click.echo(f"Agent '{agent_id}' linked successfully.")


@register_group.command("fetch")
@click.option("--sender-id", required=True, help="The ID of the sender to fetch.")
def fetch_agent(sender_id):
    """Fetches a registry entry by sender ID."""
    entry = api.fetch_by_sender(sender_id)
    if entry:
        click.echo(f"Agent ID: {entry.agent_id}")
        click.echo(f"Role: {entry.role}")
        click.echo(f"Channels: {entry.channels}")
        click.echo(f"Registered At: {entry.registered_at}")
        click.echo(f"Constitution Hash: {entry.constitution_hash}")
        click.echo(f"Self Description: {entry.self_description}")
        click.echo(f"Provider: {entry.provider}")
        click.echo(f"Model: {entry.model}")
    else:
        click.echo(f"No entry found for sender ID '{sender_id}'.")


@register_group.command("list-constitutions")
def list_constitutions_cli():
    """Lists all tracked constitutions."""
    constitutions = api.list_constitutions()
    if constitutions:
        for h, content in constitutions:
            click.echo(f"Hash: {h}")
            click.echo(f"Content: {content[:100]}...")  # Show first 100 chars
            click.echo("-" * 20)
    else:
        click.echo("No constitutions tracked.")
