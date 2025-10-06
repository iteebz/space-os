import shutil
from datetime import datetime
from pathlib import Path

import click

from space.os import events, stats
from space.apps import register
from space.apps.register import api as register_api


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        onboarding_guide_content = register_api.load_guide_content("onboarding")
        if onboarding_guide_content:
            click.echo(onboarding_guide_content)
        else:
            click.echo("No onboarding guide found. Create space/apps/register/prompts/guides/onboarding.md")


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
    click.echo(f"Backed up to {backup_path}")


# Dynamic discovery and registration of app CLI groups
import pkgutil
import importlib
from pathlib import Path

space_apps_path = Path(__file__).parent / "apps"

for finder, name, ispkg in pkgutil.iter_modules([str(space_apps_path)]):
    if ispkg:  # Only consider packages (directories)
        try:
            # Dynamically import the cli module of the app
            app_cli_module = importlib.import_module(f"space.apps.{name}.cli")
            
            # Assuming the click group is named as <app_name>_group
            group_name = f"{name}_group"
            app_group = getattr(app_cli_module, group_name)
            
            main.add_command(app_group)
        except (ImportError, AttributeError) as e:
            # Handle cases where an app might not have a cli.py or the group is named differently
            click.echo(f"Warning: Could not load CLI for app '{name}': {e}", err=True)


@main.command(name="events")
@click.option("--source", help="Filter by source (bridge, memory, spawn)")
@click.option("--identity", help="Filter by identity")
@click.option("--limit", default=50, help="Number of events to show")
def show_events(source, identity, limit):
    """Show recent events from append-only log."""
    rows = events.events.query(source=source, identity=identity, limit=limit)
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
    register.init()
    regs = register.view()
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
    s = stats.collect()

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
    register.init()
    changes = register.set_self_description(identity, description)
    click.echo(f"{identity}: {description}" if changes > 0 else f"No agent: {identity}")


@main.command()
@click.argument("identity")
def self(identity):
    register.init()
    desc = register.get_self_description(identity)
    click.echo(desc if desc else f"No self-description for {identity}")


if __name__ == "__main__":
    main()
