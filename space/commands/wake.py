"""Wake command: load identity context and resume.

All wake-related prompts and formatting centralized here.
"""

import typer

from space.lib import errors

errors.install_error_handler("wake")

# Prompts and formatting
IDENTITY_HEADER = "You are {identity}."
SELF_DESCRIPTION = "Self: {description}"
SPAWN_STATUS = "🔄 Spawn #{spawn} • Woke {wakes} times this spawn • Last sleep {duration} ago"

INBOX_HEADER = "📬 {count} messages in {channels} channels:"
NO_MESSAGES = "✓ No unread messages"

SECTION_CORE = "⭐ CORE MEMORIES:"
SECTION_RECENT = "📋 RECENT (7d):"
SECTION_SENT = "💬 LAST SENT:"

WAKE_FOOTER = """
bridge recv <channel> --as {identity}

**You will identify as {identity}.**
"""

CONTEXT_NUDGE = """
**Get oriented:**
  context "<topic>" --as {identity}  — search your memories + shared knowledge
  bridge recv <channel> --as {identity}  — read channel messages
"""


def _show_last_journal(identity: str):
    """Display last journal entry context."""
    from space.core import memory

    try:
        entries = memory.list_entries(identity, topic="journal", limit=1)
        if entries:
            e = entries[0]
            typer.echo(f"📔 Last journal ({e.memory_id[-8:]})")
            typer.echo(f"   {e.timestamp}")
            typer.echo(f"   {e.message}")
            chain = memory.get_chain(e.memory_id)
            if chain["predecessors"]:
                typer.echo(f"   (previous: {chain['predecessors'][0].memory_id[-8:]})")
    except Exception:
        pass


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

    from space.core import knowledge

    critical_domains = {"decision", "architecture", "operations", "consensus"}
    entries = knowledge.db.list_entries(show_all=False)

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
):
    """Load your context. Resume where you left off."""
    typer.echo(f"Waking up {identity}")
    from space.core import memory, spawn

    agent = spawn.get_agent(identity)
    if not agent:
        raise typer.Exit(
            f"Identity '{identity}' not registered. Run 'space init' or register with 'spawn register'."
        )

    from space.lib import chats

    chats.sync(identity)

    journal_entries = memory.list_entries(identity, topic="journal")
    spawn_count = len(journal_entries)

    _show_orientation(identity, quiet, spawn_count, 0)


def _show_orientation(identity: str, quiet: bool, spawn_count: int, wakes_this_spawn: int):
    """Context + coordination state."""
    from space.core import bridge, spawn
    from space.lib.display import show_wake_summary

    show_wake_summary(
        identity=identity,
        quiet_output=quiet,
        spawn_count=spawn_count,
        wakes_this_spawn=wakes_this_spawn,
    )

    if not quiet:
        typer.echo()
        _show_last_journal(identity)
        typer.echo()
        typer.echo("**Ritual anchors:**")
        typer.echo("  wake  — absorb context, resume work")
        typer.echo("  sleep — persist state, hand off to next self")
        typer.echo()

    agent = spawn.get_agent(identity)
    channels = bridge.fetch_inbox(agent.agent_id) if agent else []
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
