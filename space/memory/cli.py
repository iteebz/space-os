import typer

from . import db
from ..lib import protocols

app = typer.Typer(invoke_without_command=True)

# Removed: PROTOCOL_FILE definitions and protocols.track calls
# Removed: show_dashboard functions


@app.callback()
def main_command(
    identity: str = typer.Option(None, "--as", help="Identity name"),
):
    if not identity:
        try:
            protocol_content = protocols.load("memory")
            typer.echo(protocol_content)
        except FileNotFoundError:
            typer.echo("❌ memory.md protocol not found")
        return


@app.command("add")
def add_entry_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(..., help="Topic name"),
    message: str = typer.Argument(..., help="The memory message"),
):
    """Add a new memory entry."""
    db.add_entry(identity, topic, message)
    typer.echo(f"Added memory for {identity} on topic {topic}")


@app.command("edit")
def edit_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Edit an existing memory entry."""
    try:
        db.edit_entry(uuid, message)
        typer.echo(f"Edited entry {uuid}")
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


@app.command("delete")
def delete_entry_command(
    uuid: str = typer.Argument(..., help="UUID of the entry to delete"),
):
    """Delete a memory entry."""
    try:
        db.delete_entry(uuid)
        typer.echo(f"Deleted entry {uuid}")
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


@app.command("clear")
def clear_entries_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
):
    """Clear memory entries for an identity and optional topic."""
    db.clear_entries(identity, topic)
    scope = f"topic '{topic}'" if topic else "all topics"
    typer.echo(f"Cleared {scope} for {identity}")


@app.command("list")
def list_entries_command(
    identity: str = typer.Option(..., "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
):
    """List memory entries for an identity and optional topic."""
    entries = db.get_entries(identity, topic)
    if not entries:
        scope = f"topic '{topic}'" if topic else "all topics"
        typer.echo(f"No entries found for {identity} in {scope}")
        return

    current_topic = None
    for e in entries:
        if e.topic != current_topic:
            if current_topic is not None:
                typer.echo()
            typer.echo(f"# {e.topic}")
            current_topic = e.topic
        typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {e.message}")


if __name__ == "__main__":
    app()
