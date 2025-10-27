import typer

from space.apps import canon, daemons
from space.apps.context.commands import context
from space.apps.council.commands import council
from space.apps.stats.commands import stats
from space.apps.system.commands import system
from space.lib import readme
from space.os import (
    bridge,
    knowledge,
    memory,
)
from space.os.spawn import commands as spawn_commands

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(bridge.app, name="bridge")
app.add_typer(spawn_commands.app, name="spawn")
app.add_typer(memory.app, name="memory")
app.add_typer(knowledge.app, name="knowledge")
app.add_typer(canon.app, name="canon")

app.add_typer(context, name="context")
app.add_typer(council, name="council")
app.add_typer(daemons.app, name="daemons")
app.add_typer(stats, name="stats")
app.add_typer(system, name="system")


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.invoked_subcommand is None:
        typer.echo(readme.root())


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
