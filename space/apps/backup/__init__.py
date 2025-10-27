import typer

from space.apps.system import commands as system_commands

app = typer.Typer()


@app.command()
def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup ~/.space/data and ~/.space/chats to ~/.space_backups/."""
    system_commands.backup(json_output, quiet_output)
