import click
import typer
from typer.core import TyperGroup

from space.apps import canon, chats, council, daemons, health, init, stats
from space.lib import backup
from space.os.spawn import api


class SpawnGroup(TyperGroup):
    """Custom group to support dynamic agent spawning."""

    def get_command(self, ctx, cmd_name):
        """Get command by name, or spawn agent if not found."""
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        agent = api.get_agent(cmd_name)
        if agent is None:
            return None

        @click.command(name=cmd_name)
        @click.argument("task_input", required=False, nargs=-1)
        def spawn_agent(task_input):
            input_list = list(task_input) if task_input else []
            api.spawn_agent(agent.identity, extra_args=input_list)

        return spawn_agent


app = typer.Typer(
    invoke_without_command=True, no_args_is_help=False, cls=SpawnGroup, add_completion=False
)


@app.callback(invoke_without_command=True)
def common_options_callback(
    ctx: typer.Context,
):
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


app.add_typer(init.app, name="init", help="Initialize space workspace structure and databases.")
app.add_typer(backup.app, name="backup", help="Backup and restore space data.")
app.add_typer(health.app, name="health", help="Verify space-os lattice integrity.")

app.add_typer(stats.app, name="stats", help="Show space overview and agent statistics.")
app.add_typer(canon.app, name="canon", help="Navigate and read canon documents from ~/space/canon.")
app.add_typer(chats.app, name="chats", help="Sync and view chat statistics across providers.")

app.add_typer(
    council.app, name="council", help="Join a bridge council - stream messages and respond live."
)
app.add_typer(
    daemons.app,
    name="daemons",
    help="Space health heartbeat: run all daemons in parallel, or invoke subcommands.",
)


def main() -> None:
    """Entry point for space command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
