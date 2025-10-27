import typer

from space.apps import backup, canon, context, council, daemons, health, init, stats

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

app.add_typer(init.app, name="init")
app.add_typer(backup.app, name="backup")
app.add_typer(health.app, name="health")

app.add_typer(canon.app, name="canon")
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
                "Commands: space backup|health|init|canon|context|council|daemons|stats|system"
            )


def main() -> None:
    """Entry point for poetry script."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
