import typer

from space.os import config
from space.os.lib import errors

from . import commands
from . import spawn as spawn_module

errors.install_error_handler("spawn")

spawn = typer.Typer()


@spawn.callback()
def cb(ctx: typer.Context):
    """Constitutional agent registry"""
    pass


spawn.add_typer(commands.agents.app)
spawn.add_typer(commands.tasks.app)


@spawn.command(
    name="launch",
    hidden=True,
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch(ctx: typer.Context, agent_id: str):
    """Launch an agent (internal fallback)."""
    _spawn_from_registry(agent_id, ctx.args)


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
            model = spawn_module.resolve_model_alias("sonnet")
            i += 1
        elif extra_args[i] == "--haiku":
            model = spawn_module.resolve_model_alias("haiku")
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
            spawn_module.launch_agent(
                arg, role=arg, base_agent=agent, extra_args=passthrough, model=model
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
                spawn_module.launch_agent(
                    inferred_role,
                    role=arg,
                    base_agent=agent,
                    extra_args=passthrough,
                    model=model,
                )
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def _get_agent(role: str, base_agent: str | None, model: str | None, cfg: dict):
    """Get agent instance by role."""
    from space.os.lib import agents

    actual_role = role
    if actual_role not in cfg["roles"]:
        typer.echo(f"❌ Unknown role: {actual_role}", err=True)
        raise typer.Exit(1)

    role_cfg = cfg["roles"][actual_role]
    actual_base_agent = base_agent or role_cfg["base_agent"]

    agent_cfg = cfg.get("agents", {}).get(actual_base_agent)
    if not agent_cfg:
        typer.echo(f"❌ Unknown agent: {actual_base_agent}", err=True)
        raise typer.Exit(1)

    command = agent_cfg.get("command")
    agent_map = {
        "claude": agents.claude,
        "gemini": agents.gemini,
        "codex": agents.codex,
    }

    if command not in agent_map:
        typer.echo(f"❌ Unknown agent command: {command}", err=True)
        raise typer.Exit(1)

    agent_module = agent_map[command]
    return _AgentRunner(actual_identity, agent_module)


class _AgentRunner:
    """Simple agent runner wrapper."""

    def __init__(self, identity: str, agent_module):
        self.identity = identity
        self.agent_module = agent_module

    def run(self, prompt: str | None = None) -> str:
        return self.agent_module.spawn(self.identity, prompt)


def main() -> None:
    """Entry point for poetry script."""
    import sys

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd = sys.argv[1]
        if cmd not in [
            "tasks",
            "logs",
            "wait",
            "kill",
            "agents",
            "describe",
            "inspect",
            "merge",
            "delete",
            "rename",
        ]:
            sys.argv.insert(1, "launch")

    spawn()


if __name__ == "__main__":
    main()
