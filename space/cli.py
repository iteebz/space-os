import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import typer

from . import events
from . import stats as space_stats
from .knowledge.cli import app as knowledge_app
from .lib import protocols
from .memory.cli import app as memory_app
from .spawn import registry

app = typer.Typer(invoke_without_command=True)
agents_app = typer.Typer(invoke_without_command=True)

app.add_typer(knowledge_app, name="knowledge")
app.add_typer(memory_app, name="memory")
app.add_typer(agents_app, name="agents")


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
):
    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        try:
            typer.echo(protocols.load("space"))
        except FileNotFoundError:
            typer.echo("❌ space.md protocol not found")


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


def main() -> None:
    """Entry point for poetry script."""
    app()
