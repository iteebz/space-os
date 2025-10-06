import shutil
from datetime import datetime
from pathlib import Path

import click

from space import events
from space import stats as space_stats
from space.lib import fs

from .bridge import bridge_group
from .knowledge import knowledge_group  # Import the new knowledge_group
from .memory import memory_group  # Import the new memory_group
from .spawn import registry, spawn_group

GUIDE_FILE = fs.guide_path("space.md")


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        if GUIDE_FILE.exists():
            click.echo(GUIDE_FILE.read_text())
        else:
            click.echo("space backup - backup workspace to ~/.space/backups/")


@main.group()
def system():
    """System-level commands for Space."""
    pass


@system.command(name="backup")
def system_backup():
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
    shutil.copytree(workspace_space, backup_path)
    click.echo(f"Backed up to {backup_path}")


main.add_command(bridge_group)
main.add_command(spawn_group)
main.add_command(memory_group)
main.add_command(knowledge_group)


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
    regs = registry.list()
    if not regs:
        click.echo("No agents registered")
        return

    seen = set()
    for reg in regs:
        if reg.agent_id in seen:
            continue
        seen.add(reg.agent_id)
        click.echo(f"{reg.agent_id}: {reg.role}")


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
    changes = registry.set_self_description(identity, description)
    click.echo(f"{identity}: {description}" if changes > 0 else f"No agent: {identity}")


@main.command()
@click.argument("identity")
def self(identity):
    registry.init_db()
    desc = registry.get_self_description(identity)
    click.echo(desc if desc else f"No self-description for {identity}")


if __name__ == "__main__":
    main()
