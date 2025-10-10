import typer

from ..lib import lattice
from . import registry, spawn

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    agent_id: str = typer.Argument(None, help="Agent to spawn (role or agent_name)"),
):
    """Constitutional agent registry"""
    registry.init_db()

    if agent_id:
        _spawn_from_registry(agent_id, ctx.args)
    elif not ctx.invoked_subcommand:
        try:
            protocol_content = lattice.load("# spawn")
            typer.echo(protocol_content)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ spawn section not found in README: {e}")




def _spawn_from_registry(arg: str, extra_args: list[str]):
    """Launch agent by role or agent_name."""

    agent = None
    model = None
    passthrough = []
    
    i = 0
    while i < len(extra_args):
        if extra_args[i] == "--as" and i + 1 < len(extra_args):
            agent = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--model" and i + 1 < len(extra_args):
            model = extra_args[i + 1]
            i += 2
        else:
            passthrough.append(extra_args[i])
            i += 1

    cfg = spawn.load_config()

    if arg in cfg["roles"]:
        agent_name = spawn.auto_register_if_needed(arg, model)
        spawn.launch_agent(arg, agent_name=agent_name, base_identity=agent, extra_args=passthrough, model=model)
        return

    regs = [r for r in registry.list_registrations() if r.agent_name == arg]
    if regs:
        reg = regs[0]
        spawn.launch_agent(reg.role, agent_name=arg, base_identity=agent, extra_args=passthrough, model=model or reg.model)
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            spawn.launch_agent(inferred_role, agent_name=arg, base_identity=agent, extra_args=passthrough, model=model)
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def main() -> None:
    """Entry point for poetry script."""
    app()


if __name__ == "__main__":
    main()
