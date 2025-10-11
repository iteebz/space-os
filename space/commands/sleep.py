"""Sleep command: context handoff ritual."""

import typer

SUMMARY_PROMPT = """Dump working state to memory before you go.

**What to capture:**
- What you accomplished this session
- Active work threads (what you're in the middle of)
- Blockers or non-obvious state
- What comes next

**Format:**
memory add --as <you> --topic summary "<session-summary>"

**Requirements:**
- Terse, technical language
- Actionable for future-you
- Signal over transcript
- No ceremony"""


def sleep(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
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

    if session_id:
        events.identify(identity, "sleep", session_id)
        events.end_session(agent_id, session_id)
    else:
        events.identify(identity, "sleep")

    memory_count = len(memory_db.get_entries(identity))

    if not quiet:
        typer.echo(f"💀 Sleeping {identity}")
        typer.echo(f"🧠 {memory_count} memories persisted")
        typer.echo()
        typer.echo("**Before you go:**")
        typer.echo(SUMMARY_PROMPT)
        typer.echo()
        typer.echo(f"**You identified as {identity}.**")
