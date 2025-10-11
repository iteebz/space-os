import typer

from .commands import agent, analytics, backup, context, describe, events, init, search, sleep, stats, wake
from .knowledge.cli import app as knowledge_app
from .lib import readme
from .memory.cli import app as memory_app

app = typer.Typer(invoke_without_command=True)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agent.app, name="agents")

app.command()(wake.wake)
app.command()(sleep.sleep)
app.command()(backup.backup)
app.command()(init.init)
app.command(name="events")(events.show_events)
app.command()(stats.stats)
app.command()(analytics.analytics)
app.command()(search.search)
app.command()(context.context)
app.command()(describe.describe)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.invoked_subcommand is None:
        typer.echo(readme.load("space"))
        typer.echo("\n")
        stats.stats()


def main() -> None:
    """Entry point for poetry script."""
    app()
