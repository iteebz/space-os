import sys

import typer

from space import events, readme
from space.lib.invocation import AliasResolver, InvocationContext

from .bridge.app import app as bridge_app
from .commands import (
    agent,
    backup,
    check,
    describe,
    errors,
    init,
    registry,
    search,
    sleep,
    stats,
    wake,
)
from .commands import events as events_cmd
from .context.app import app as context_app
from .knowledge.app import app as knowledge_app
from .memory.app import app as memory_app

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agent.app, name="agents")
app.add_typer(context_app, name="context")
app.add_typer(stats.app, name="stats")
app.add_typer(registry.app, name="registry")
app.add_typer(bridge_app, name="bridge")

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
    invocation = AliasResolver.resolve(sys.argv[1:])
    ctx.obj = invocation

    cmd = ctx.invoked_subcommand or "(no command)"
    invocation.emit_invocation(cmd)

    if ctx.invoked_subcommand is None:
        typer.echo(readme.root())


def main() -> None:
    """Entry point for poetry script."""
    argv_orig = sys.argv[1:]
    normalized_argv = AliasResolver.normalize_args(argv_orig)
    sys.argv = [sys.argv[0]] + normalized_argv
    
    try:
        app()
    except SystemExit as e:
        if e.code and e.code != 0:
            invocation = AliasResolver.resolve(argv_orig)
            invocation.emit_error(f"CLI command (exit={e.code})")
        raise
    except BaseException as e:
        invocation = AliasResolver.resolve(argv_orig)
        invocation.emit_error(f"CLI command: {str(e)}")
        raise SystemExit(1) from e
