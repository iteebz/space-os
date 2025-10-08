import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import typer

from . import events
from . import stats as space_stats
from .lib import protocols
from .spawn import config as spawn_config
from .spawn import registry

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def main_command(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        try:
            typer.echo(protocols.load("space"))
        except FileNotFoundError:
            typer.echo("❌ space.md protocol not found")


@app.command()
def backup():
    """Backup workspace .space directory to ~/.space/backups/"""
    workspace_space = Path.cwd() / ".space"
    if not workspace_space.exists():
        typer.echo("No .space directory in current workspace")
        return

    backup_root = Path.home() / ".space" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / timestamp

    shutil.copytree(workspace_space, backup_path)
    typer.echo(f"Backed up to {backup_path}")


@app.command(name="events")
def show_events(
    source: str = typer.Option(None, help="Filter by source (bridge, memory, spawn)"),
    identity: str = typer.Option(None, help="Filter by identity"),
    limit: int = typer.Option(50, help="Number of events to show"),
):
    """Show recent events from append-only log."""
    rows = events.query(source=source, identity=identity, limit=limit)
    if not rows:
        typer.echo("No events found")
        return

    for uuid, src, ident, event_type, data, created_at in rows:
        ts = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
        ident_str = f" [{ident}]" if ident else ""
        data_str = f" {data}" if data else ""
        typer.echo(f"[{uuid[:8]}] {ts} {src}.{event_type}{ident_str}{data_str}")


@app.command()
def agents():
    registry.init_db()
    regs = registry.list_registrations()
    if not regs:
        typer.echo("No agents registered")
        return

    seen = set()
    for reg in regs:
        if reg.sender_id in seen:
            continue
        seen.add(reg.sender_id)
        self_desc = registry.get_self_description(reg.sender_id)
        typer.echo(f"{reg.sender_id}: {self_desc}" if self_desc else reg.sender_id)


@app.command()
def stats():
    s = space_stats.collect()

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
def describe(
    identity: str = typer.Argument(..., help="Identity to describe"),
    description: str = typer.Argument(..., help="Description of the identity"),
):
    registry.init_db()
    db = spawn_config.workspace_root() / ".space" / "spawn.db"
    conn = sqlite3.connect(db)
    changes = conn.execute(
        "UPDATE registrations SET self = ? WHERE sender_id = ?", (description, identity)
    ).rowcount
    conn.commit()
    conn.close()
    typer.echo(f"{identity}: {description}" if changes > 0 else f"No agent: {identity}")


@app.command()
def self(
    identity: str = typer.Argument(..., help="Identity to get self-description for"),
):
    registry.init_db()
    desc = registry.get_self_description(identity)
    typer.echo(desc if desc else f"No self-description for {identity}")


if __name__ == "__main__":
    app()
