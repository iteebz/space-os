import click
import typer
from typer.core import TyperGroup

from space.apps import canon, chats, context, council, daemons, health, init, stats
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
    identity: str = typer.Option(None, "--as", help="Agent identity to use."),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Agent Orchestration System

    Manage agents, their memories, shared knowledge, and coordination."""
    from space.lib import output

    output.set_flags(ctx, json_output, quiet_output)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["identity"] = identity
    ctx.obj["json"] = json_output
    ctx.obj["quiet"] = quiet_output

    if ctx.invoked_subcommand is None:
        if identity:
            pass
        else:
            typer.echo(ctx.get_help())


app.add_typer(init.app, name="init")
app.add_typer(backup.app, name="backup")
app.add_typer(health.app, name="health")

app.add_typer(canon.app, name="canon")
app.add_typer(chats.app, name="chats")
app.add_typer(context.app, name="context")
app.add_typer(council.app, name="council")
app.add_typer(daemons.app, name="daemons")
app.add_typer(stats.app, name="stats")


def main() -> None:
    """Entry point for space command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
