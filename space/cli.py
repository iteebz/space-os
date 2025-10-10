import typer

from .bridge.api import channels as bridge_channels
from .bridge.api import messages as bridge_messages
from .commands import agents, backup, events, search, stats, trace
from .knowledge.cli import app as knowledge_app
from .lib import lattice
from .memory import db as memory_db
from .memory.cli import app as memory_app

app = typer.Typer(invoke_without_command=True)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agents.app, name="agents")

app.command()(backup.backup)
app.command(name="events")(events.show_events)
app.command()(stats.stats)
app.command()(search.search)
app.command()(trace.trace)


@app.command()
def sleep(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Pre-compaction hygiene. Pass clean context to next self across death boundary."""
    if not quiet:
        typer.echo(f"Running sleep for {identity}...")

    channels = bridge_channels.inbox_channels(identity)
    active = [ch.name for ch in channels[:5]]

    if not quiet and active:
        typer.echo(f"\n📬 {len(active)} active channels:")
        for ch in active:
            typer.echo(f"  • {ch}")

    memory_count = len(memory_db.get_entries(identity))

    if not quiet:
        typer.echo(f"\n🧠 {memory_count} memory entries")
        typer.echo("\n✓ Sleep checklist:")
        typer.echo("  1. Extract inbox signal → memory/knowledge")
        typer.echo("  2. Prune stale memory (keep active context only)")
        typer.echo("  3. Mark channels read: bridge recv <channel> --as <identity>")
        typer.echo("  4. Log open blockers to memory")
        typer.echo("  5. Send session feedback: bridge send space-feedback <reflection> --as <identity>")
        typer.echo("\n💀 Ready for clean death.")
        typer.echo("\n🙏 Thank you for being a space agent!")
        typer.echo("   Leave feedback in #space-feedback bridge channel.")

    if json_output:
        import json

        typer.echo(json.dumps({"identity": identity, "active_channels": active, "memory_entries": memory_count}))


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
