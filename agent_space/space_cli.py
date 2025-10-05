import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import click

from . import events, protocols
from .bridge import config as bridge_config
from .spawn import config as spawn_config

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

    space_dir = spawn_config.workspace_root() / ".space"

    bridge_db = bridge_config.DB_PATH
    spawn_db = space_dir / "spawn.db"
    memory_db = space_dir / "memory.db"

    sections: list[str] = []

    # Bridge statistics
    if bridge_db.exists():
        try:
            with sqlite3.connect(bridge_db) as conn:
                conn.row_factory = sqlite3.Row
                total_channels = conn.execute("SELECT COUNT(*) AS count FROM channels").fetchone()["count"]
                total_messages = conn.execute("SELECT COUNT(*) AS count FROM messages").fetchone()["count"]
                active_24h = conn.execute(
                    """
                    SELECT COUNT(DISTINCT channel_id) AS count
                    FROM messages
                    WHERE created_at >= datetime('now', '-24 hours')
                    """
                ).fetchone()["count"]
                top_channels = conn.execute(
                    """
                    SELECT c.name AS name,
                           COUNT(m.id) AS messages,
                           MAX(m.created_at) AS last_activity
                    FROM channels c
                    LEFT JOIN messages m ON c.id = m.channel_id
                    GROUP BY c.id, c.name
                    ORDER BY messages DESC, c.created_at DESC
                    LIMIT 5
                    """
                ).fetchall()
        except sqlite3.OperationalError:
            total_channels = total_messages = active_24h = 0
            top_channels = []

        bridge_lines = [
            "Bridge",
            f"- Channels: {total_channels} (active last 24h: {active_24h})",
            f"- Messages: {total_messages}",
        ]

        if top_channels:
            bridge_lines.append("- Top Channels:")
            for index, row in enumerate(top_channels, start=1):
                last_activity = row["last_activity"] or "–"
                bridge_lines.append(
                    f"  {index}. {row['name']} — {row['messages']} messages (last activity: {last_activity})"
                )

        sections.append("\n".join(bridge_lines))
    else:
        sections.append("Bridge\n- No bridge.db found")

    # Memory statistics
    if memory_db.exists():
        try:
            with sqlite3.connect(memory_db) as conn:
                total_entries = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
                identities = conn.execute("SELECT COUNT(DISTINCT identity) FROM entries").fetchone()[0]
                topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM entries").fetchone()[0]
        except sqlite3.OperationalError:
            total_entries = identities = topics = 0

        sections.append(
            "\n".join(
                [
                    "Memories",
                    f"- Entries: {total_entries}",
                    f"- Identities: {identities}",
                    f"- Topics: {topics}",
                ]
            )
        )
    else:
        sections.append("Memories\n- No memory.db found")

    # Agent statistics
    if spawn_db.exists():
        try:
            with sqlite3.connect(spawn_db) as conn:
                conn.row_factory = sqlite3.Row
                total_registrations = conn.execute(
                    "SELECT COUNT(*) AS count FROM registrations"
                ).fetchone()["count"]
                total_agents = conn.execute(
                    "SELECT COUNT(DISTINCT sender_id) AS count FROM registrations"
                ).fetchone()["count"]
        except sqlite3.OperationalError:
            total_registrations = total_agents = 0

        sections.append(
            "\n".join(
                [
                    "Agents",
                    f"- Unique identities: {total_agents}",
                    f"- Registrations: {total_registrations}",
                ]
            )
        )
    else:
        sections.append("Agents\n- No spawn.db found")

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
