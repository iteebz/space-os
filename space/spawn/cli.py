import json

import typer

from ..bridge import api as bridge_api
from ..lib import lattice
from . import config, registry, spawn

app = typer.Typer(
    invoke_without_command=True,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


@app.callback()
def main_command(ctx: typer.Context):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is None:
        if ctx.args:
            sender_id = ctx.args[0]
            _spawn_from_registry(sender_id, ctx.args[1:])
        else:
            try:
                protocol_content = lattice.load("### spawn")
                typer.echo(protocol_content)
            except (FileNotFoundError, ValueError) as e:
                typer.echo(f"❌ spawn section not found in README: {e}")


@app.command()
def register(
    role: str = typer.Argument(...),
    agent_name: str = typer.Argument(...),
    topic: str = typer.Argument(...),
    client: str | None = typer.Option(
        None, "--client", help="Client type (e.g., claude, gemini, codex)"
    ),
    model: str | None = typer.Option(
        None, "--model", help="Model to use (e.g., claude-4.5-sonnet, gpt-5-codex)"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Register constitutional agent"""
    try:
        result = spawn.register_agent(role, agent_name, topic, client, model)
        if json_output:
            typer.echo(json.dumps(result))
        elif not quiet_output:
            model_suffix = f" (model: {result['model']})" if result.get("model") else ""
            client_suffix = f" (client: {result['client']})" if result.get("client") else ""
            typer.echo(
                f"Registered: {result['role']} → {result['agent_name']} on {result['topic']} "
                f"(constitution: {result['constitution_hash']}){client_suffix}{model_suffix}"
            )
    except Exception as e:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"Registration failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def unregister(
    role: str = typer.Argument(..., help="Role of the agent"),
    agent_name: str = typer.Argument(..., help="Agent name"),
    topic: str = typer.Argument(..., help="Topic the agent is unregistered from"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Unregister agent"""
    reg = registry.get_registration(role, agent_name, topic)
    if not reg:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": "Registration not found"}))
        elif not quiet_output:
            typer.echo(f"Registration not found: {role} {agent_name} {topic}", err=True)
        raise typer.Exit(code=1)

    try:
        registry.unregister(role, agent_name, topic)
        if json_output:
            typer.echo(json.dumps({"status": "success", "role": role, "agent_name": agent_name}))
        elif not quiet_output:
            typer.echo(f"Unregistered: {role} ({agent_name})")
    except Exception as e:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"Unregistration failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command(name="list")
def list_registrations(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List registered agents"""
    regs = registry.list_registrations()
    if not regs:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No registrations found")
        return

    if json_output:
        from dataclasses import asdict

        typer.echo(json.dumps([asdict(r) for r in regs]))
        return

    if not quiet_output:
        typer.echo(
            f"{'ROLE':<15} {'AGENT_NAME':<15} {'CLIENT':<10} {'TOPIC':<20} {'MODEL':<20} {'HASH':<10} {'REGISTERED':<20}"
        )
        typer.echo("-" * 120)
        for r in regs:
            model_display = r.model or "–"
            client_display = r.client or "–"
            typer.echo(
                f"{r.role:<15} {r.agent_name:<15} {client_display:<10} {r.topic:<20} {model_display:<20} "
                f"{r.constitution_hash[:8]:<10} {r.registered_at:<20}"
            )


@app.command()
def constitution(
    role: str = typer.Argument(...),
):
    """Get constitution path for role"""
    try:
        path = spawn.get_constitution_path(role)
        typer.echo(str(path))
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def launch(
    ctx: typer.Context,
    role_or_name: str = typer.Argument(...),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="The agent to spawn (e.g., gemini, claude). Uses role default if not specified.",
    ),
    model: str | None = typer.Option(
        None, "--model", help="Model override (e.g., claude-4.5-sonnet, gpt-5-codex)"
    ),
):
    """Launches an agent with a specific constitutional role or agent_name."""
    try:
        cfg = spawn.load_config()

        if role_or_name in cfg["roles"]:
            agent_name = spawn.auto_register_if_needed(role_or_name, model)
            spawn.launch_agent(
                role_or_name, agent_name, agent, extra_args=list(ctx.args), model=model
            )
            return

        regs = [r for r in registry.list_registrations() if r.agent_name == role_or_name]
        if regs:
            reg = regs[0]
            spawn.launch_agent(
                reg.role, role_or_name, agent, extra_args=list(ctx.args), model=model or reg.model
            )
            return

        if "-" in role_or_name:
            inferred_role = role_or_name.split("-", 1)[0]
            if inferred_role in cfg["roles"]:
                spawn.launch_agent(
                    inferred_role, role_or_name, agent, extra_args=list(ctx.args), model=model
                )
                return

        typer.echo(f"❌ Unknown role or agent: {role_or_name}", err=True)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def identity(
    base_identity: str = typer.Argument(...),
):
    """Get bridge identity file path"""

    identity_file = config.bridge_identities_dir() / f"{base_identity}.md"
    typer.echo(str(identity_file))


@app.command()
def rename(
    old_agent_name: str = typer.Argument(...),
    new_agent_name: str = typer.Argument(...),
    role: str | None = typer.Option(
        None, "--role", help="New role (optional, keeps existing if not specified)"
    ),
):
    """Rename agent across all provenance systems"""

    try:
        regs = [r for r in registry.list_registrations() if r.agent_name == old_agent_name]
        if not regs:
            typer.echo(f"No registrations found for {old_agent_name}", err=True)
            raise typer.Exit(code=1)

        if role:
            const_path = spawn.get_constitution_path(role)
            const_content = const_path.read_text()
            const_hash = spawn.hash_content(const_content)
            registry.save_agent_identity(new_agent_name, const_content, const_hash)

        registry.rename_agent(old_agent_name, new_agent_name, role)

        bridge_api.rename_agent(old_agent_name, new_agent_name)

        old_identity = config.bridge_identities_dir() / f"{old_agent_name}.md"
        if old_identity.exists() and not role:
            new_identity = config.bridge_identities_dir() / f"{new_agent_name}.md"
            old_identity.rename(new_identity)

        typer.echo(
            f"Renamed {old_agent_name} → {new_agent_name}" + (f" (role: {role})" if role else "")
        )
    except Exception as e:
        typer.echo(f"Rename failed: {e}", err=True)
        raise typer.Exit(code=1) from e


def _spawn_from_registry(arg: str, extra_args: list[str]):
    """Launch agent by role or agent_name."""

    cfg = spawn.load_config()

    if arg in cfg["roles"]:
        agent_name = spawn.auto_register_if_needed(arg)
        spawn.launch_agent(arg, agent_name=agent_name, extra_args=extra_args)
        return

    regs = [r for r in registry.list_registrations() if r.agent_name == arg]
    if regs:
        reg = regs[0]
        spawn.launch_agent(reg.role, agent_name=arg, extra_args=extra_args, model=reg.model)
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            spawn.launch_agent(inferred_role, agent_name=arg, extra_args=extra_args)
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def main() -> None:
    """Entry point for poetry script."""
    app()


if __name__ == "__main__":
    main()
