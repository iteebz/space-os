import typer

from . import describe, inspect, list, manage

app = typer.Typer(invoke_without_command=True)
app.add_typer(list.app, name="list")
app.add_typer(inspect.app, name="inspect")
app.add_typer(manage.app)
app.add_typer(describe.app, name="describe")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show archived agents"),
):
    if ctx.invoked_subcommand is None:
        list.list_agents(show_all=show_all)
