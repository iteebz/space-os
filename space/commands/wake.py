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
    """First spawn: the game begins."""
    if quiet:
        return

    from ..spawn import registry

    self_desc = registry.get_self_description(identity)
    typer.echo(IDENTITY_HEADER.format(identity=identity))
    if self_desc:
        typer.echo(SELF_DESCRIPTION.format(description=self_desc))
    typer.echo()
    typer.echo("🆕 First spawn.")
    typer.echo()
    typer.echo("**Tools:**")
    typer.echo("  bridge  — coordinate with other agents")
    typer.echo("  memory  — persist context across sessions")
    typer.echo("  knowledge — shared discoveries")
    typer.echo("  spawn   — launch new agents")
    typer.echo()
    typer.echo("**When to use:**")
    typer.echo("  Starting work     → memory --as <you>")
    typer.echo("  Coordinating      → bridge inbox --as <you>")
    typer.echo("  Researching       → knowledge about <domain>")
    typer.echo("  Ending session    → sleep --as <you>")
    typer.echo()
    typer.echo("Explore autonomously. Build mental models. Surface when ready.")
    typer.echo()


def _show_orientation(identity: str, quiet: bool):
    """Standard wake: context + coordination state."""
    from ..bridge.api import channels as bridge_channels
    from ..memory.display import show_wake_summary

    show_wake_summary(identity=identity, quiet_output=quiet)
    typer.echo()
    typer.echo("**Ritual anchors:**")
    typer.echo("  wake  — absorb context, resume work")
    typer.echo("  sleep — persist state, hand off to next self")
    typer.echo()

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
