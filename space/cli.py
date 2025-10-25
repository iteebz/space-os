import typer

from space.apps.context.app import context
from space.apps.council.app import council
from space.apps.stats.app import stats
from space.commands.backup import backup
from space.commands.events import events
from space.commands.health import health
from space.commands.init import init
from space.commands.launch import launch
from space.commands.sleep import sleep
from space.commands.sleep_journal import sleep_journal
from space.commands.wake import wake
from space.os import (
    bridge_app,
    knowledge_app,
    memory_app,
    spawn_app,
)
from space.os.lib import readme

app = typer.Typer(invoke_without_command=True, no_args_is_help=False, add_help_option=False)

app.add_typer(bridge_app, name="bridge")
app.add_typer(spawn_app, name="spawn")
app.add_typer(memory_app, name="memory")
app.add_typer(knowledge_app, name="knowledge")

app.add_typer(context, name="context")
app.add_typer(council, name="council")
app.add_typer(stats, name="stats")

app.command()(wake)
app.command()(sleep)
app.command()(sleep_journal)
app.command()(launch)
app.command()(backup)
app.command()(health)
app.command()(init)
app.command()(events)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    if help:
        typer.echo(readme.root())
        ctx.exit()

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
