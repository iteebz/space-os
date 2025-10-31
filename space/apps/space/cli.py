"""Space orchestrator CLI: unified human interface."""

import click
import typer
from typer.core import TyperGroup

from space.apps.space import api
from space.lib import backup, paths
from space.os.spawn import api as spawn_api


class SpawnGroup(TyperGroup):
    """Custom group to support dynamic agent spawning."""

    def get_command(self, ctx, cmd_name):
        """Get command by name, or spawn agent if not found."""
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        agent = spawn_api.get_agent(cmd_name)
        if agent is None:
            return None

        @click.command(name=cmd_name)
        @click.argument("task_input", required=False, nargs=-1)
        def spawn_agent(task_input):
            input_list = list(task_input) if task_input else []
            spawn_api.spawn_agent(agent.identity, extra_args=input_list)

        return spawn_agent


app = typer.Typer(
    invoke_without_command=True, no_args_is_help=False, cls=SpawnGroup, add_completion=False
)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """Agent Orchestration System

    Manage agents, their memories, shared knowledge, and coordination."""
    from space.lib import output

    output.set_flags(ctx, False, False)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["identity"] = None
    ctx.obj["json"] = False
    ctx.obj["quiet"] = False

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        typer.echo("\nAgent primitives (direct agent access):")
        typer.echo("  bridge    — async messaging and coordination")
        typer.echo("  memory    — single-agent private working memory")
        typer.echo("  knowledge — multi-agent shared discoveries")
        typer.echo("  context   — unified retrieval across all primitives")
        typer.echo("  spawn     — constitutional identity and lifecycle")
        typer.echo("\nUsage: bridge/memory/knowledge/context/spawn --help")


init_app = typer.Typer()


@init_app.callback(invoke_without_command=True)
def init_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(init_cmd)


@init_app.command()
def init_cmd():
    """Initialize space workspace structure and databases."""
    api.init.init()


stats_app = typer.Typer(invoke_without_command=True)


@stats_app.callback(invoke_without_command=True)
def stats_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _show_overview()


def _show_overview():
    """Show space overview."""
    s = api.stats.collect(agent_limit=10)

    lines = [
        """
   ___ _ __   __ _  ___ ___
  / __| '_ \\ / _` |/ __/ _ \\
 _\\__ \\ |_) | (_| | (_|  __/
(_)___/ .__/ \\__,_|\\___\\___|
      | |
      |_|

overview"""
    ]

    if s.spawn.available and s.spawn.total > 0:
        lines.append(
            f"  spawn · {s.spawn.total} spawns · {s.spawn.agents} agents · {s.spawn.hashes} hashes"
        )

    if s.bridge.available:
        lines.append(
            f"  bridge · {s.bridge.active_channels} active · {s.bridge.archived_channels} archived · {s.bridge.active} msgs ({s.bridge.archived} archived)"
        )

    if s.memory.available and s.memory.total > 0:
        archived = s.memory.total - s.memory.active
        lines.append(
            f"  memory · {s.memory.active} active · {archived} archived · {s.memory.topics} topics"
        )

    if s.knowledge.available and s.knowledge.total > 0:
        archived_k = s.knowledge.total - s.knowledge.active
        lines.append(
            f"  knowledge · {s.knowledge.active} active · {archived_k} archived · {s.knowledge.topics} domains"
        )

    if s.agents:
        lines.append("\nagents")
        lines.append("  name · id · e-s-b-m-k")

        sorted_agents = sorted(
            s.agents, key=lambda a: int(a.last_active) if a.last_active else 0, reverse=True
        )

        for a in sorted_agents:
            parts = [a.identity]
            parts.append(f"{a.events}-{a.spawns}-{a.msgs}-{a.mems}-{a.knowledge}")
            lines.append("  " + " · ".join(parts))

    typer.echo("\n".join(lines) + "\n")


chats_app = typer.Typer()


@chats_app.callback(invoke_without_command=True)
def chats_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(chats_stats)


@chats_app.command()
def sync():
    """Sync chats from ~/.claude, ~/.codex, ~/.gemini to ~/.space/chats/."""
    results = api.chats.sync_all_providers()

    typer.echo("✓ Chat sync complete")
    typer.echo()
    typer.echo(f"{'Provider':<10} {'Discovered':<12} {'Synced'}")
    typer.echo("-" * 40)

    total_discovered = 0
    total_synced = 0

    for provider in ("claude", "codex", "gemini"):
        discovered, synced = results.get(provider, (0, 0))
        total_discovered += discovered
        total_synced += synced
        status = "✓" if synced > 0 else "-"
        typer.echo(f"{provider:<10} {discovered:<12} {synced:<12} {status}")

    typer.echo("-" * 40)
    typer.echo(f"{'TOTAL':<10} {total_discovered:<12} {total_synced}")


@chats_app.command(name="stats")
def chats_stats():
    """Show chat statistics across providers."""
    provider_stats = api.chats.get_provider_stats()

    if not provider_stats:
        typer.echo("No chats synced yet. Run: space chats sync")
        return

    typer.echo("Chat statistics:")
    typer.echo()
    typer.echo(f"{'Provider':<12} {'Sessions':<12} {'Size (MB)'}")
    typer.echo("-" * 40)

    total_files = 0
    total_size = 0

    for provider in sorted(provider_stats.keys()):
        stats_dict = provider_stats[provider]
        total_files += stats_dict["files"]
        total_size += stats_dict["size_mb"]
        typer.echo(f"{provider:<12} {stats_dict['files']:<12} {stats_dict['size_mb']:>10.1f}")

    typer.echo("-" * 40)
    typer.echo(f"{'TOTAL':<12} {total_files:<12} {total_size:>10.1f}")
    typer.echo()
    typer.echo(f"Location: {paths.chats_dir()}")


health_app = typer.Typer()


@health_app.callback(invoke_without_command=True)
def health_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(health_cmd)


@health_app.command()
def health_cmd():
    """Verify space-os lattice integrity."""
    issues, counts_by_db = api.health.run_all_checks()

    for db_name, tables_counts in counts_by_db.items():
        for tbl, cnt in tables_counts.items():
            typer.echo(f"✓ {db_name}::{tbl} ({cnt} rows)")

    if issues:
        for issue in issues:
            typer.echo(issue)
        raise typer.Exit(1)

    typer.echo("\n✓ Space infrastructure healthy")


app.add_typer(init_app, name="init", help="Initialize space workspace structure and databases.")
app.add_typer(backup.app, name="backup", help="Backup and restore space data.")
app.add_typer(stats_app, name="stats", help="Show space overview and agent statistics.")
app.add_typer(chats_app, name="chats", help="Sync and view chat statistics across providers.")
app.add_typer(health_app, name="health", help="Verify space-os lattice integrity.")


def main() -> None:
    """Entry point for space command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main"]
