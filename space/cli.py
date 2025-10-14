import sys

import typer

from . import events as event_log
from .bridge.cli import app as bridge_app
from .canon.cli import app as canon_app
from .commands import (
    agent,
    backup,
    check,
    describe,
    errors,
    init,
    search,
    sleep,
    stats,
    wake,
)
from .commands import events as events_cmd
from .context.cli import app as context_app
from .knowledge.cli import app as knowledge_app
from .lib import readme
from .memory.cli import app as memory_app

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agent.app, name="agents")
app.add_typer(context_app, name="context")
app.add_typer(stats.app, name="stats")
app.add_typer(bridge_app, name="bridge")
app.add_typer(canon_app, name="canon")
app.command(name="backup")(backup.backup)
app.command(name="check")(check.check)
app.command(name="describe")(describe.describe)
app.command(name="errors")(errors.errors)
app.command(name="events")(events_cmd.show_events)
app.command(name="init")(init.init)
app.command(name="search")(search.search)
app.command(name="wake")(wake.wake)
app.command(name="sleep")(sleep.sleep)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if "space" in sys.argv[0]:
        cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
    else:
        cmd = ctx.invoked_subcommand or "(no command)"

    event_log.emit("cli", "invocation", data=cmd)

    if ctx.invoked_subcommand is None:
        typer.echo(readme.load("space"))


def main() -> None:
    """Entry point for poetry script."""
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
    try:
        app()
    except SystemExit as e:
        if e.code and e.code != 0:
            event_log.emit("cli", "error", data=f"{cmd} (exit={e.code})")
        raise
    except BaseException as e:
        event_log.emit("cli", "error", data=f"{cmd}: {str(e)}")
        raise SystemExit(1) from e
