import typer

from space.commands.backup import backup
from space.commands.context import context
from space.commands.council import council
from space.commands.events import events
from space.commands.health import health
from space.commands.init import init
from space.commands.launch import launch
from space.commands.sleep import sleep
from space.commands.stats import stats
from space.commands.wake import wake
from space.core import (
    bridge,
    knowledge,
    memory,
    spawn,
)
from space.lib import readme

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(bridge.app, name="bridge")
app.add_typer(spawn.app, name="spawn")
app.add_typer(memory.app, name="memory")
app.add_typer(knowledge.app, name="knowledge")

app.add_typer(context, name="context")
app.add_typer(council, name="council")
app.add_typer(stats, name="stats")

app.add_typer(sleep, name="sleep")
app.command()(wake)
app.command()(launch)
app.command()(backup)
app.command()(health)
app.command()(init)
app.command()(events)


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
