import sys

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
from space.commands.wake import wake
from space.os import bridge, chats, knowledge, memory, spawn
from space.os.lib import readme
from space.os.lib.aliasing import Aliasing
from space.os.lib.invocation import Invocation
from space.os.core.spawn.commands.agents import app as agents_app
from space.os.core.spawn.commands.registry import app as registry_app

app = typer.Typer(invoke_without_command=True, no_args_is_help=False, add_help_option=False)

app.add_typer(knowledge, name="knowledge")
app.add_typer(memory, name="memory")
app.add_typer(agents_app, name="agents")
app.add_typer(context, name="context")
app.add_typer(stats, name="stats")
app.add_typer(registry_app, name="registry")
app.add_typer(bridge, name="bridge")
app.add_typer(spawn, name="spawn")
app.add_typer(chats.app, name="chats")

app.command(name="backup")(backup)
app.command(name="council")(council)
app.command(name="events")(events)
app.command(name="health")(health)
app.command(name="init")(init)
app.command(name="launch")(launch)
app.command(name="wake")(wake)
app.command(name="sleep")(sleep)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    invocation = ctx.obj
    if not invocation:
        invocation = Invocation.from_args(sys.argv[1:])
        ctx.obj = invocation
    cmd = ctx.invoked_subcommand or "(no command)"
    if invocation:
        invocation.emit_invocation(cmd)

    if help:
        typer.echo(readme.root())
        ctx.exit()

    if ctx.invoked_subcommand is None:
        typer.echo(readme.root())


def main() -> None:
    """Entry point for poetry script."""
    argv_orig = sys.argv[1:]
    rewritten_argv = Aliasing.rewrite(argv_orig)
    sys.argv = [sys.argv[0]] + rewritten_argv

    invocation = Invocation.from_args(rewritten_argv)

    try:
        app(obj=invocation)
    except SystemExit as e:
        if e.code and e.code != 0:
            invocation.emit_error(f"CLI command (exit={e.code})")
        raise
    except BaseException as e:
        invocation.emit_error(f"CLI command: {str(e)}")
        raise SystemExit(1) from e
