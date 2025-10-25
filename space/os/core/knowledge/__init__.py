import typer

from space.os.lib import errors, output, readme

from . import api, db
from .commands.entries import app as entries_app

errors.install_error_handler("knowledge")

db.register()

knowledge = typer.Typer(invoke_without_command=True)
knowledge.add_typer(entries_app)


@knowledge.callback()
def main_command(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        typer.echo(readme.load("knowledge"))
        ctx.exit()

    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        typer.echo(readme.load("knowledge"))
    return


__all__ = ["knowledge", "api", "db"]
