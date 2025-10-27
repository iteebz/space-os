import typer

from space.apps import canon, daemons
from space.apps.context.commands import context
from space.apps.council.commands import council
from space.apps.stats.commands import stats
from space.apps.system.commands import system

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(canon.app, name="canon")

app.add_typer(context, name="context")
app.add_typer(council, name="council")
app.add_typer(daemons.app, name="daemons")
app.add_typer(stats, name="stats")
app.add_typer(system, name="system")


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
                "Primitives: bridge, spawn, memory, knowledge\n"
                "Apps: space <canon|context|council|daemons|stats|system> --help"
            )


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
