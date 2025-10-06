import click
from .api import add_memory, get_all_memories

@click.group(name="memory")
def cli():
    """Memory primitive - a simple, file-based memory store."""
    pass

@cli.command("add")
@click.option("--identity", required=True, help="Identity of the memory's author.")
@click.option("--topic", required=True, help="Topic of the memory.")
@click.argument("message")
def add(identity: str, topic: str, message: str):
    """Add a new memory to the store."""
    add_memory(identity, topic, message)
    click.echo("Memory added.")

@cli.command("list")
def list_memories():
    """List all memories."""
    memories = get_all_memories()
    if not memories:
        click.echo("No memories found.")
        return

    for mem in memories:
        click.echo(f"[{mem.uuid[-8:]}] [{mem.timestamp}] [{mem.identity}/{mem.topic}] {mem.message}")