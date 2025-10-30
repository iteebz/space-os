import click
import typer
from typer.core import TyperGroup

from space.apps import backup, canon, chats, context, council, daemons, health, init, stats
from space.os import bridge, knowledge, memory, spawn
from space.os.spawn import api


class SpawnGroup(TyperGroup):
    """Typer group that dynamically spawns tasks for agent names."""

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


app = typer.Typer(invoke_without_command=True, no_args_is_help=False, cls=SpawnGroup)


@app.callback(invoke_without_command=True)
def common_options_callback(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Agent identity to use."),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Adds common CLI options (identity, json_output, quiet_output) to a Typer app."""
    from space.lib import output

    output.set_flags(ctx, json_output, quiet_output)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["identity"] = identity
    ctx.obj["json"] = json_output
    ctx.obj["quiet"] = quiet_output

    if ctx.invoked_subcommand is None:
        if identity:
            # The 'launch' module has been removed, so this functionality is disabled.
            # Please refer to the updated documentation for alternatives.
            pass
        else:
            typer.echo(
                "space-os: Agent orchestration system.\n"
                "\n"
                "Commands: space backup|health|init|canon|chats|context|council|daemons|stats"
            )


app.add_typer(init.app, name="init")
app.add_typer(backup.app, name="backup")
app.add_typer(health.app, name="health")

app.add_typer(canon.app, name="canon")
app.add_typer(chats.app, name="chats")
app.add_typer(context.app, name="context")
app.add_typer(council.app, name="council")
app.add_typer(daemons.app, name="daemons")
app.add_typer(stats.app, name="stats")

app.add_typer(bridge.app, name="bridge")
app.add_typer(knowledge.app, name="knowledge")
app.add_typer(memory.app, name="memory")
app.add_typer(spawn.app, name="spawn")


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
