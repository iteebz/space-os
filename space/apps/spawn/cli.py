import click

from . import (
    add_identity,
    get_identity,
    add_constitution,
    update_identity_current_constitution,
)

@click.group()
def cli():
    """Spawn primitive - agent identity and constitution management."""
    pass

@cli.command("add-identity")
@click.argument("identity_id")
@click.option("--type", default="agent", help="Type of identity (e.g., agent, human).")
@click.option("--constitution", help="Initial constitution content for the identity.")
def add_identity_command(identity_id: str, type: str, constitution: str | None):
    """Add a new identity."""
    identity = add_identity(identity_id, type, constitution)
    click.echo(f"Identity {identity.id} ({identity.type}) added.")

@cli.command("get-identity")
@click.argument("identity_id")
def get_identity_command(identity_id: str):
    """Get details of an identity."""
    identity = get_identity(identity_id)
    if identity:
        click.echo(f"ID: {identity.id}")
        click.echo(f"Type: {identity.type}")
        click.echo(f"Created At: {identity.created_at_iso}")
        click.echo(f"Updated At: {identity.updated_at_iso}")
        if identity.current_constitution_id:
            click.echo(f"Current Constitution ID: {identity.current_constitution_id}")
    else:
        click.echo(f"Identity {identity_id} not found.")

@cli.command("add-constitution")
@click.argument("identity_id")
@click.argument("name")
@click.argument("version")
@click.argument("content")
@click.option("--created-by", default="human", help="Who created this constitution.")
@click.option("--change-description", default="Initial creation", help="Description of the change.")
@click.option("--previous-version-id", help="ID of the previous constitution version.")
def add_constitution_command(
    identity_id: str,
    name: str,
    version: str,
    content: str,
    created_by: str,
    change_description: str,
    previous_version_id: str | None,
):
    """Add a new constitution version for an identity."""
    constitution = add_constitution(
        name, version, content, identity_id, created_by, change_description, previous_version_id
    )
    click.echo(f"Constitution {constitution.id} added for identity {identity_id}.")

@cli.command("update-current-constitution")
@click.argument("identity_id")
@click.argument("constitution_id")
def update_current_constitution_command(identity_id: str, constitution_id: str):
    """Update the current constitution for an identity."""
    update_identity_current_constitution(identity_id, constitution_id)
    click.echo(f"Identity {identity_id} current constitution updated to {constitution_id}.")
