"""Sleep journal command: structured continuity capture."""

import typer

from space.core import memory, spawn
from space.lib import errors

errors.install_error_handler("journal")


def journal(
    ctx: typer.Context,
    entry: str = typer.Argument(None, help="Journal entry text"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Emit or view sleep journal entries.

    Usage:
      sleep journal --as hailot "completed X, moving to Y"  # add entry
      sleep journal --as hailot                             # show last entry
      sleep journal --as hailot --list                      # show all entries
    """
    identity = ctx.obj["identity"]
    if not identity:
        typer.echo("Identity must be provided with --as")
        raise typer.Exit(1)

    agent = spawn.resolve_agent(identity)
    if not agent:
        if not quiet:
            typer.echo(f"No agent found for {identity}")
        return
    agent_id = agent.agent_id

    if entry:
        _add_entry(identity, agent_id, entry, quiet)
    else:
        _show_last_entry(identity, quiet)


def _add_entry(identity: str, agent_id: str, text: str, quiet: bool):
    """Add a new journal entry and link to previous."""
    journal_id = memory.add_entry(agent_id, topic="journal", message=text, source="journal")

    prev_entries = memory.list_entries(identity, topic="journal", limit=2)
    if len(prev_entries) > 1:
        prev_id = prev_entries[1].memory_id
        memory.add_link(journal_id, prev_id, kind="supersedes")

    if not quiet:
        typer.echo(f"📔 Journal entry saved ({journal_id[-8:]})")


def _show_last_entry(identity: str, quiet: bool):
    """Show last journal entry."""
    entries = memory.list_entries(identity, topic="journal", limit=1)
    if not entries:
        if not quiet:
            typer.echo(f"No journal entries for {identity}")
        return

    e = entries[0]
    typer.echo(f"📔 Last journal ({e.memory_id[-8:]})")
    typer.echo(f"   {e.timestamp}")
    typer.echo()
    typer.echo(f"   {e.message}")
    typer.echo()

    chain = memory.get_chain(e.memory_id)
    if chain["predecessors"]:
        typer.echo(f"   Previous: {chain['predecessors'][0].memory_id[-8:]}")
