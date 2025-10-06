import click
from datetime import datetime

# Import the module-level setter from api.py
from .api import _set_spawn_app_instance, spawn_app_instance # Assuming api.py will expose this

@click.group()
def spawn_group(): # Renamed from register_group
    """Commands for managing identities and their constitutions."""
@spawn_group.command()
@click.argument("id")
@click.argument("type")
@click.option("--initial-constitution-content", help="Initial constitution content for the identity.")
def add_identity(id: str, type: str, initial_constitution_content: str | None):
    if not spawn_app_instance:
        click.echo("Spawn app instance not set.")
        return

    repo = spawn_app_instance.repositories["spawn"]
    identity = repo.add_identity(id, type, initial_constitution_content)
    click.echo(f"Identity '{identity.id}' ({identity.type}) added.")
    if identity.current_constitution_id:
        click.echo(f"Initial constitution registered: {identity.current_constitution_id}")

@spawn_group.command()
@click.argument("id")
def get_identity(id: str):
    """Retrieves an identity by ID."""
    if not spawn_app_instance:
        click.echo("Spawn app instance not set.")
        return

    repo = spawn_app_instance.repositories["spawn"]
    identity = repo.get_identity(id)
    if identity:
        click.echo(f"Identity ID: {identity.id}")
        click.echo(f"Type: {identity.type}")
        click.echo(f"Current Constitution ID: {identity.current_constitution_id}")
        click.echo(f"Created At: {identity.created_at}")
        click.echo(f"Updated At: {identity.updated_at}")
    else:
        click.echo(f"Identity with ID '{id}' not found.")

@spawn_group.command()
@click.argument("identity_id")
@click.argument("name")
@click.argument("content")
@click.option("--change-description", help="Description of the changes in this constitution version.")
@click.option("--created-by", default="user", help="Identifier of the entity creating this version.")
def add_constitution_version(identity_id: str, name: str, content: str, change_description: str | None, created_by: str):
    """Adds a new version of a constitution for an identity."""
    if not spawn_app_instance:
        click.echo("Spawn app instance not set.")
        return

    repo = spawn_app_instance.repositories["spawn"]
    constitution = repo.add_constitution_version(
        name=name,
        content=content,
        identity_id=identity_id,
        change_description=change_description,
        created_by=created_by,
    )
    click.echo(f"Constitution version '{constitution.id}' added for identity '{identity_id}'.")
    click.echo(f"Version: {constitution.version}")

@spawn_group.command()
@click.argument("identity_id")
def get_current_constitution(identity_id: str):
    """Retrieves the current constitution for an identity."""
    if not spawn_app_instance:
        click.echo("Spawn app instance not set.")
        return

    repo = spawn_app_instance.repositories["spawn"]
    constitution = repo.get_current_constitution_for_identity(identity_id)
    if constitution:
        click.echo(f"Current Constitution ID: {constitution.id}")
        click.echo(f"Name: {constitution.name}")
        click.echo(f"Version: {constitution.version}")
        click.echo(f"Content:\n{constitution.content}")
        click.echo(f"Created By: {constitution.created_by}")
        click.echo(f"Change Description: {constitution.change_description}")
    else:
        click.echo(f"No current constitution found for identity '{identity_id}'.")

@spawn_group.command()
@click.argument("identity_id")
def list_constitution_history(identity_id: str):
    """Lists the history of constitutions for an identity."""
    if not spawn_app_instance:
        click.echo("Spawn app instance not set.")
        return

    repo = spawn_app_instance.repositories["spawn"]
    history = repo.get_constitution_history_for_identity(identity_id)
    if history:
        for const in history:
            click.echo(f"- ID: {const.id}, Name: {const.name}, Version: {const.version}, Created: {const.created_at}")
    else:
        click.echo(f"No constitution history found for identity '{identity_id}'.")