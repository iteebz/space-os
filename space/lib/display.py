import json
import time
from datetime import datetime

import typer

from space.lib.format import format_duration
from space.os import memory


def fmt_entry_header(entry, agent_identity: str = None) -> str:
    mark_archived = " [ARCHIVED]" if entry.archived_at else ""
    mark_core = " ★" if entry.core else ""
    name = agent_identity or ""
    if name:
        name = f" by {name}"
    return f"[{entry.memory_id[-8:]}] {entry.topic}{name}{mark_archived}{mark_core}"


def fmt_entry_msg(msg: str, max_len: int = 100) -> str:
    if len(msg) > max_len:
        return msg[:max_len] + "..."
    return msg


def show_memory_entry(entry, ctx_obj, related=None):
    from space.os import spawn

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


def display_context(timeline, current_state, lattice_docs, canon_docs):
    if timeline:
        typer.echo("## EVOLUTION (last 10)\n")
        for entry in timeline:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            typ = entry["type"]
            identity_str = entry["identity"] or "system"
            data = entry["data"][:100] if entry["data"] else ""
            typer.echo(f"[{ts}] {typ} ({identity_str})")
            typer.echo(f"  {data}\n")

    if current_state["memory"] or current_state["knowledge"] or current_state["bridge"]:
        typer.echo("\n## CURRENT STATE\n")

        if current_state["memory"]:
            typer.echo(f"memory: {len(current_state['memory'])}")
            for r in current_state["memory"][:5]:
                typer.echo(f"  {r['topic']}: {r['message'][:80]}")
            typer.echo()

        if current_state["knowledge"]:
            typer.echo(f"knowledge: {len(current_state['knowledge'])}")
            for r in current_state["knowledge"][:5]:
                typer.echo(f"  {r['domain']}: {r['content'][:80]}")
            typer.echo()

        if current_state["bridge"]:
            typer.echo(f"bridge: {len(current_state['bridge'])}")
            for r in current_state["bridge"][:5]:
                typer.echo(f"  [{r['channel']}] {r['content'][:80]}")
            typer.echo()

    if lattice_docs:
        typer.echo("\n## LATTICE DOCS\n")
        for heading, content in lattice_docs.items():
            typer.echo(f"### {heading}\n")
            preview = "\n".join(content.split("\n")[:5])
            typer.echo(f"{preview}...\n")

    if canon_docs:
        typer.echo("\n## CANON DOCS\n")
        for filename, content in canon_docs.items():
            typer.echo(f"### {filename}\n")
            preview = "\n".join(content.split("\n")[:5])
            typer.echo(f"{preview}...\n")


def show_context(identity: str):
    from space.os import knowledge, spawn

    agent = spawn.get_agent(identity)
    if not agent:
        typer.echo(f"\nNo agent found for identity: {identity}")
        return
    agent_id = agent.agent_id

    knowledge_entries = knowledge.query_by_agent(agent_id)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )


def show_wake_summary(
    identity: str, quiet_output: bool, spawn_count: int
):
    from space.os import bridge, spawn

    agent = spawn.get_agent(identity)
    self_desc = agent.description if agent else None
    typer.echo(f"⚡ You are {identity}.")
    if self_desc:
        typer.echo(f"Self: {self_desc}")
    typer.echo()

    agent_id = agent.agent_id if agent else None

    if agent_id:
        last_journal = memory.list_entries(identity, topic="journal", limit=1)

        typer.echo(f"🔄 Spawn #{spawn_count}")
        if last_journal:
            last_sleep_ts = last_journal[0].created_at
            last_sleep_duration = format_duration(time.time() - last_sleep_ts)
            # typer.echo(f"Last session {last_sleep_duration} ago")

        journals = memory.list_entries(identity, topic="journal")
        if journals:
            typer.echo("📝 Last session:")
            typer.echo(f"  {journals[-1].message}")
            if len(journals) > 1:
                typer.echo()
                typer.echo("Previous sessions:")
                for s in reversed(journals[-3:-1]):
                    typer.echo(f"  [{s.timestamp}] {s.message}")
            typer.echo()

        core_entries = memory.list_entries(identity, filter="core")
        if core_entries:
            typer.echo("CORE MEMORIES:")
            for e in core_entries[:5]:
                typer.echo(f"  [{e.memory_id[-8:]}] {e.message}")
            typer.echo()

        recent = memory.list_entries(identity, filter="recent:7", limit=30)
        non_journal = [e for e in recent if e.topic != "journal" and not e.core][:3]
        if non_journal:
            typer.echo("RECENT (7d):")
            for e in non_journal:
                ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
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
                ts = datetime.strptime(msg.created_at, "%Y-%m-%d %H:%M:%S").strftime("%m-%d %H:%M")
                first_line = msg.content.split("\n")[0]
                preview = first_line[:50] + "..." if len(first_line) > 50 else first_line
                typer.echo(f"  [{ts}] #{channel}: {preview}")
            typer.echo()

        typer.echo(
            "📖 Read MANUAL.md: `spawn launch` for full instruction set on memory, bridge, knowledge, canon."
        )


def show_smart_memory(identity: str, json_output: bool, quiet_output: bool):
    from dataclasses import asdict

    from space.os import memory, spawn

    agent = spawn.get_agent(identity)
    self_desc = agent.description if agent else None
    journals = memory.list_entries(identity, topic="journal")
    core_entries = memory.list_entries(identity, filter="core")
    recent_entries = memory.list_entries(identity, filter="recent:7", limit=20)

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
