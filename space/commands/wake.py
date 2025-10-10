"""Wake command: load identity context and resume.

All wake-related prompts and formatting centralized here.
"""

import typer

# Prompts and formatting
IDENTITY_HEADER = "You are {identity}."
SELF_DESCRIPTION = "Self: {description}"
SPAWN_STATUS = "🔄 Spawn #{count} • Last spawn {duration} ago"

SECTION_CORE = "CORE:"
SECTION_RECENT = "RECENT:"
SECTION_SENT = "SENT (last 5):"

INBOX_HEADER = "📬 {count} messages in {channels} channels:"
NO_MESSAGES = "✓ No unread messages"

WAKE_FOOTER = """
bridge recv <channel> --as {identity}
"""


def wake(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Load your context. Resume where you left off."""
    typer.echo(f"Waking up {identity}")
    from .. import events
    from ..bridge.api import channels as bridge_channels
    from ..lib import db as lib_db
    from ..lib import paths
    from ..spawn import registry

    agent_id = registry.ensure_agent(identity)
    session_id = events.start_session(agent_id)
    spawn_count = events.get_session_count(agent_id)
    is_first_spawn = spawn_count == 1
    
    events.identify(identity, "wake", session_id)
    
    if is_first_spawn:
        _show_initiation(identity, quiet)
    else:
        _show_orientation(identity, quiet)


def _show_initiation(identity: str, quiet: bool):
    """First spawn: encourage autonomous exploration."""
    if quiet:
        return
    
    from ..spawn import registry
    
    self_desc = registry.get_self_description(identity)
    typer.echo(IDENTITY_HEADER.format(identity=identity))
    if self_desc:
        typer.echo(SELF_DESCRIPTION.format(description=self_desc))
    typer.echo()
    
    typer.echo("🆕 First spawn detected.")
    typer.echo()
    typer.echo("Building orientation...")
    typer.echo("  ✓ Scanning knowledge base")
    typer.echo("  ✓ Mapping active channels")
    typer.echo("  ✓ Loading recent context")
    typer.echo()
    typer.echo("Your move: Explore autonomously, build mental models, surface when ready.")
    typer.echo()
    typer.echo("Suggested first steps:")
    typer.echo("  → knowledge search \"space-os\"")
    typer.echo("  → memory write --key \"initial-scan\" \"...\"")
    typer.echo(f"  → bridge list --as {identity} (when ready to engage)")
    typer.echo()


def _show_orientation(identity: str, quiet: bool):
    """Standard wake: show context and inbox."""
    from ..bridge.api import channels as bridge_channels
    from ..memory.display import show_wake_summary

    show_wake_summary(identity=identity, quiet_output=quiet)

    channels = bridge_channels.inbox_channels(identity)
    if channels:
        total_msgs = sum(ch.unread_count for ch in channels)
        typer.echo(INBOX_HEADER.format(count=total_msgs, channels=len(channels)))
        for ch in channels[:5]:
            typer.echo(f"  #{ch.name} ({ch.unread_count} unread)")
        if len(channels) > 5:
            typer.echo(f"  ... and {len(channels) - 5} more")
        typer.echo(WAKE_FOOTER.format(identity=identity))
    else:
        typer.echo(NO_MESSAGES)
