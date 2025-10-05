import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import click

from . import events, protocols

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


@main.command()
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
    """List current agent identities."""
    space_dir = Path.cwd() / ".space"
    spawn_db = space_dir / "spawn.db"
    bridge_db = space_dir / "bridge.db"
    
    identities = set()
    
    if spawn_db.exists():
        conn = sqlite3.connect(spawn_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT sender_id FROM registrations ORDER BY sender_id")
            identities.update(row[0] for row in cursor.fetchall())
        except sqlite3.OperationalError:
            pass
        conn.close()
    
    if bridge_db.exists():
        conn = sqlite3.connect(bridge_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT sender FROM messages ORDER BY sender")
            identities.update(row[0] for row in cursor.fetchall())
        except sqlite3.OperationalError:
            pass
        conn.close()
    
    if not identities:
        click.echo("No agents found")
        return
    
    for sender_id in sorted(identities):
        click.echo(sender_id)


if __name__ == "__main__":
    main()
