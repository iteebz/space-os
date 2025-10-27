import click
import typer
from typer.core import TyperGroup

from space.apps import backup, canon, chats, context, council, daemons, health, init, stats
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
            api.launch_agent(agent.identity, extra_args=input_list)

        return spawn_agent


app = typer.Typer(invoke_without_command=True, no_args_is_help=False, cls=SpawnGroup)

app.add_typer(init.app, name="init")
app.add_typer(backup.app, name="backup")
app.add_typer(health.app, name="health")

app.add_typer(canon.app, name="canon")
app.add_typer(chats.app, name="chats")
app.add_typer(context.app, name="context")
app.add_typer(council.app, name="council")
app.add_typer(daemons.app, name="daemons")
app.add_typer(stats.app, name="stats")


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Show agent spawn context"),
):
    if ctx.invoked_subcommand is None:
        if identity:
            from space.os.spawn.api import agents, launch

            agent = agents.get_agent(identity)
            model = agent.model if agent else None
            context = launch.build_spawn_context(identity, model)
            typer.echo(context)
        else:
            typer.echo(
                "space-os: Agent orchestration system.\n"
                "\n"
                "Commands: space backup|health|init|canon|chats|context|council|daemons|stats"
            )


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
