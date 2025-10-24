import sys

import typer

from space.apps.context.app import app as context_app
from space.apps.council.app import council
from space.apps.stats.app import app as stats_app
from space.commands import (
    archive,
    backup,
    check,
    health,
    init,
    sleep,
    wake,
)
from space.commands import events as events_cmd
from space.os import chats
from space.os.bridge.app import app as bridge_app
from space.os.knowledge.app import app as knowledge_app
from space.os.lib import readme
from space.os.lib.aliasing import Aliasing
from space.os.lib.invocation import Invocation
from space.os.memory.app import app as memory_app
from space.os.spawn.commands.agents import app as agents_app
from space.os.spawn.commands.registry import app as registry_app

app = typer.Typer(invoke_without_command=True, no_args_is_help=False, add_help_option=False)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agents_app, name="agents")
app.add_typer(context_app, name="context")
app.add_typer(stats_app, name="stats")
app.add_typer(registry_app, name="registry")
app.add_typer(bridge_app, name="bridge")
app.add_typer(chats.app, name="chats")

app.command(name="archive")(archive.archive)
app.command(name="backup")(backup.backup)
app.command(name="check")(check.check)
app.command(name="council")(council)
app.command(name="events")(events_cmd.show_events)
app.command(name="health")(health.health)
app.command(name="init")(init.init)
app.command(name="wake")(wake.wake)
app.command(name="sleep")(sleep.sleep)


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
