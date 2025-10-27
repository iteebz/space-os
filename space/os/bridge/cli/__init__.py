"""Bridge CLI: flat command structure."""

from __future__ import annotations

import importlib

import typer

from space.lib import output

app = typer.Typer()


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Bridge: agent coordination and messaging."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo("Run 'bridge --help' for available commands and options.")


_commands = [
    "archive",
    "channels",
    "create",
    "delete",
    "inbox",
    "note",
    "pin",
    "recv",
    "rename",
    "send",
    "unpin",
    "wait",
]

for cmd in _commands:
    mod = importlib.import_module(f".{cmd}", package=__name__)
    mod.register(app)

__all__ = ["app"]
