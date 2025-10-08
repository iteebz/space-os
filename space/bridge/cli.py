"""Bridge CLI - Clean command interface."""

from pathlib import Path

import typer

from ..lib import protocols
from .commands.channels import app as channels_app
from .commands.messages import app as messages_app
from .commands.messages import export as messages_export
from .commands.monitor import app as monitor_app

app = typer.Typer(invoke_without_command=True)

PROTOCOL_FILE = Path(__file__).parent.parent.parent / "protocols" / "bridge.md"


@app.callback()
def main_command(ctx: typer.Context):
    """Bridge: AI Coordination Protocol"""
    if ctx.invoked_subcommand is None:
        try:
            typer.echo(protocols.load("bridge"))
        except FileNotFoundError:
            typer.echo("❌ bridge.md protocol not found")


app.add_typer(channels_app, name="channels")
app.add_typer(messages_app, name="messages")
app.add_typer(monitor_app, name="monitor")


@app.command("export")
def export_channel(channel: str):
    """Export channel transcript (legacy alias for `bridge messages export`)."""
    messages_export(channel)


if __name__ == "__main__":
    app()
