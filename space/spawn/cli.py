import typer

from . import registry, spawn

app = typer.Typer()


@app.command(name="rename")
def rename_cmd(old_name: str, new_name: str):
    """Rename an agent."""
    registry.init_db()
    if registry.rename_agent(old_name, new_name):
        typer.echo(f"✓ Renamed {old_name} → {new_name}")
    else:
        typer.echo(f"❌ Agent not found: {old_name}", err=True)
        raise typer.Exit(1)


@app.callback()
def main_command(ctx: typer.Context):
    """Constitutional agent registry"""
    registry.init_db()


@app.command(name="launch", hidden=True)
def launch_cmd(agent_id: str, extra: list[str] | None = None):
    """Launch an agent (internal fallback)."""
    _spawn_from_registry(agent_id, extra or [])


def main() -> None:
    """Entry point for poetry script."""
    import sys

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd = sys.argv[1]
        if cmd not in ["rename"]:
            sys.argv.insert(1, "launch")

    app()


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
        agent_name = spawn.get_base_identity(arg)
        spawn.launch_agent(
            arg, agent_name=agent_name, base_identity=agent, extra_args=passthrough, model=model
        )
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            spawn.launch_agent(
                inferred_role,
                agent_name=arg,
                base_identity=agent,
                extra_args=passthrough,
                model=model,
            )
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    main()
