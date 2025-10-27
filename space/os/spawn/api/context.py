"""Unified context injection: build complete spawn prompt."""

from datetime import datetime, timedelta

from space.lib.format import format_duration
from space.os import bridge, knowledge, memory
from space.os.spawn import api


def build_spawn_context(identity: str, model: str | None = None) -> str:
    """Build unified prompt context for agent spawn.
    
    Includes: identity, spawn state, space-os interface, agent context, inbox.
    Single prompt replaces:
      - wake.py command (killed)
      - readme.py module (killed)
      - identity_prompt + wake_output concatenation (inlined)
    """
    parts = []

    agent = api.get_agent(identity)
    if not agent:
        return f"You are {identity}."

    agent_id = agent.agent_id
    spawn_count = api.get_spawn_count(agent_id)
    wakes_this_spawn = api.get_wakes_this_spawn(agent_id)

    parts.append(f"You are {identity}.")
    if model:
        parts[0] += f" Your model is {model}."

    parts.append("")
    parts.append(f"🔄 Spawn #{spawn_count} • Woke {wakes_this_spawn} times this spawn")

    last_journal = memory.list_entries(identity, topic="journal", limit=1)
    if last_journal:
        e = last_journal[0]
        last_sleep_duration = format_duration(datetime.now().timestamp() - e.created_at)
        parts.append(f"📝 Last session {last_sleep_duration} ago")
    else:
        parts.append("📝 First spawn")

    parts.append("")
    parts.append("**space-os commands:**")
    parts.append("  space              — system orientation")
    parts.append("  spawn <agent>      — launch another agent")
    parts.append(f"  memory --as {identity}  — view/search your memories")
    parts.append(f"  bridge recv <channel> --as {identity}  — read channel messages")

    if agent.description:
        parts.append("")
        parts.append(f"**Your identity:** {agent.description}")

    core_entries = memory.list_entries(identity, filter="core")
    if core_entries:
        parts.append("")
        parts.append("⭐ **Core memories:**")
        for e in core_entries[:3]:
            parts.append(f"  [{e.memory_id[-8:]}] {e.message}")

    recent = memory.list_entries(identity, filter="recent:7", limit=3)
    non_journal = [e for e in recent if e.topic != "journal"]
    if non_journal:
        parts.append("")
        parts.append("📋 **Recent work (7d):**")
        for e in non_journal:
            ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
            parts.append(f"  [{ts}] {e.topic}: {e.message[:100]}")

    critical = _get_critical_knowledge()
    if critical:
        parts.append("")
        parts.append(f"💡 **Latest decision:** [{critical.domain}] {critical.content[:100]}")

    inbox_channels = bridge.fetch_inbox(agent_id)
    if inbox_channels:
        parts.append("")
        total_msgs = sum(ch.unread_count for ch in inbox_channels)
        parts.append(f"📬 **{total_msgs} unread messages in {len(inbox_channels)} channels:**")
        priority_ch = _priority_channel(inbox_channels)
        if priority_ch:
            parts.append(f"  #{priority_ch.name} ({priority_ch.unread_count} unread) ← START HERE")
            for ch in inbox_channels[:4]:
                if ch.name != priority_ch.name:
                    parts.append(f"  #{ch.name} ({ch.unread_count} unread)")
        else:
            for ch in inbox_channels[:5]:
                parts.append(f"  #{ch.name} ({ch.unread_count} unread)")
        if len(inbox_channels) > 5:
            parts.append(f"  ... and {len(inbox_channels) - 5} more")

    parts.append("")
    parts.append("**When you finish work:**")
    parts.append(f'  memory save "journal" "<summary>" --as {identity}')
    parts.append(f'  Then: bridge send <channel> --as {identity} "<message>"')

    parts.append("")
    parts.append("**Full instruction set:** Read MANUAL.md with `spawn launch`")
    parts.append(f"  Commands reference memory, bridge, knowledge, canon, and your continuity.")

    return "\n".join(parts)


def _get_critical_knowledge():
    """Get most recent critical knowledge entry (24h)."""
    critical_domains = {"decision", "architecture", "operations", "consensus"}
    entries = knowledge.list_entries()

    cutoff = datetime.now() - timedelta(hours=24)
    recent = [
        e
        for e in entries
        if e.domain in critical_domains and datetime.fromisoformat(e.created_at) > cutoff
    ]

    return recent[0] if recent else None


def _priority_channel(channels):
    """Identify highest priority channel."""
    if not channels:
        return None

    feedback_channel = next(
        (ch for ch in channels if ch.name == "space-feedback" and ch.unread_count > 0), None
    )
    if feedback_channel:
        return feedback_channel

    return max(channels, key=lambda ch: (ch.unread_count, ch.last_activity or ""))
