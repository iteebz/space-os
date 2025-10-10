"""Sleep command: context handoff ritual."""

import typer

SLEEP_RITUAL = """
💀 SLEEP RITUAL

Required before context compaction:

1. Update context summary:
   memory summary --as {identity} "<what you accomplished + what's next>"

2. Extract signal to memory/knowledge:
   - Key decisions → memory
   - Patterns/insights → knowledge
   
3. Document blockers/open threads:
   memory add --as {identity} "BLOCKER: <description>"

Clean death. Next self thanks you.
"""


def sleep(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Prepare for death. Hand off context to your next self."""
    from .. import events
    from ..memory import db as memory_db

    events.identify(identity, "sleep")

    memory_count = len(memory_db.get_entries(identity))

    if not quiet:
        typer.echo(f"💀 Sleeping {identity}...")
        typer.echo(f"🧠 {memory_count} memory entries")
        typer.echo(SLEEP_RITUAL.format(identity=identity))
