"""Knowledge commands: CLI parsing & typer wiring."""

import typer

from space.lib import output, readme

app = typer.Typer(invoke_without_command=True)

from . import entries  # noqa: E402


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    """Knowledge: Domain-specific Knowledge Base"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        typer.echo(readme.load("knowledge"))
        ctx.exit()

    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        typer.echo(readme.load("knowledge"))


def __getattr__(name):
    if name == "entries":
        from . import entries

        return entries
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["entries", "app"]
