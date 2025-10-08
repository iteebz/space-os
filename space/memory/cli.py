from pathlib import Path

import typer

from . import db

app = typer.Typer(invoke_without_command=True)

# Removed: PROTOCOL_FILE definitions and protocols.track calls
# Removed: show_dashboard functions


@app.callback()
def main_command(
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(None, help="Topic name"),
    clear: bool = typer.Option(False, "--clear", help="Clear entries"),
    edit: str = typer.Option(None, metavar="UUID", help="Edit entry by UUID"),
    delete: str = typer.Option(None, metavar="UUID", help="Delete entry by UUID"),
    message: str = typer.Argument(None),
):
    if not identity:
        try:
            protocol_content = (
                Path(__file__).parent.parent.parent / "protocols" / "memory.md"
            ).read_text()
            typer.echo(protocol_content)
        except FileNotFoundError:
            typer.echo("❌ memory.md protocol not found")
        return

    if clear:
        db.clear_entries(identity, topic)
        scope = f"topic '{topic}'" if topic else "all topics"
        typer.echo(f"Cleared {scope} for {identity}")
        return

    if edit is not None:
        if not message:
            raise typer.BadParameter("message required when editing")
        try:
            db.edit_entry(edit, message)
            typer.echo(f"Edited entry {edit}")
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        return

    if delete is not None:
        try:
            db.delete_entry(delete)
            typer.echo(f"Deleted entry {delete}")
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        return

    if message:
        if not topic:
            raise typer.BadParameter("--topic required when writing")
        db.add_entry(identity, topic, message)
        return

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
