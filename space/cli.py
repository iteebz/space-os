import typer

from .commands import backup, context, describe, events, init, search, sleep, stats, trace, wake
from .knowledge.cli import app as knowledge_app
from .lib import readme
from .memory.cli import app as memory_app

app = typer.Typer(invoke_without_command=True)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")

app.command()(wake.wake)
app.command()(sleep.sleep)
app.command()(backup.backup)
app.command()(init.init)
app.command(name="events")(events.show_events)
app.command()(stats.stats)
app.command()(search.search)
app.command()(trace.trace)
app.command()(context.context)
app.command()(describe.describe)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        try:
            typer.echo(readme.load("space"))
            typer.echo("\n")
            stats.stats()
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ space README not found: {e}")


def main() -> None:
    """Entry point for poetry script."""
    app()
