"""Bridge CLI: Main entry point wiring all commands."""

import json

import typer

from space.os.lib import output, readme

from . import channels, messages, notes, export
from .. import spawning

errors = __import__("space.os.lib.errors", fromlist=["install_error_handler"])
errors.install_error_handler("bridge")

bridge = typer.Typer(invoke_without_command=True, add_help_option=False)

bridge.add_typer(channels.app, name="channels", help="Channel commands")
bridge.add_typer(messages.app, help="Message commands")
bridge.add_typer(notes.app, help="Notes commands")
bridge.add_typer(export.app, help="Export commands")


@bridge.callback()
def main_callback(
    ctx: typer.Context,
    agent_id: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    """Bridge: AI Coordination Protocol"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        _show_readme(ctx.obj)
        ctx.exit()

    if ctx.invoked_subcommand is None:
        if agent_id:
            ctx.invoke(messages.inbox, identity=agent_id)
        else:
            _show_readme(ctx.obj)


def _show_readme(ctx_obj: dict):
    content = readme.load("bridge")
    if content:
        typer.echo(content)
    else:
        output.out_text("BRIDGE: AI Coordination Protocol", ctx_obj)


def main() -> None:
    """Entry point for poetry script."""
    bridge()
