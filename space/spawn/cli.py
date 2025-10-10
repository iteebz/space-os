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
def main_command(
    ctx: typer.Context,
    agent: str | None = typer.Option(None, "--as", help="Agent to spawn as (e.g., claude, gemini)"),
    model: str | None = typer.Option(None, "--model", help="Model override"),
):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is None:
        if ctx.args:
            sender_id = ctx.args[0]
            _spawn_from_registry(sender_id, ctx.args[1:], agent, model)
        else:
            try:
                protocol_content = lattice.load("### spawn")
                typer.echo(protocol_content)
            except (FileNotFoundError, ValueError) as e:
                typer.echo(f"❌ spawn section not found in README: {e}")


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


def _spawn_from_registry(
    arg: str, extra_args: list[str], agent: str | None = None, model: str | None = None
):
    """Launch agent by role or agent_name."""

    cfg = spawn.load_config()

    if arg in cfg["roles"]:
        agent_name = spawn.auto_register_if_needed(arg, model)
        spawn.launch_agent(arg, agent_name=agent_name, base_identity=agent, extra_args=extra_args, model=model)
        return

    regs = [r for r in registry.list_registrations() if r.agent_name == arg]
    if regs:
        reg = regs[0]
        spawn.launch_agent(reg.role, agent_name=arg, base_identity=agent, extra_args=extra_args, model=model or reg.model)
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            spawn.launch_agent(inferred_role, agent_name=arg, base_identity=agent, extra_args=extra_args, model=model)
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def main() -> None:
    """Entry point for poetry script."""
    app()


if __name__ == "__main__":
    main()
