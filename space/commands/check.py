from datetime import datetime

import typer

from ..lib import db, paths
from ..spawn import registry


def check(agent: str = typer.Argument(..., help="Agent name")):
    """Show agent dashboard: summary, memories, stats."""
    registry.init_db()

    agent_id = registry.get_agent_id(agent)
    if not agent_id:
        typer.echo(f"Agent {agent} not found")
        raise typer.Exit(1)

    with registry.get_db() as conn:
        row = conn.execute(
            "SELECT name, self_description FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
        name = row["name"]
        self_desc = row["self_description"]

    typer.echo(f"Agent: {name}")
    if self_desc:
        typer.echo(f"Self: {self_desc}")
    typer.echo()

    events_db = paths.space_root() / "events.db"
    memory_db = paths.space_root() / "memory.db"
    knowledge_db = paths.space_root() / "knowledge.db"
    bridge_db = paths.space_root() / "bridge.db"

    session_start = None
    last_event = None
    spawn_count = 0

    if events_db.exists():
        with db.connect(events_db) as conn:
            row = conn.execute(
                "SELECT MAX(timestamp) as ts FROM events WHERE agent_id = ? AND event_type = 'session_start'",
                (agent_id,),
            ).fetchone()
            if row["ts"]:
                session_start = row["ts"]

            row = conn.execute(
                "SELECT MAX(timestamp) as ts FROM events WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            if row["ts"]:
                last_event = row["ts"]

            row = conn.execute(
                "SELECT COUNT(*) as count FROM events WHERE agent_id = ? AND event_type = 'session_start'",
                (agent_id,),
            ).fetchone()
            spawn_count = row["count"]

    now = datetime.now()
    if session_start and last_event and session_start == last_event:
        elapsed = now - datetime.fromtimestamp(session_start)
        mins = int(elapsed.total_seconds() / 60)
        time_display = f"Active {mins}m" if mins < 60 else f"Active {int(mins / 60)}h {mins % 60}m"
    elif last_event:
        last_dt = datetime.fromtimestamp(last_event)
        elapsed = now - last_dt
        mins = int(elapsed.total_seconds() / 60)
        if mins < 60:
            time_display = f"Idle {mins}m"
        elif mins < 1440:
            time_display = f"Idle {int(mins / 60)}h"
        else:
            time_display = f"Idle {int(mins / 1440)}d"
    else:
        time_display = None

    summary = None
    if memory_db.exists():
        with db.connect(memory_db) as conn:
            row = conn.execute(
                "SELECT message FROM memory WHERE agent_id = ? AND topic = 'summary' AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
            if row:
                summary = row["message"]

    core_memories = []
    if memory_db.exists():
        with db.connect(memory_db) as conn:
            rows = conn.execute(
                "SELECT topic, message FROM memory WHERE agent_id = ? AND core = 1 AND archived_at IS NULL ORDER BY created_at DESC",
                (agent_id,),
            ).fetchall()
            core_memories = [(r["topic"], r["message"]) for r in rows]

    knowledge_count = 0
    if knowledge_db.exists():
        with db.connect(knowledge_db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM knowledge WHERE agent_id = ? AND archived_at IS NULL",
                (agent_id,),
            ).fetchone()
            knowledge_count = row["count"]

    msg_count = 0
    if bridge_db.exists():
        with db.connect(bridge_db) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM messages WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            msg_count = row["count"]

    if time_display:
        typer.echo(time_display)
    typer.echo(f"Spawns: {spawn_count} | Messages: {msg_count} | Knowledge: {knowledge_count}")
    typer.echo()

    if summary:
        typer.echo("Last session:")
        typer.echo(f"  {summary}")
        typer.echo()

    if core_memories:
        typer.echo("Core memories:")
        for topic, msg in core_memories:
            typer.echo(f"  [{topic}] {msg}")
