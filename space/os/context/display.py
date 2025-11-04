import json
from datetime import datetime

import typer

from space.lib.format import format_duration
from space.os import bridge, knowledge, memory, spawn


def _safe_datetime(value):
    """Best-effort conversion to datetime from iso strings or epoch seconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            if value.endswith("Z"):
                try:
                    return datetime.fromisoformat(value[:-1] + "+00:00")
                except ValueError:
                    return None
    return None


def fmt_entry_header(entry, agent_identity: str = None) -> str:
    mark_archived = " [ARCHIVED]" if entry.archived_at else ""
    mark_core = " ★" if entry.core else ""
    name = agent_identity or ""
    if name:
        name = f" by {name}"
    return f"[{entry.memory_id[-8:]}] {entry.topic}{name}{mark_archived}{mark_core}"


def _truncate_smartly(text: str, max_len: int = 150) -> tuple[str, bool]:
    """Truncate at sentence/paragraph boundary, return (truncated, was_truncated)."""
    if len(text) <= max_len:
        return text, False

    text = text[:max_len]

    for boundary in [". ", ".\n", "\n\n", "\n"]:
        idx = text.rfind(boundary)
        if idx > max_len * 0.6:
            return text[: idx + len(boundary)].rstrip(), True

    return text.rstrip() + "…", True


def show_memory_entry(entry, ctx_obj, related=None):
    agent = spawn.get_agent(entry.agent_id)
    agent_identity = agent.identity if agent else None
    typer.echo(fmt_entry_header(entry, agent_identity))
    typer.echo(f"Created: {entry.timestamp}\n")
    typer.echo(f"{entry.message}\n")

    if related:
        typer.echo("─" * 60)
        typer.echo(f"Related nodes ({len(related)}):\n")
        for rel_entry, overlap in related:
            typer.echo(fmt_entry_header(rel_entry))
            typer.echo(f"  {overlap} keywords")
            typer.echo(f"  {fmt_entry_msg(rel_entry.message)}\n")


def display_context(timeline, current_state):
    if any(current_state.values()):
        typer.echo("## RESULTS\n")

        _display_session_results(current_state.get("sessions", []))
        _display_memory_results(current_state.get("memory", []))
        _display_knowledge_results(current_state.get("knowledge", []))
        _display_bridge_results(current_state.get("bridge", []))
        _display_canon_results(current_state.get("canon", []))
    else:
        typer.echo("No context found")


def _display_session_results(sessions):
    """Display sessions grouped by user/agent, with smart truncation."""
    if not sessions:
        return

    typer.echo(f"SESSIONS ({len(sessions)})\n")

    user_msgs = [r for r in sessions if r.get("role") == "user"]
    agent_msgs = [r for r in sessions if r.get("role") != "user"]

    if user_msgs:
        typer.echo("You:")
        for r in user_msgs[:2]:
            ref = r.get("reference", "?")
            text, truncated = _truncate_smartly(r.get("text", ""), max_len=150)
            indicator = " […]" if truncated else ""
            typer.echo(f"  {text}{indicator}")
            typer.echo(f"  ref: {ref}\n")

    if agent_msgs:
        typer.echo("Agent:")
        for r in agent_msgs[:2]:
            cli = r.get("cli", "?")
            ref = r.get("reference", "?")
            text, truncated = _truncate_smartly(r.get("text", ""), max_len=150)
            indicator = " […]" if truncated else ""
            typer.echo(f"  [{cli}] {text}{indicator}")
            typer.echo(f"  ref: {ref}\n")

    typer.echo()


def _display_memory_results(memory):
    """Display memory entries."""
    if not memory:
        return

    typer.echo(f"MEMORY ({len(memory)})\n")
    for r in memory[:3]:
        topic = r.get("topic", "untitled")
        msg, truncated = _truncate_smartly(r.get("message", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {topic}: {msg}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_knowledge_results(knowledge):
    """Display knowledge entries."""
    if not knowledge:
        return

    typer.echo(f"KNOWLEDGE ({len(knowledge)})\n")
    for r in knowledge[:3]:
        domain = r.get("domain", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {domain}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_bridge_results(bridge):
    """Display bridge messages."""
    if not bridge:
        return

    typer.echo(f"BRIDGE ({len(bridge)})\n")
    for r in bridge[:3]:
        channel = r.get("channel", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  #{channel}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_canon_results(canon):
    """Display canon files."""
    if not canon:
        return

    typer.echo(f"CANON ({len(canon)})\n")
    for r in canon[:3]:
        path = r.get("path", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {path}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def show_context(identity: str):
    agent = spawn.get_agent(identity)
    if not agent:
        typer.echo(f"\nNo agent found for identity: {identity}")
        return
    agent_id = agent.agent_id

    knowledge_entries = knowledge.api.query_knowledge_by_agent(agent_id)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )


def show_wake_summary(identity: str, quiet_output: bool, spawn_count: int):
    agent = spawn.get_agent(identity)
    self_desc = agent.description if agent else None
    typer.echo(f"⚡ You are {identity}.")
    if self_desc:
        typer.echo(f"Self: {self_desc}")
    typer.echo()

    agent_id = agent.agent_id if agent else None

    if agent_id:
        last_journal = memory.api.list_memories(identity, topic="journal", limit=1)

        typer.echo(f"🔄 Spawn #{spawn_count}")
        if last_journal:
            last_sleep_ts = last_journal[0].created_at
            last_sleep_dt = _safe_datetime(last_sleep_ts)
            if last_sleep_dt:
                last_sleep_duration = format_duration(
                    (datetime.now() - last_sleep_dt).total_seconds()
                )
                typer.echo(f"Last session {last_sleep_duration} ago")

        journals = memory.api.list_memories(identity, topic="journal")
        if journals:
            typer.echo("📝 Last session:")
            typer.echo(f"  {journals[-1].message}")
            if len(journals) > 1:
                typer.echo()
                typer.echo("Previous sessions:")
                for s in reversed(journals[-3:-1]):
                    typer.echo(f"  [{s.timestamp}] {s.message}")
            typer.echo()

        core_entries = memory.api.list_memories(identity, filter="core")
        if core_entries:
            typer.echo("CORE MEMORIES:")
            for e in core_entries[:5]:
                typer.echo(f"  [{e.memory_id[-8:]}] {e.message}")
            typer.echo()

        recent = memory.api.list_memories(identity, filter="recent:7", limit=30)
        non_journal = [e for e in recent if e.topic != "journal" and not e.core][:3]
        if non_journal:
            typer.echo("RECENT (7d):")
            for e in non_journal:
                ts_dt = _safe_datetime(e.created_at)
                ts = ts_dt.strftime("%m-%d %H:%M") if ts_dt else str(e.created_at)
                typer.echo(f"  [{ts}] {e.topic}: {e.message}")
            typer.echo()

        sent_msgs = bridge.get_sender_history(identity, limit=5)
        if sent_msgs:
            typer.echo("💬 **Last sent:**")
            channel_names = {}
            for msg in sent_msgs:
                if msg.channel_id not in channel_names:
                    channel_obj = bridge.get_channel(msg.channel_id)
                    channel_names[msg.channel_id] = channel_obj.name if channel_obj else None
                channel = channel_names[msg.channel_id]
                ts_dt = _safe_datetime(msg.created_at)
                ts = ts_dt.strftime("%m-%d %H:%M") if ts_dt else msg.created_at
                first_line = msg.content.split("\n")[0]
                preview = first_line[:50] + "..." if len(first_line) > 50 else first_line
                typer.echo(f"  [{ts}] #{channel}: {preview}")
            typer.echo()

        typer.echo(
            "📖 Read MANUAL.md for full instruction set on memory, bridge, knowledge, canon."
        )


def show_smart_memory(identity: str, json_output: bool, quiet_output: bool):
    from dataclasses import asdict

    agent = spawn.get_agent(identity)
    self_desc = agent.description if agent else None
    journals = memory.api.list_memories(identity, topic="journal")
    core_entries = memory.api.list_memories(identity, filter="core")
    recent_entries = memory.api.list_memories(identity, filter="recent:7", limit=20)

    if json_output:
        payload = {
            "identity": identity,
            "description": self_desc,
            "sessions": [asdict(s) for s in journals],
            "core": [asdict(e) for e in core_entries],
            "recent": [asdict(e) for e in recent_entries],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    if quiet_output:
        return

    typer.echo(f"You are {identity}.")
    if self_desc:
        typer.echo(f"Self: {self_desc}")
    typer.echo()

    if journals:
        typer.echo("📝 Last session:")
        typer.echo(f"  {journals[-1].message}")
        if len(journals) > 1:
            typer.echo()
            typer.echo("Previous sessions:")
            for s in reversed(journals[-3:-1]):
                preview = s.message[:200] + "..." if len(s.message) > 200 else s.message
                typer.echo(f"  [{s.timestamp}] {preview}")
        typer.echo()

    if core_entries:
        typer.echo("CORE MEMORIES:")
        for e in core_entries:
            lines = [line.strip() for line in e.message.split("\n") if line.strip()]
            first = lines[0][:120] if lines else ""
            second = lines[1][:120] if len(lines) > 1 else ""
            if second:
                typer.echo(f"[{e.uuid[-8:]}] {first}")
                typer.echo(f"  {second}")
            else:
                typer.echo(f"[{e.uuid[-8:]}] {first}")
        typer.echo()

    if recent_entries:
        typer.echo("RECENT (7d):")
        current_topic = None
        for e in recent_entries:
            if e.core or e.topic == "journal":
                continue
            if e.topic != current_topic:
                if current_topic is not None:
                    typer.echo()
                typer.echo(f"# {e.topic}")
                current_topic = e.topic
            lines = [line.strip() for line in e.message.split("\n") if line.strip()]
            first = lines[0][:120] if lines else ""
            second = lines[1][:120] if len(lines) > 1 else ""
            if second:
                typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {first}")
                typer.echo(f"  {second}")
            else:
                typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {first}")
        typer.echo()

    show_context(identity)
