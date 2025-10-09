import typer

from .commands import agents, backup, events, search, stats, trace
from .handover.cli import app as handover_app
from .knowledge.cli import app as knowledge_app
from .lib import lattice
from .memory.cli import app as memory_app

app = typer.Typer(invoke_without_command=True)

app.add_typer(handover_app, name="handover")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agents.app, name="agents")

app.command()(backup.backup)
app.command(name="events")(events.show_events)
app.command()(stats.stats)
app.command()(search.search)
app.command()(trace.trace)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        try:
            typer.echo(lattice.load("## Orientation"))
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ Orientation section not found in README: {e}")


def main() -> None:
    """Entry point for poetry script."""
    app()
