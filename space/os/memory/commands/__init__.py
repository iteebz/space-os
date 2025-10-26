"""Memory commands."""

import typer

from space.lib import errors, output, readme

errors.install_error_handler("memory")

app = typer.Typer(invoke_without_command=True)

from . import entries, journal  # noqa: E402


@app.callback()
def main_callback(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    topic: str = typer.Option(None, "--topic", help="Filter by topic"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Memory: Knowledge Base Management"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["identity"] = identity
    ctx.obj["topic"] = topic

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if identity:
            entries._list_entries(identity, ctx, show_all=show_all, topic=topic)
        else:
            typer.echo(readme.load("memory"))


def __getattr__(name):
    if name == "entries":
        from . import entries

        return entries
    if name == "journal":
        from . import journal

        return journal
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["entries", "journal", "app"]
