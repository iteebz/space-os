import sqlite3
from datetime import datetime

import typer

from space.os import db
from space.os.lib import paths
from space.os.spawn import db as spawn_db


def check(
    agent: str = typer.Argument(..., help="Agent name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet_output: bool = typer.Option(False, "--quiet", help="Suppress output"),
):
    """Show agent dashboard: summary, memories, stats."""
    try:
        agent_id = spawn_db.get_agent_id(agent)
        if not agent_id:
            typer.echo(f"Agent {agent} not found")
            raise typer.Exit(1)

        with spawn_db.connect() as conn:
            row = conn.execute(
                "SELECT name, self_description FROM agents WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            name = row["name"]
            self_desc = row["self_description"]

        typer.echo(f"Agent: {name}")
        if self_desc:
            typer.echo(f"Self: {self_desc}")
        typer.echo()

        events_db = paths.dot_space() / "events.db"
        memory_db = paths.dot_space() / "memory.db"
        knowledge_db = paths.dot_space() / "knowledge.db"
        bridge_db = paths.dot_space() / "bridge.db"

        session_start = None
        last_event = None
        spawn_count = 0

        registry_map = {"events.db": "events", "memory.db": "memory", "knowledge.db": "knowledge", "bridge.db": "bridge"}

        def safe_fetch(db_path, query, params=(), default=None, fetch="one"):
            if not db_path.exists():
                return default
            try:
                registry_name = registry_map.get(db_path.name)
                if not registry_name:
                    return default
                with db.ensure(registry_name) as conn:
                    cursor = conn.execute(query, params)
                    if fetch == "all":
                        rows = cursor.fetchall()
                        return rows if rows else default
                    row = cursor.fetchone()
                    return row if row else default
            except sqlite3.OperationalError:
                return default

        if events_db.exists():
            row = safe_fetch(
                events_db,
                "SELECT MAX(timestamp) as ts FROM events WHERE agent_id = ? AND event_type = 'session_start'",
                (agent_id,),
            )
            if row and row["ts"]:
                session_start = row["ts"]

            row = safe_fetch(
                events_db,
                "SELECT MAX(timestamp) as ts FROM events WHERE agent_id = ?",
                (agent_id,),
            )
            if row and row["ts"]:
                last_event = row["ts"]

            row = safe_fetch(
                events_db,
                "SELECT COUNT(*) as count FROM events WHERE agent_id = ? AND event_type = 'session_start'",
                (agent_id,),
            )
            spawn_count = row["count"] if row else 0

        now = datetime.now()
        if session_start and last_event and session_start == last_event:
            elapsed = now - datetime.fromtimestamp(session_start)
            mins = int(elapsed.total_seconds() / 60)
            time_display = (
                f"Active {mins}m" if mins < 60 else f"Active {int(mins / 60)}h {mins % 60}m"
            )
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

        row = safe_fetch(
            memory_db,
            "SELECT message FROM memories WHERE agent_id = ? AND topic = 'summary' AND archived_at IS NULL ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        )
        summary = row["message"] if row else None

        rows = safe_fetch(
            memory_db,
            "SELECT topic, message FROM memories WHERE agent_id = ? AND core = 1 AND archived_at IS NULL ORDER BY created_at DESC",
            (agent_id,),
            default=[],
            fetch="all",
        )
        core_memories = [(r["topic"], r["message"]) for r in rows] if rows else []

        row = safe_fetch(
            knowledge_db,
            "SELECT COUNT(*) as count FROM knowledge WHERE agent_id = ? AND archived_at IS NULL",
            (agent_id,),
        )
        knowledge_count = row["count"] if row else 0

        row = safe_fetch(
            bridge_db,
            "SELECT COUNT(*) as count FROM messages WHERE agent_id = ?",
            (agent_id,),
        )
        msg_count = row["count"] if row else 0

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
    except Exception as e:
        typer.echo(f"An unexpected error occurred: {e}", err=True)
        raise typer.Exit(1) from e
