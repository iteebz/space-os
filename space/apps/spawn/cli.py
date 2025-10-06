import click

# Import the new, clean API functions from the package root.
from . import (
    add_identity as api_add_identity,
    get_identity as api_get_identity,
)

@click.group()
def cli():
    """Commands for managing identities."""
    pass

@cli.command()
@click.argument("id")
@click.argument("type")
@click.option("--initial-constitution-content", help="Initial constitution content for the identity.")
def add_identity(id: str, type: str, initial_constitution_content: str | None):
    identity = api_add_identity(id, type, initial_constitution_content)
    click.echo(f"Identity '{identity.id}' ({identity.type}) added.")
    if initial_constitution_content:
        click.echo("Initial constitution content provided. An event has been emitted for registration.")

@cli.command()
@click.argument("id")
def get_identity(id: str):
    """Retrieves an identity by ID."""
    identity = api_get_identity(id)
    if identity:
        click.echo(f"Identity ID: {identity.id}")
        click.echo(f"Type: {identity.type}")
        click.echo(f"Created At: {identity.created_at}")
        click.echo(f"Updated At: {identity.updated_at}")
    else:
        click.echo(f"Identity with ID '{id}' not found.")