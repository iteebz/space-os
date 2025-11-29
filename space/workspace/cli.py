import typer

from space.lib import backup
from space.workspace import health, init, stats

app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(ctx: typer.Context):
    """Agent Orchestration System

    Manage agents, their memories, shared knowledge, and coordination."""
    from space.cli import output

    output.init_context(ctx, json_output=False, quiet_output=False, identity=None)

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        typer.echo("\nAgent primitives (direct agent access):")
        typer.echo("  bridge    — async messaging and coordination")
        typer.echo("  memory    — single-agent private working memory")
        typer.echo("  knowledge — multi-agent shared discoveries")
        typer.echo("  task      — shared work ledger for swarm coordination")
        typer.echo("  context   — unified retrieval across all primitives")
        typer.echo("  spawn     — constitutional identity and lifecycle")
        typer.echo("\nUsage: bridge/memory/knowledge/task/context/spawn --help")


init_app = typer.Typer()


@init_app.callback(invoke_without_command=True)
def init_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(init_cmd)


@init_app.command()
def init_cmd():
    """Initialize space workspace structure and databases."""
    init.init()


stats_app = typer.Typer(invoke_without_command=True)


@stats_app.callback(invoke_without_command=True)
def stats_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _show_overview()


def _show_overview():
    """Show space overview."""
    s = stats.collect(agent_limit=10)

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

    if s.sessions and s.sessions.available and s.sessions.total_sessions > 0:
        total_tokens = s.sessions.input_tokens + s.sessions.output_tokens
        lines.append(
            f"  sessions · {s.sessions.total_sessions} total · {s.sessions.total_messages} messages · {s.sessions.total_tools_used} tools · {total_tokens:,} tokens"
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


health_app = typer.Typer()


@health_app.callback(invoke_without_command=True)
def health_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(health_cmd)


@health_app.command()
def health_cmd():
    """Verify space-os lattice integrity."""
    issues, counts_by_db = health.run_all_checks()

    for db_name, tables_counts in counts_by_db.items():
        for tbl, cnt in tables_counts.items():
            typer.echo(f"✓ {db_name}::{tbl} ({cnt} rows)")

    if issues:
        for issue in issues:
            typer.echo(issue)
        raise typer.Exit(1)

    typer.echo("\n✓ Space infrastructure healthy")


identity_app = typer.Typer()


@identity_app.command(name="set")
def identity_set_cmd(name: str):
    """Set your human identity (default: human)."""
    from space.os.spawn import agents

    if " " in name:
        typer.echo("Identity cannot contain spaces. Use hyphens instead.", err=True)
        raise typer.Exit(1)

    # Check if identity already exists as an agent
    existing = agents.get_agent(name)
    if existing and existing.model:
        typer.echo(
            f"Identity '{name}' already registered as agent. Choose different name.", err=True
        )
        raise typer.Exit(1)

    # Get current human identity
    human_agent = agents.get_agent("human")
    if not human_agent:
        typer.echo("No human identity found. Run: space init", err=True)
        raise typer.Exit(1)

    if name == "human":
        typer.echo("Already set to: human")
        return

    # Rename human -> new identity
    success = agents.rename_agent("human", name)
    if not success:
        typer.echo(f"Failed to set identity to: {name}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Identity set to: {name}")


@identity_app.command(name="get")
def identity_get_cmd():
    """Show your current identity."""
    from space.lib import store

    with store.ensure() as conn:
        row = conn.execute("SELECT identity FROM agents WHERE model IS NULL LIMIT 1").fetchone()

    if row:
        typer.echo(row[0])
    else:
        typer.echo("No human identity found. Run: space init", err=True)
        raise typer.Exit(1)


app.add_typer(identity_app, name="identity", help="Manage your human identity.")
app.add_typer(init_app, name="init", help="Initialize space workspace structure and databases.")
app.add_typer(backup.app, name="backup", help="Backup and restore space data.")
app.add_typer(stats_app, name="stats", help="Show space overview and agent statistics.")
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
