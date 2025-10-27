import typer

from space.apps.system import commands as system_commands

app = typer.Typer()


@app.command()
def health():
    """Verify space-os lattice integrity."""
    system_commands.health()
