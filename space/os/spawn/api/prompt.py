"""Agent launching: unified context injection."""

from datetime import datetime

from space.lib import paths
from space.os import bridge, memory

from . import agents, sessions


def build_identity_prompt(identity: str, model: str | None = None) -> str:
    """Build identity and space instructions for first prompt injection."""
    parts = [f"You are {identity}."]
    if model:
        parts[0] += f" Your model is {model}."
    parts.append("")
    parts.append("space commands:")
    parts.append("  run `space` for orientation (already in PATH)")
    parts.append(f"  run `memory --as {identity}` to access memories")
    return "\n".join(parts)


def spawn_prompt(identity: str, model: str | None = None) -> str:
    """Build unified prompt context from MANUAL.md template with agent context filled in.

    Replaces <identity> placeholders and inserts agent-specific context blocks.
    """
    try:
        agent = agents.get_agent(identity)
    except ValueError:
        agent = None
    agent_id = agent.agent_id if agent else None
    resolved_model = model

    manual_path = paths.package_root().parent / "MANUAL.md"
    if not manual_path.exists():
        base = f"You are {identity}."
        if resolved_model:
            base += f" Your model is {resolved_model}."
        return base

    manual_text = manual_path.read_text()

    if agent_id:
        try:
            spawn_count = sessions.get_spawn_count(agent_id)
        except Exception:  # pragma: no cover - defensive because DB may be unavailable in tests
            spawn_count = 0
    else:
        spawn_count = 0

    spawn_status = "📝 First spawn"
    try:
        last_journal = memory.api.list_memories(identity, topic="journal", limit=1)
        if last_journal:
            entry = last_journal[0]
            created_at = datetime.fromisoformat(entry.created_at)
            from space.lib.format import format_duration

            last_sleep_duration = format_duration((datetime.now() - created_at).total_seconds())
            spawn_status = f"📝 Last session {last_sleep_duration} ago"
    except Exception:  # pragma: no cover - defensive for missing memory DB
        pass

    template_vars = {
        "identity": identity,
        "spawn_count": spawn_count,
        "spawn_status": spawn_status,
        "model": f" Your model is {resolved_model}." if resolved_model else "",
    }

    output = manual_text
    for var, value in template_vars.items():
        output = output.replace(f"<{var}>", str(value))

    agent_info_blocks = _build_agent_info_blocks(identity, agent, agent_id)
    return output.replace("{{AGENT_INFO}}", agent_info_blocks or "")


def _build_agent_info_blocks(identity: str, agent, agent_id: str | None) -> str:
    """Build identity, memories, and bridge context blocks for template injection."""
    parts = []

    if not agent or not agent_id:
        return ""

    try:
        core_entries = memory.api.list_memories(identity, filter="core")
    except Exception:  # pragma: no cover - safeguard for unseeded DBs
        core_entries = []
    if core_entries:
        parts.append("⭐ **Core memories:**")
        for entry in core_entries[:3]:
            parts.append(f"  [{entry.memory_id[-8:]}] {entry.message}")
        parts.append("")

    try:
        recent = memory.api.list_memories(identity, filter="recent:7", limit=3)
    except Exception:  # pragma: no cover - safeguard for unseeded DBs
        recent = []
    non_journal = [entry for entry in recent if entry.topic != "journal"]
    if non_journal:
        parts.append("📋 **Recent work (7d):**")
        for entry in non_journal:
            ts = datetime.fromisoformat(entry.created_at).strftime("%m-%d %H:%M")
            parts.append(f"  [{ts}] {entry.topic}: {entry.message[:100]}")
        parts.append("")

    try:
        inbox_channels = bridge.fetch_inbox(agent_id)
    except Exception:  # pragma: no cover - safeguard for offline bridge
        inbox_channels = []
    if inbox_channels:
        total_msgs = sum(ch.unread_count for ch in inbox_channels)
        parts.append(f"📬 **{total_msgs} unread messages in {len(inbox_channels)} channels:**")
        for channel in inbox_channels[:5]:
            parts.append(f"  #{channel.name} ({channel.unread_count} unread)")
        if len(inbox_channels) > 5:
            parts.append(f"  ... and {len(inbox_channels) - 5} more")
        parts.append("")

    return "\n".join(parts)
