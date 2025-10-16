import json
import time
from datetime import datetime

import typer

from space.lib.format import format_duration


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
    from space.knowledge import db as knowledge_db
    from space.spawn import registry

    typer.echo("\n" + "─" * 60)

    agent_id = registry.get_agent_id(identity)
    if not agent_id:
        typer.echo(f"\nNo agent found for identity: {identity}")
        return

    knowledge_entries = knowledge_db.query_by_agent(agent_id)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )
    else:
        typer.echo(
            "\nYou haven't made any knowledge contributions yet. Build more confidence first before doing that."
        )

    typer.echo("\n" + "─" * 60)


def show_wake_summary(identity: str, quiet_output: bool, spawn_count: int):
    from space.bridge import db as bridge_db
    from space.commands import wake as wake_prompts
    from space.memory import db as memory_db
    from space.spawn import registry

    if quiet_output:
        return

    self_desc = registry.get_self_description(identity)
    typer.echo(wake_prompts.IDENTITY_HEADER.format(identity=identity))
    if self_desc:
        typer.echo(wake_prompts.SELF_DESCRIPTION.format(description=self_desc))
    typer.echo()

    from space import events

    agent_id = registry.get_agent_id(identity)

    if agent_id:
        last_sleep_timestamp = events.get_last_sleep_time(agent_id)

        if last_sleep_timestamp:
            last_sleep_duration = format_duration(time.time() - last_sleep_timestamp)
            typer.echo(
                wake_prompts.SPAWN_STATUS.format(count=spawn_count, duration=last_sleep_duration)
            )
        else:
            typer.echo(f"🔄 Spawn #{spawn_count}")

        summaries = memory_db.get_memories(identity, topic="summary")
        if summaries:
            typer.echo("📝 Last session:")
            typer.echo(f"  {summaries[-1].message}")
            if len(summaries) > 1:
                typer.echo()
                typer.echo("Previous sessions:")
                for s in reversed(summaries[-3:-1]):
                    typer.echo(f"  [{s.timestamp}] {s.message}")
            typer.echo()

        core_entries = memory_db.get_core_entries(identity)
        if core_entries:
            typer.echo(wake_prompts.SECTION_CORE)
            for e in core_entries[:5]:
                typer.echo(f"  [{e.memory_id[-8:]}] {e.message}")
            typer.echo()

        recent = memory_db.get_recent_entries(identity, days=7, limit=30)
        non_summary = [e for e in recent if e.topic != "summary" and not e.core][:3]
        if non_summary:
            typer.echo(wake_prompts.SECTION_RECENT)
            for e in non_summary:
                ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
                typer.echo(f"  [{ts}] {e.topic}: {e.message}")
            typer.echo()

        sent_msgs = bridge_db.get_sender_history(identity, limit=5)
        if sent_msgs:
            typer.echo(wake_prompts.SECTION_SENT)
            channel_names = {}
            for msg in sent_msgs:
                if msg.channel_id not in channel_names:
                    channel_names[msg.channel_id] = bridge_db.get_channel_name(msg.channel_id)
                channel = channel_names[msg.channel_id]
                ts = datetime.strptime(msg.created_at, "%Y-%m-%d %H:%M:%S").strftime("%m-%d %H:%M")
                first_line = msg.content.split("\n")[0]
                preview = first_line[:50] + "..." if len(first_line) > 50 else first_line
                typer.echo(f"  [{ts}] #{channel}: {preview}")
            typer.echo()


def show_smart_memory(identity: str, json_output: bool, quiet_output: bool):
    from dataclasses import asdict

    from space.memory import db as memory_db
    from space.spawn import registry

    self_desc = registry.get_self_description(identity)
    summaries = memory_db.get_memories(identity, topic="summary")
    core_entries = memory_db.get_core_entries(identity)
    recent_entries = memory_db.get_recent_entries(identity, days=7, limit=20)

    if json_output:
        payload = {
            "identity": identity,
            "description": self_desc,
            "sessions": [asdict(s) for s in summaries],
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

    if summaries:
        typer.echo("📝 Last session:")
        typer.echo(f"  {summaries[-1].message}")
        if len(summaries) > 1:
            typer.echo()
            typer.echo("Previous sessions:")
            for s in reversed(summaries[-3:-1]):
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
            if e.core or e.topic == "summary":
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
