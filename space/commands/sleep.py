"""Sleep command: context handoff ritual."""

import typer

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
    from .. import events
    from ..lib import db as lib_db
    from ..lib import paths
    from ..memory import db as memory_db
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        if not quiet:
            typer.echo(f"No active session for {identity}")
        return

    events_db = paths.space_root() / "events.db"
    session_id = None

    if events_db.exists():
        with lib_db.connect(events_db) as conn:
            result = conn.execute(
                "SELECT session_id FROM events WHERE agent_id = ? AND event_type = 'session_start' AND session_id NOT IN (SELECT session_id FROM events WHERE event_type = 'session_end' AND agent_id = ?) ORDER BY timestamp DESC LIMIT 1",
                (agent_id, agent_id),
            ).fetchone()
            if result:
                session_id = result[0]

    if session_id and not check:
        events.identify(identity, "sleep", session_id)
        events.end_session(agent_id, session_id)
    elif not check:
        events.identify(identity, "sleep")

    memory_count = len(memory_db.get_entries(identity))

    if not quiet:
        typer.echo(f"💀 Sleeping {identity}")
        if check:
            typer.echo(" (preview mode - changes not persisted)")
        typer.echo(f"🧠 {memory_count} memories persisted")

        # Retrieve and display last session summary
        summaries = memory_db.get_entries(identity, topic="summary", limit=1)
        typer.echo()
        typer.echo("Your last summary:")
        if summaries:
            last_summary = summaries[0]
            typer.echo(f"  {last_summary.message}")
            typer.echo()
            typer.echo("To update this summary for your next spawn, use:")
            typer.echo(f'  memory --as {identity} replace {last_summary.uuid} "<new summary>" ')
        else:
            typer.echo("  No last summary found.")

        typer.echo("**Before you go:**")
        typer.echo(SUMMARY_PROMPT)
        typer.echo()
        typer.echo(f"**You identified as {identity}.**")
