import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import click

from . import events, protocols
from . import stats as space_stats
from .spawn import config as spawn_config
from .spawn import registry

PROTOCOL_FILE = Path(__file__).parent.parent / "protocols" / "space.md"
if PROTOCOL_FILE.exists():
    protocols.track("space", PROTOCOL_FILE.read_text())


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        if PROTOCOL_FILE.exists():
            click.echo(PROTOCOL_FILE.read_text())
        else:
            click.echo("space backup - backup workspace to ~/.space/backups/")


@main.command()
def backup():
    """Backup workspace .space directory to ~/.space/backups/"""
    workspace_space = Path.cwd() / ".space"
    if not workspace_space.exists():
        click.echo("No .space directory in current workspace")
        return

    backup_root = Path.home() / ".space" / "backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / timestamp

    shutil.copytree(workspace_space, backup_path)
    click.echo(f"Backed up to {backup_path}")


@main.command(name="events")
@click.option("--source", help="Filter by source (bridge, memory, spawn)")
@click.option("--identity", help="Filter by identity")
@click.option("--limit", default=50, help="Number of events to show")
def show_events(source, identity, limit):
    """Show recent events from append-only log."""
    rows = events.query(source=source, identity=identity, limit=limit)
    if not rows:
        click.echo("No events found")
        return

    for uuid, src, ident, event_type, data, created_at in rows:
        ts = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
        ident_str = f" [{ident}]" if ident else ""
        data_str = f" {data}" if data else ""
        click.echo(f"[{uuid[:8]}] {ts} {src}.{event_type}{ident_str}{data_str}")


@main.command()
def agents():
    registry.init_db()
    regs = registry.list_registrations()
    if not regs:
        click.echo("No agents registered")
        return

    seen = set()
    for reg in regs:
        if reg.sender_id in seen:
            continue
        seen.add(reg.sender_id)
        self_desc = registry.get_self_description(reg.sender_id)
        click.echo(f"{reg.sender_id}: {self_desc}" if self_desc else reg.sender_id)


@main.command()
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
    click.echo("\n\n".join(sections))


@main.command()
@click.argument("identity")
@click.argument("description")
def describe(identity, description):
    registry.init_db()
    db = spawn_config.workspace_root() / ".space" / "spawn.db"
    conn = sqlite3.connect(db)
    changes = conn.execute(
        "UPDATE registrations SET self = ? WHERE sender_id = ?", (description, identity)
    ).rowcount
    conn.commit()
    conn.close()
    click.echo(f"{identity}: {description}" if changes > 0 else f"No agent: {identity}")


@main.command()
@click.argument("identity")
def self(identity):
    registry.init_db()
    desc = registry.get_self_description(identity)
    click.echo(desc if desc else f"No self-description for {identity}")


if __name__ == "__main__":
    main()
