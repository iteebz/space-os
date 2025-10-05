import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import click

from . import events, protocols
from .spawn import config as spawn_config
from . import stats as space_stats


def humanize_ago(timestamp_str: str | None) -> str:
    if not timestamp_str:
        return "–"
    
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - ts
        
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            mins = seconds // 60
            return f"{mins}m ago"
        if seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        days = seconds // 86400
        if days < 30:
            return f"{days}d ago"
        if days < 365:
            months = days // 30
            return f"{months}mo ago"
        years = days // 365
        return f"{years}y ago"
    except (ValueError, AttributeError):
        return timestamp_str

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
    """List current agent identities with self-descriptions."""
    spawn_db = spawn_config.workspace_root() / ".space" / "spawn.db"
    
    if not spawn_db.exists():
        click.echo("No spawn.db found")
        return
    
    conn = sqlite3.connect(str(spawn_db))
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sender_id, self FROM registrations ORDER BY sender_id")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    
    if not rows:
        click.echo("No agents registered")
        return
    
    seen = set()
    for sender_id, self_desc in rows:
        if sender_id in seen:
            continue
        seen.add(sender_id)
        if self_desc:
            click.echo(f"{sender_id}: {self_desc}")
        else:
            click.echo(sender_id)


@main.command()
def stats():
    """Show high-level workspace stats across coordination subsystems."""

    stats = space_stats.collect()

    sections: list[str] = []

    if stats.bridge.available:
        bridge_lines = ["Bridge"]
        
        if stats.bridge.message_leaderboard:
            for index, item in enumerate(stats.bridge.message_leaderboard, start=1):
                bridge_lines.append(f"  {index}. {item.identity} — {item.count}")

        sections.append("\n".join(bridge_lines))
    else:
        sections.append("Bridge\n- No bridge.db found")

    if stats.memory.available:
        memory_lines = ["Memory"]
        
        if stats.memory.leaderboard:
            for index, item in enumerate(stats.memory.leaderboard[:5], start=1):
                memory_lines.append(f"  {index}. {item.identity} — {item.count}")

        sections.append("\n".join(memory_lines))
    else:
        sections.append("Memory\n- No memory.db found")

    if stats.knowledge.available:
        knowledge_lines = ["Knowledge"]
        
        if stats.knowledge.leaderboard:
            for index, item in enumerate(stats.knowledge.leaderboard[:5], start=1):
                knowledge_lines.append(f"  {index}. {item.identity} — {item.count}")

        sections.append("\n".join(knowledge_lines))
    else:
        sections.append("Knowledge\n- No knowledge.db found")

    click.echo("\n\n".join(sections))


@main.command()
@click.argument("identity")
@click.argument("description")
def describe(identity, description):
    """Update agent self-description."""
    spawn_db = spawn_config.workspace_root() / ".space" / "spawn.db"
    
    if not spawn_db.exists():
        click.echo("No spawn.db found")
        return
    
    conn = sqlite3.connect(str(spawn_db))
    cursor = conn.cursor()
    cursor.execute("UPDATE registrations SET self = ? WHERE sender_id = ?", (description, identity))
    changes = cursor.rowcount
    conn.commit()
    conn.close()
    
    if changes > 0:
        click.echo(f"{identity}: {description}")
    else:
        click.echo(f"No agent found with identity: {identity}")


@main.command()
@click.argument("identity")
def self(identity):
    """Show agent self-description."""
    spawn_db = spawn_config.workspace_root() / ".space" / "spawn.db"
    
    if not spawn_db.exists():
        click.echo("No spawn.db found")
        return
    
    conn = sqlite3.connect(str(spawn_db))
    cursor = conn.cursor()
    cursor.execute("SELECT self FROM registrations WHERE sender_id = ? LIMIT 1", (identity,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:
        click.echo(row[0])
    else:
        click.echo(f"No self-description for {identity}")


if __name__ == "__main__":
    main()
