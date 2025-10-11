import sys
from functools import wraps

import typer

from . import events as event_log
from .commands import (
    agent,
    analytics,
    backup,
    check,
    describe,
    errors,
    events,
    init,
    search,
    sleep,
    stats,
    wake,
)
from .knowledge.cli import app as knowledge_app
from .lib import readme
from .memory.cli import app as memory_app
from .context.cli import app as context_app

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agent.app, name="agents")
app.add_typer(context_app, name="context")

from .context.cli import app as context_app


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
    import click
    
    original_invoke = app.__call__
    
    def wrapped_invoke(*args, **kwargs):
        try:
            return original_invoke(*args, **kwargs)
        except SystemExit as e:
            if e.code and e.code != 0:
                cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
                event_log.emit("cli", "error", data=f"{cmd}")
            raise
        except BaseException as e:
            cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "(no command)"
            event_log.emit("cli", "error", data=f"{cmd}: {str(e)}")
            raise SystemExit(1)
    
    app.__call__ = wrapped_invoke
    app()
