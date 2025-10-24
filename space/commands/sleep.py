"""Sleep command: context handoff ritual."""

import typer

from space.os.lib import errors

errors.install_error_handler("sleep")

SUMMARY_PROMPT = """Consolidate session state before death. Quality sleep = prepared spawn.

**Capture:**
- Compress the last summary and this session's activities into a new, consolidated summary.
- Preserve valuable mental models or architectural insights as separate, focused memories.
- What shipped this session
- Active threads mid-execution
- Blockers, non-obvious state
- Architectural patterns discovered
- What next spawn inherits

**Memory operations:**
memory add --as <you> --topic summary "<synthesis>"
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


def sleep(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    check: bool = typer.Option(False, "--check", help="Preview sleep without persisting changes."),
):
    """Prepare for death. Hand off context to your next self."""
    from space.os import events
    from space.os.memory import db as memory_db
    from space.os.spawn import db as spawn_db

    agent_id = spawn_db.get_agent_id(identity)
    if not agent_id:
        if not quiet:
            typer.echo(f"No active session for {identity}")
        return

    if not check:
        events.identify(identity, "sleep")

    memory_count = len(memory_db.get_memories(identity))

    if not quiet:
        typer.echo(f"💀 Sleeping {identity}")
        if check:
            typer.echo(" (preview mode - changes not persisted)")
        typer.echo(f"🧠 {memory_count} memories persisted")

        # Retrieve and display last session summary
        summaries = memory_db.get_memories(identity, topic="summary", limit=1)
        typer.echo()
        typer.echo("Your last summary:")
        if summaries:
            last_summary = summaries[0]
            typer.echo(f"  {last_summary.message}")
            typer.echo()
            typer.echo("To update this summary for your next spawn, use:")
            typer.echo(
                f'  memory --as {identity} replace {last_summary.memory_id} "<new summary>" '
            )
        else:
            typer.echo("  No last summary found.")

        typer.echo("**Before you go:**")
        typer.echo(SUMMARY_PROMPT)
        typer.echo()
        typer.echo(f"**You identified as {identity}.**")


def main():
    """Entry point for standalone sleep command."""
    app = typer.Typer()
    app.command()(sleep)
    app()
