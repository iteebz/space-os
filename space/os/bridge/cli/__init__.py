"""Bridge CLI: thin command wrappers delegating to ops layer."""

import typer

from space.lib import output

from . import channels, messages, notes

app = typer.Typer()


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Manage channels, messages, and notes."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo("Run 'bridge --help' for available commands and options.")


app.add_typer(channels.app, name="channels")
app.add_typer(messages.app, name="messages")
app.add_typer(notes.app, name="notes")

__all__ = ["app"]
