import json
import time
from datetime import datetime

import typer

from ..bridge import db as bridge_db
from ..knowledge import db as knowledge_db
from ..spawn import registry as spawn_registry
from . import db


def show_context(identity: str):
    typer.echo("\n" + "─" * 60)

    regs = spawn_registry.list_registrations()
    my_regs = [r for r in regs if r.agent_name == identity]
    if my_regs:
        topics = {r.topic for r in my_regs}
        typer.echo(f"\nREGISTERED: {', '.join(sorted(topics))}")

    knowledge_entries = knowledge_db.query_by_contributor(identity)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )

    typer.echo("\n" + "─" * 60)


def show_wake_summary(identity: str, quiet_output: bool):
    """Show concise wake summary: sleep duration, last checkpoint, recent activity."""
    if quiet_output:
        return

    self_desc = spawn_registry.get_self_description(identity)
    typer.echo(f"You are {identity}.")
    if self_desc:
        typer.echo(f"Self: {self_desc}")
    typer.echo()

    last_checkpoint = _get_last_checkpoint(identity)
    if last_checkpoint:
        sleep_duration = _format_duration(time.time() - last_checkpoint.created_at)
        checkpoint_time = datetime.fromtimestamp(last_checkpoint.created_at).strftime(
            "%Y-%m-%d %H:%M"
        )
        typer.echo(f"💤 Asleep for {sleep_duration} (since {checkpoint_time})")
        typer.echo(f"📌 Last checkpoint: {last_checkpoint.message}")
        typer.echo()

    core_entries = db.get_core_entries(identity)
    if core_entries:
        typer.echo("CORE:")
        for e in core_entries[:5]:
            preview = e.message[:80] + "..." if len(e.message) > 80 else e.message
            typer.echo(f"  [{e.uuid[-8:]}] {preview}")
        typer.echo()

    recent = db.get_recent_entries(identity, days=7, limit=30)
    non_checkpoint = [e for e in recent if e.source != "checkpoint" and not e.core][:3]
    if non_checkpoint:
        typer.echo("RECENT:")
        for e in non_checkpoint:
            ts = datetime.fromtimestamp(e.created_at).strftime("%m-%d %H:%M")
            preview = e.message[:60] + "..." if len(e.message) > 60 else e.message
            typer.echo(f"  [{ts}] {e.topic}: {preview}")
        typer.echo()

    sent_msgs = bridge_db.get_sender_history(identity, limit=5)
    if sent_msgs:
        typer.echo("SENT (last 5):")
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


def _get_last_checkpoint(identity: str):
    """Get the most recent checkpoint entry for an identity."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT uuid, identity, topic, message, timestamp, created_at, archived_at, core, source, bridge_channel, code_anchors FROM memory WHERE identity = ? AND source = 'checkpoint' ORDER BY created_at DESC LIMIT 1",
            (identity,),
        ).fetchone()
    if not row:
        return None
    from .models import Entry

    return Entry(
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        bool(row[7]),
        row[8],
        row[9],
        row[10],
    )


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
    core_entries = db.get_core_entries(identity)
    recent_entries = db.get_recent_entries(identity, days=7, limit=20)

    if json_output:
        payload = {
            "identity": identity,
            "description": self_desc,
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

    if core_entries:
        typer.echo("CORE MEMORIES:")
        for e in core_entries:
            preview = e.message[:80] + "..." if len(e.message) > 80 else e.message
            typer.echo(f"[{e.uuid[-8:]}] {preview}")
        typer.echo()

    if recent_entries:
        typer.echo("RECENT (7d):")
        current_topic = None
        for e in recent_entries:
            if e.core:
                continue
            if e.topic != current_topic:
                if current_topic is not None:
                    typer.echo()
                typer.echo(f"# {e.topic}")
                current_topic = e.topic
            preview = e.message[:100] + "..." if len(e.message) > 100 else e.message
            typer.echo(f"[{e.uuid[-8:]}] [{e.timestamp}] {preview}")
        typer.echo()

    show_context(identity)
