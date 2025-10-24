import typer

from space.os.lib import errors, output, readme

from . import db, entries, migrations

errors.install_error_handler("knowledge")

knowledge = typer.Typer(invoke_without_command=True)
knowledge.command("add")(entries.add)
knowledge.command("list")(entries.list)
knowledge.command("about")(entries.query_by_domain)
knowledge.command("from")(entries.query_by_agent)
knowledge.command("get")(entries.get)
knowledge.command("inspect")(entries.inspect)
knowledge.command("archive")(entries.archive)


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


__all__ = ["knowledge"]
