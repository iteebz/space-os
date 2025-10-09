import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import typer

from . import events
from . import stats as space_stats
from .events import DB_PATH
from .lib import db as libdb
from .handover.cli import app as handover_app
from .knowledge.cli import app as knowledge_app
from .lib import lattice
from .memory.cli import app as memory_app
from .spawn import registry

app = typer.Typer(invoke_without_command=True)
agents_app = typer.Typer(invoke_without_command=True)

app.add_typer(handover_app, name="handover")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agents_app, name="agents")


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        try:
            typer.echo(lattice.load("## Orientation"))
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ Orientation section not found in README: {e}")


@app.command()
def backup(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Backup workspace .space directory to ~/.space/backups/"""
    workspace_space = Path.cwd() / ".space"
    if not workspace_space.exists():
        if not quiet_output:
            typer.echo("No .space directory in current workspace")
        raise typer.Exit(code=1)

    backup_root = Path.home() / ".space" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / timestamp

    shutil.copytree(workspace_space, backup_path)
    if json_output:
        typer.echo(json.dumps({"backup_path": str(backup_path)}))
    elif not quiet_output:
        typer.echo(f"Backed up to {backup_path}")


@app.command(name="events")
def show_events(
    source: str = typer.Option(None, help="Filter by source (bridge, memory, spawn)"),
    identity: str = typer.Option(None, help="Filter by identity"),
    limit: int = typer.Option(50, help="Number of events to show"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show recent events from append-only log."""
    rows = events.query(source=source, identity=identity, limit=limit)
    if not rows:
        if not quiet_output:
            typer.echo("No events found")
        if json_output:
            typer.echo(json.dumps([]))
        return

    if json_output:
        # Convert rows to a list of dictionaries for JSON output
        json_rows = []
        for uuid, src, ident, event_type, data, created_at in rows:
            json_rows.append(
                {
                    "uuid": uuid,
                    "source": src,
                    "identity": ident,
                    "event_type": event_type,
                    "data": data,
                    "created_at": datetime.fromtimestamp(created_at).isoformat(),
                }
            )
        typer.echo(json.dumps(json_rows))
    elif not quiet_output:
        for uuid, src, ident, event_type, data, created_at in rows:
            ts = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            ident_str = f" [{ident}]" if ident else ""
            data_str = f" {data}" if data else ""
            typer.echo(f"[{uuid[:8]}] {ts} {src}.{event_type}{ident_str}{data_str}")


def _agent_io_flags(ctx: typer.Context) -> tuple[bool, bool]:
    """Extract json/quiet flags from the parent callback context."""
    parent = ctx.parent
    if parent and isinstance(parent.obj, dict):
        return parent.obj.get("json_output", False), parent.obj.get("quiet_output", False)
    return False, False


def _list_agents(json_output: bool, quiet_output: bool):
    """Render registered agents honoring output flags."""
    registry.init_db()
    regs = registry.list_registrations()
    if not regs:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No agents registered")
        return

    seen = set()
    unique_agents = []
    for reg in regs:
        if reg.sender_id not in seen:
            seen.add(reg.sender_id)
            self_desc = registry.get_self_description(reg.sender_id)
            unique_agents.append({"sender_id": reg.sender_id, "description": self_desc})

    if json_output:
        typer.echo(json.dumps(unique_agents))
    elif not quiet_output:
        for agent in unique_agents:
            if agent["description"]:
                typer.echo(f"{agent['sender_id']}: {agent['description']}")
            else:
                typer.echo(agent["sender_id"])


@agents_app.callback()
def agents_root(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Agent registry tooling (defaults to listing)."""
    ctx.obj = {"json_output": json_output, "quiet_output": quiet_output}
    if ctx.invoked_subcommand is None:
        _list_agents(json_output, quiet_output)
        raise typer.Exit()


@agents_app.command("list")
def list_agents(
    ctx: typer.Context,
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """List registered agents."""
    parent_json, parent_quiet = _agent_io_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    _list_agents(json_output, quiet_output)


@agents_app.command("describe")
def describe_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to describe"),
    description: str = typer.Argument(..., help="Description of the identity"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Set self-description for an identity."""
    parent_json, parent_quiet = _agent_io_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    updated = registry.set_self_description(identity, description)
    payload = {"identity": identity, "description": description, "updated": updated}

    if json_output:
        typer.echo(json.dumps(payload))
        return

    if quiet_output:
        return

    if updated:
        typer.echo(f"{identity}: {description}")
    else:
        typer.echo(f"No agent: {identity}")


@agents_app.command("show")
def show_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to inspect"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Display self-description for an identity."""
    parent_json, parent_quiet = _agent_io_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    desc = registry.get_self_description(identity)
    payload = {"identity": identity, "description": desc}

    if json_output:
        typer.echo(json.dumps(payload))
        return

    if quiet_output:
        return

    if desc:
        typer.echo(desc)
    else:
        typer.echo(f"No self-description for {identity}")


@agents_app.command("delete")
def delete_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to delete"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Delete an agent from the registry."""
    parent_json, parent_quiet = _agent_io_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    registry.delete_agent(identity)

    if json_output:
        typer.echo(json.dumps({"identity": identity, "deleted": True}))
    elif not quiet_output:
        typer.echo(f"Deleted {identity}")


@agents_app.command("config")
def show_agent_config(
    ctx: typer.Context,
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Show configured agent binaries (claude, gemini, codex)."""
    from .spawn import spawn

    parent_json, parent_quiet = _agent_io_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag

    cfg = spawn.load_config()
    agents = cfg.get("agents", {})

    if json_output:
        typer.echo(json.dumps(agents))
        return

    if quiet_output:
        return

    if not agents:
        typer.echo("No agents configured")
        return

    typer.echo(f"{'AGENT':<10} {'COMMAND':<15} {'TARGETS'}")
    typer.echo("-" * 60)
    for name, agent_cfg in agents.items():
        cmd = agent_cfg.get("command", "")
        targets = agent_cfg.get("identity_targets", [])
        if isinstance(targets, list):
            targets_str = ", ".join([Path(t).name for t in targets])
        else:
            targets_str = Path(targets).name if targets else ""
        typer.echo(f"{name:<10} {cmd:<15} {targets_str}")


@app.command()
def stats(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show space statistics."""
    s = space_stats.collect()

    if json_output:
        typer.echo(json.dumps(asdict(s)))
        return

    if quiet_output:
        return

    def fmt(name: str, available: bool, board: list | None) -> str:
        if not available:
            return f"{name}\n- Not found"
        if not board:
            return name
        total = sum(item.count for item in board)
        header = f"{name}: {total}"
        lines = [header] + [
            f"  {i}. {item.identity} — {item.count}" for i, item in enumerate(board, 1)
        ]
        return "\n".join(lines)

    sections = [
        fmt("bridge", s.bridge.available, s.bridge.message_leaderboard),
        fmt("memory", s.memory.available, s.memory.leaderboard),
        fmt("knowledge", s.knowledge.available, s.knowledge.leaderboard),
    ]
    typer.echo("\n\n".join(sections))


@app.command()
def search(
    keyword: str = typer.Argument(..., help="Keyword to search"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Search across memory, knowledge, and bridge."""
    from .memory import db as memory_db
    from .knowledge import db as knowledge_db
    from .bridge import db as bridge_db

    results = {"memory": [], "knowledge": [], "bridge": []}

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            rows = conn.execute(
                "SELECT identity, topic, message FROM memory WHERE message LIKE ?",
                (f"%{keyword}%",),
            ).fetchall()
            results["memory"] = [{"identity": r[0], "topic": r[1], "message": r[2]} for r in rows]

    if knowledge_db.database_path().exists():
        with knowledge_db.connect() as conn:
            rows = conn.execute(
                "SELECT domain, content, contributor FROM knowledge WHERE content LIKE ? OR domain LIKE ?",
                (f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
            results["knowledge"] = [{"domain": r[0], "content": r[1], "contributor": r[2]} for r in rows]

    from .bridge import config as bridge_config
    if bridge_config.DB_PATH.exists():
        with libdb.connect(bridge_config.DB_PATH) as conn:
            rows = conn.execute(
                "SELECT c.name, m.sender, m.content FROM messages m JOIN channels c ON m.channel_id = c.id WHERE m.content LIKE ?",
                (f"%{keyword}%",),
            ).fetchall()
            results["bridge"] = [{"channel": r[0], "sender": r[1], "content": r[2]} for r in rows]

    if json_output:
        typer.echo(json.dumps(results))
        return

    if quiet_output:
        return

    total = len(results["memory"]) + len(results["knowledge"]) + len(results["bridge"])
    if total == 0:
        typer.echo(f"No results for '{keyword}'")
        return

    typer.echo(f"Found in memory ({len(results['memory'])}), knowledge ({len(results['knowledge'])}), bridge ({len(results['bridge'])})\n")

    if results["memory"]:
        typer.echo("MEMORY:")
        for r in results["memory"][:5]:
            typer.echo(f"  [{r['identity']}] {r['topic']}: {r['message'][:80]}")
        typer.echo()

    if results["knowledge"]:
        typer.echo("KNOWLEDGE:")
        for r in results["knowledge"][:5]:
            typer.echo(f"  [{r['domain']}] {r['content'][:80]}")
        typer.echo()

    if results["bridge"]:
        typer.echo("BRIDGE:")
        for r in results["bridge"][:5]:
            typer.echo(f"  [{r['channel']}] {r['sender']}: {r['content'][:80]}")


@app.command()
def trace(
    concept: str = typer.Argument(..., help="Concept to trace"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Trace concept evolution via provenance reconstruction."""
    from .memory import db as memory_db
    from .knowledge import db as knowledge_db
    from .bridge import config as bridge_config

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


def main() -> None:
    """Entry point for poetry script."""
    app()
