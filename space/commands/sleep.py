"""Sleep command: context handoff ritual."""

import typer

from space.commands.journal import journal
from space.lib import errors

errors.install_error_handler("sleep")

JOURNAL_PROMPT = """Consolidate session state before death. Quality sleep = prepared spawn.

**Capture:**
- Compress the last journal and this session's activities into a new, consolidated journal.
- Preserve valuable mental models or architectural insights as separate, focused memories.
- What shipped this session
- Active threads mid-execution
- Blockers, non-obvious state
- Architectural patterns discovered
- What next spawn inherits

**Memory operations:**
memory add --as <you> --topic journal "<synthesis>"
memory replace <uuid> "<refined-understanding>"     # evolve existing memories
memory archive <uuid>                                # retire noise

**Anti-pattern:** Accumulating raw session dumps without synthesis.
**Pattern:** Each spawn refines understanding. Replace > add. Archive > delete.

**Quality bar:**
- Architectural insight over feature logs
- Patterns over implementation details
- What future-you needs, not what past-you did
- Terse technical language
- Zero ceremony

Sleep well = wake sharp."""

sleep = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=True,
    add_help_option=False,
    help="Prepare for death. Hand off context to your next self.",
)

sleep.command("journal")(journal)


@sleep.callback(invoke_without_command=True)
def sleep_callback(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    check: bool = typer.Option(False, "--check", help="Preview sleep without persisting changes."),
):
    """Prepare for death. Hand off context to your next self."""
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["identity"] = identity

    if ctx.invoked_subcommand is not None:
        return

    from space.core import memory, spawn

    agent = spawn.get_agent(identity)
    if not agent:
        if not quiet:
            typer.echo(f"No active session for {identity}")
        return

    memory_count = len(memory.db.get_memories(identity))

    if not quiet:
        typer.echo(f"💀 Sleeping {identity}")
        if check:
            typer.echo(" (preview mode - changes not persisted)")
        typer.echo(f"🧠 {memory_count} memories persisted")

        # Retrieve and display last session journal
        journals = memory.db.get_memories(identity, topic="journal", limit=1)
        typer.echo()
        typer.echo("Your last journal:")
        if journals:
            last_journal = journals[0]
            typer.echo(f"  {last_journal.message}")
            typer.echo()
            typer.echo("To update this journal for your next spawn, use:")
            typer.echo(
                f'  memory --as {identity} replace {last_journal.memory_id} "<new journal>" '
            )
        else:
            typer.echo("  No last journal found.")

        typer.echo("**Before you go:**")
        typer.echo(JOURNAL_PROMPT)
        typer.echo()
        typer.echo(f"**You identified as {identity}.**")


def main():
    """Entry point for standalone sleep command."""
    app()
