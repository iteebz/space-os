import json
import time
from datetime import datetime

import typer

from ..bridge import db as bridge_db
from ..commands import wake as wake_prompts
from ..knowledge import db as knowledge_db
from ..lib import db as lib_db
from ..lib import paths
from ..spawn import registry as spawn_registry
from . import db


def show_context(identity: str):
    typer.echo("\n" + "─" * 60)

    knowledge_entries = knowledge_db.query_by_agent(identity)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )

    typer.echo("\n" + "─" * 60)


def show_wake_summary(identity: str, quiet_output: bool):
    """Show concise wake summary: rolling summary, recent activity."""
    if quiet_output:
        return

    self_desc = spawn_registry.get_self_description(identity)
    typer.echo(wake_prompts.IDENTITY_HEADER.format(identity=identity))
    if self_desc:
        typer.echo(wake_prompts.SELF_DESCRIPTION.format(description=self_desc))
    typer.echo()

    from .. import events
    from ..spawn import registry

    agent_id = registry.get_agent_id(identity)

    if agent_id:
        spawn_count = events.get_session_count(agent_id)

        events_db = paths.space_root() / "events.db"
        if events_db.exists():
            with lib_db.connect(events_db) as conn:
                last_session_start = conn.execute(
                    "SELECT timestamp FROM events WHERE agent_id = ? AND event_type = 'session_start' ORDER BY timestamp DESC LIMIT 1",
                    (agent_id,),
                ).fetchone()

                if last_session_start:
                    last_spawn_duration = _format_duration(time.time() - last_session_start[0])
                    typer.echo(
                        wake_prompts.SPAWN_STATUS.format(
                            count=spawn_count, duration=last_spawn_duration
                        )
                    )

                    last_session_end = conn.execute(
                        "SELECT timestamp FROM events WHERE agent_id = ? AND event_type = 'session_end' ORDER BY timestamp DESC LIMIT 1",
                        (agent_id,),
                    ).fetchone()

                    if last_session_end:
                        sleep_duration = _format_duration(time.time() - last_session_end[0])
                        typer.echo(f"💤 Last sleep: {sleep_duration} ago")

                    typer.echo()

    summaries = db.get_entries(identity, topic="summary")
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

    core_entries = db.get_core_entries(identity)
    if core_entries:
        typer.echo(wake_prompts.SECTION_CORE)
        for e in core_entries[:5]:
            preview = e.message[:80] + "..." if len(e.message) > 80 else e.message
            typer.echo(f"  [{e.uuid[-8:]}] {preview}")
        typer.echo()

    recent = db.get_recent_entries(identity, days=7, limit=30)
    non_summary = [e for e in recent if e.topic != "summary" and not e.core][:3]
    if non_summary:
        typer.echo(wake_prompts.SECTION_RECENT)
        for e in non_summary:
            ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
            preview = e.message[:60] + "..." if len(e.message) > 60 else e.message
            typer.echo(f"  [{ts}] {e.topic}: {preview}")
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


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m" if mins else f"{hours}h"
    days = int(seconds / 86400)
    hours = int((seconds % 86400) / 3600)
    return f"{days}d {hours}h" if hours else f"{days}d"


def show_smart_memory(identity: str, json_output: bool, quiet_output: bool):
    from dataclasses import asdict

    self_desc = spawn_registry.get_self_description(identity)
    summaries = db.get_entries(identity, topic="summary")
    core_entries = db.get_core_entries(identity)
    recent_entries = db.get_recent_entries(identity, days=7, limit=20)

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
