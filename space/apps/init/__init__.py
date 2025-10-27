import typer

from space.apps.system import commands as system_commands

app = typer.Typer()


@app.command()
def init():
    """Initialize space workspace structure and databases."""
    system_commands.init()
