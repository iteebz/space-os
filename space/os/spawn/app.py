import typer

from space.os.lib import errors

from .. import config
from . import registry, spawn
from .commands import tasks as tasks_module

errors.install_error_handler("spawn")

app = typer.Typer()


@app.command(name="tasks")
def tasks_cmd(
    status: str | None = typer.Option(None, help="Filter by status (pending|running|completed|failed|timeout)"),
    identity: str | None = typer.Option(None, help="Filter by agent identity"),
):
    """List spawn tasks."""
    registry.init_db()
    tasks_module.tasks_cmd(status=status, identity=identity)


@app.command(name="logs")
def logs_cmd(task_id: str):
    """Show full task details."""
    registry.init_db()
    tasks_module.logs_cmd(task_id)


@app.command(name="wait")
def wait_cmd(
    task_id: str,
    timeout: float = typer.Option(300.0, help="Wait timeout in seconds"),
):
    """Block until task completes."""
    registry.init_db()
    exit_code = tasks_module.wait_cmd(task_id, timeout=timeout)
    raise typer.Exit(exit_code)


@app.command(name="kill")
def kill_cmd(task_id: str):
    """Kill a running task."""
    registry.init_db()
    tasks_module.kill_cmd(task_id)


@app.command(name="rename")
def rename_cmd(old_name: str, new_name: str):
    """Rename an agent."""
    registry.init_db()
    try:
        if registry.rename_agent(old_name, new_name):
            typer.echo(f"✓ Renamed {old_name} → {new_name}")
        else:
            typer.echo(f"❌ Agent not found: {old_name}. Run `spawn` to list agents.", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.callback()
def main_command(ctx: typer.Context):
    """Constitutional agent registry"""
    registry.init_db()


@app.command(
    name="launch",
    hidden=True,
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch_cmd(ctx: typer.Context, agent_id: str):
    """Launch an agent (internal fallback)."""
    _spawn_from_registry(agent_id, ctx.args)


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
    context = None
    passthrough = []
    task = None

    i = 0
    while i < len(extra_args):
        if extra_args[i] == "--as" and i + 1 < len(extra_args):
            agent = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--model" and i + 1 < len(extra_args):
            model = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--channel" and i + 1 < len(extra_args):
            extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--context" and i + 1 < len(extra_args):
            context = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--sonnet":
            model = spawn.resolve_model_alias("sonnet")
            i += 1
        elif extra_args[i] == "--haiku":
            model = spawn.resolve_model_alias("haiku")
            i += 1
        elif not task and not extra_args[i].startswith("-"):
            task = extra_args[i]
            i += 1
        else:
            passthrough.append(extra_args[i])
            i += 1

    config.init_config()
    cfg = config.load_config()

    if arg in cfg["roles"]:
        if task:
            agent_obj = _get_agent(arg, agent, model, cfg)
            full_prompt = (context + "\n\n" + task) if context else task
            result = agent_obj.run(full_prompt)
            typer.echo(result)
        else:
            spawn.launch_agent(
                arg, identity=arg, base_identity=agent, extra_args=passthrough, model=model
            )
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            if task:
                agent_obj = _get_agent(arg, agent, model, cfg)
                full_prompt = (context + "\n\n" + task) if context else task
                result = agent_obj.run(full_prompt)
                typer.echo(result)
            else:
                spawn.launch_agent(
                    inferred_role,
                    identity=arg,
                    base_identity=agent,
                    extra_args=passthrough,
                    model=model,
                )
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def _get_agent(identity: str, base_agent: str | None, model: str | None, cfg: dict):
    """Get agent instance by identity."""
    from .agents import claude, codex, gemini

    actual_identity = identity
    if actual_identity not in cfg["roles"]:
        typer.echo(f"❌ Unknown identity: {actual_identity}", err=True)
        raise typer.Exit(1)

    role_cfg = cfg["roles"][actual_identity]
    base_identity = base_agent or role_cfg["base_identity"]

    agent_cfg = cfg.get("agents", {}).get(base_identity)
    if not agent_cfg:
        typer.echo(f"❌ Unknown agent: {base_identity}", err=True)
        raise typer.Exit(1)

    command = agent_cfg.get("command")
    agent_map = {"claude": claude.Claude, "gemini": gemini.Gemini, "codex": codex.Codex}

    if command not in agent_map:
        typer.echo(f"❌ Unknown agent command: {command}", err=True)
        raise typer.Exit(1)

    agent_class = agent_map[command]
    return agent_class(actual_identity)


if __name__ == "__main__":
    main()
