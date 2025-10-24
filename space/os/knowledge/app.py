import typer

from space.os.lib import errors, readme

from . import entries

errors.install_error_handler("knowledge")

app = typer.Typer(invoke_without_command=True)
app.command("add")(entries.add)
app.command("list")(entries.list)
app.command("about")(entries.query_by_domain)
app.command("from")(entries.query_by_agent)
app.command("get")(entries.get)
app.command("inspect")(entries.inspect)
app.command("archive")(entries.archive)


@app.callback()
def main_command(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    from space.os.lib import output

    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        typer.echo(readme.load("knowledge"))
        ctx.exit()

    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        typer.echo(readme.load("knowledge"))
    return


__all__ = ["app"]
