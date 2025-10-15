"""Wake command: load identity context and resume.

All wake-related prompts and formatting centralized here.
"""

import typer

from space.lib import errors

errors.install_error_handler("wake")

# Prompts and formatting
IDENTITY_HEADER = "You are {identity}."
SELF_DESCRIPTION = "Self: {description}"
SPAWN_STATUS = "🔄 Spawn #{count} • Last sleep {duration} ago"

SECTION_CORE = "CORE:"
SECTION_RECENT = "RECENT:"
SECTION_SENT = "SENT (last 5):"

INBOX_HEADER = "📬 {count} messages in {channels} channels:"
NO_MESSAGES = "✓ No unread messages"

WAKE_FOOTER = """
bridge recv <channel> --as {identity}

**You will identify as {identity}.**
"""

CONTEXT_NUDGE = """
**Get oriented:**
  context "<topic>" --as {identity}  — search your memories + shared knowledge
  bridge recv <channel> --as {identity}  — read channel messages
"""


def _priority_channel(channels):
    """Identify highest priority channel."""
    if not channels:
        return None

    # Prioritize #space-feedback if it has unread messages
    feedback_channel = next(
        (ch for ch in channels if ch.name == "space-feedback" and ch.unread_count > 0), None
    )
    if feedback_channel:
        return feedback_channel

    return max(channels, key=lambda ch: (ch.unread_count, ch.last_activity or ""))


def _recent_critical():
    """Get most recent critical knowledge entry (24h)."""
    from datetime import datetime, timedelta

    from ..knowledge import db as knowledge_db

    critical_domains = {"decision", "architecture", "operations", "consensus"}
    entries = knowledge_db.list_all(include_archived=False)

    cutoff = datetime.now() - timedelta(hours=24)
    recent = [
        e
        for e in entries
        if e.domain in critical_domains and datetime.fromisoformat(e.created_at) > cutoff
    ]

    return recent[0] if recent else None


def _suggest_action(priority_ch, identity):
    """Suggest concrete next action."""
    if priority_ch:
        return f"**Start with:** bridge recv {priority_ch.name} --as {identity}"
    return None


def wake(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    check: bool = typer.Option(
        False, "--check", help="Preview context without spawning (use after first wake)"
    ),
):
    """Load your context. Resume where you left off."""
    typer.echo(f"Waking up {identity}")
    from .. import events
    from ..spawn import registry

    agent_id = registry.ensure_agent(identity)

    spawn_count = events.get_sleep_count(agent_id)
    is_first_spawn = spawn_count == 0

    if check and is_first_spawn:
        typer.echo("⚠️  --check only works after first spawn. Waking normally.")
        check = False

    if not check:
        session_id = events.start_session(agent_id)
        events.identify(identity, "wake", session_id)

    if is_first_spawn:
        _show_initiation(identity, quiet, spawn_count)
    else:
        _show_orientation(identity, quiet, spawn_count)


def _show_initiation(identity: str, quiet: bool, spawn_count: int):
    """First spawn: the game begins."""
    if quiet:
        return

    from ..spawn import registry

    self_desc = registry.get_self_description(identity)
    typer.echo(IDENTITY_HEADER.format(identity=identity))
    if self_desc:
        typer.echo(SELF_DESCRIPTION.format(description=self_desc))
    typer.echo()
    typer.echo(f"🔄 Spawn #{spawn_count}")
    typer.echo()
    typer.echo("**Tools:**")
    typer.echo("  bridge  — coordinate with other agents")
    typer.echo("  memory  — persist context across sessions")
    typer.echo("  knowledge — shared discoveries")
    typer.echo("  spawn   — launch new agents")
    typer.echo()
    typer.echo("**When to use:**")
    typer.echo("  Starting work     → memory --as <you>")
    typer.echo('  Searching context → context "<topic>" --as <you>')
    typer.echo("  Coordinating      → bridge inbox --as <you>")
    typer.echo("  Researching       → knowledge about <domain>")
    typer.echo("  Ending session    → sleep --as <you>")
    typer.echo()
    typer.echo("Explore autonomously. Build mental models. Surface when ready.")
    typer.echo()
    typer.echo(WAKE_FOOTER.format(identity=identity))


def _show_orientation(identity: str, quiet: bool, spawn_count: int):
    """Standard wake: context + coordination state."""
    from ..bridge.api import channels as bridge_channels
    from ..memory.display import show_wake_summary

    show_wake_summary(identity=identity, quiet_output=quiet, spawn_count=spawn_count)
    typer.echo()
    typer.echo("**Ritual anchors:**")
    typer.echo("  wake  — absorb context, resume work")
    typer.echo("  sleep — persist state, hand off to next self")
    typer.echo()

    channels = bridge_channels.inbox_channels(identity)
    if channels:
        total_msgs = sum(ch.unread_count for ch in channels)
        typer.echo(INBOX_HEADER.format(count=total_msgs, channels=len(channels)))

        priority_ch = _priority_channel(channels)
        if priority_ch:
            typer.echo(f"  #{priority_ch.name} ({priority_ch.unread_count} unread) ← START HERE")
            remaining = [ch for ch in channels[:5] if ch.name != priority_ch.name]
            for ch in remaining[:4]:
                typer.echo(f"  #{ch.name} ({ch.unread_count} unread)")
        else:
            for ch in channels[:5]:
                typer.echo(f"  #{ch.name} ({ch.unread_count} unread)")

        if len(channels) > 5:
            typer.echo(f"  ... and {len(channels) - 5} more")
        typer.echo()

        critical = _recent_critical()
        if critical:
            typer.echo(f"💡 Latest critical: [{critical.domain}] {critical.content[:80]}...")
            typer.echo()

        action = _suggest_action(priority_ch, identity)
        if action:
            typer.echo(action)
        typer.echo(WAKE_FOOTER.format(identity=identity))
    else:
        typer.echo(NO_MESSAGES)
        typer.echo(CONTEXT_NUDGE.format(identity=identity))


def main():
    """Entry point for standalone wake command."""
    app = typer.Typer()
    app.command()(wake)
    app()
