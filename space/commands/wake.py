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

    events.identify(identity, "wake")

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
