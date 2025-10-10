"""Sleep command: context handoff ritual."""

import typer

SUMMARY_PROMPT = """Analyze this session and produce structured markdown:

## Accomplished
[2-3 sentences: what got done, key decisions made]

## Pending
- [task]
- [task]

## Completed  
- [task]
- [task]

## Context
[Critical threads, blockers, or handoff notes for next spawn]

---
Requirements:
- Terse, technical language
- Tasks = actionable items only
- Context = blockers or non-obvious state
- Skip ceremony, capture signal"""


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
        typer.echo(f"💀 Sleeping {identity}...")
        typer.echo(f"🧠 {memory_count} memory entries")
        typer.echo()
        typer.echo("Generate sleep summary with:")
        typer.echo(f'  memory summary --as {identity} "<summary>"')
        typer.echo()
        typer.echo(SUMMARY_PROMPT)
