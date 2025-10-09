import json
from datetime import datetime

import typer

from ..bridge import config as bridge_config
from ..events import DB_PATH
from ..knowledge import db as knowledge_db
from ..lib import db as libdb
from ..memory import db as memory_db


def trace(
    concept: str = typer.Argument(..., help="Concept to trace"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Trace concept evolution via provenance reconstruction."""
    timeline = []

    if DB_PATH.exists():
        with libdb.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT id, source, identity, event_type, data, timestamp FROM events WHERE data LIKE ? ORDER BY timestamp ASC",
                (f"%{concept}%",),
            ).fetchall()
            for row in rows:
                timeline.append({
                    "source": "events",
                    "type": f"{row[1]}.{row[3]}",
                    "identity": row[2],
                    "data": row[4],
                    "timestamp": row[5],
                })

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            rows = conn.execute(
                "SELECT identity, topic, message, created_at FROM memory WHERE message LIKE ? OR topic LIKE ? ORDER BY created_at ASC",
                (f"%{concept}%", f"%{concept}%"),
            ).fetchall()
            for row in rows:
                timeline.append({
                    "source": "memory",
                    "type": row[1],
                    "identity": row[0],
                    "data": row[2],
                    "timestamp": row[3] if isinstance(row[3], int) else 0,
                })

    if knowledge_db.database_path().exists():
        with knowledge_db.connect() as conn:
            rows = conn.execute(
                "SELECT domain, content, contributor, created_at FROM knowledge WHERE content LIKE ? OR domain LIKE ? ORDER BY created_at ASC",
                (f"%{concept}%", f"%{concept}%"),
            ).fetchall()
            for row in rows:
                timeline.append({
                    "source": "knowledge",
                    "type": row[0],
                    "identity": row[2],
                    "data": row[1],
                    "timestamp": row[3] if isinstance(row[3], int) else 0,
                })

    if bridge_config.DB_PATH.exists():
        with libdb.connect(bridge_config.DB_PATH) as conn:
            rows = conn.execute(
                "SELECT c.name, m.sender, m.content, m.created_at FROM messages m JOIN channels c ON m.channel_id = c.id WHERE m.content LIKE ? OR c.name LIKE ? ORDER BY m.created_at ASC",
                (f"%{concept}%", f"%{concept}%"),
            ).fetchall()
            for row in rows:
                ts = 0
                if row[3]:
                    try:
                        ts = int(datetime.fromisoformat(row[3]).timestamp())
                    except (ValueError, TypeError):
                        ts = row[3] if isinstance(row[3], int) else 0
                timeline.append({
                    "source": "bridge",
                    "type": row[0],
                    "identity": row[1],
                    "data": row[2],
                    "timestamp": ts,
                })

    timeline.sort(key=lambda x: x["timestamp"])

    if json_output:
        typer.echo(json.dumps(timeline))
        return

    if quiet_output:
        return

    if not timeline:
        typer.echo(f"No provenance trail for '{concept}'")
        return

    typer.echo(f"Concept archaeology: {concept}\n")
    for entry in timeline:
        ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
        source = entry["source"]
        typ = entry["type"]
        identity = entry["identity"] or "system"
        data = entry["data"][:100] if entry["data"] else ""
        typer.echo(f"[{ts}] {source}.{typ} ({identity})")
        typer.echo(f"  {data}\n")
