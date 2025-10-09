import json

import typer

from ..bridge import api as bridge_api
from ..lib import protocols
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
                protocol_content = protocols.load("### spawn")
                typer.echo(protocol_content)
            except (FileNotFoundError, ValueError) as e:
                typer.echo(f"❌ spawn section not found in README: {e}")


@app.command()
def register(
    role: str = typer.Argument(...),
    sender_id: str = typer.Argument(...),
    topic: str = typer.Argument(...),
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
        result = spawn.register_agent(role, sender_id, topic, model)
        if json_output:
            typer.echo(json.dumps(result))
        elif not quiet_output:
            model_suffix = f" (model: {result['model']})" if result.get("model") else ""
            typer.echo(
                f"Registered: {result['role']} → {result['sender_id']} on {result['topic']} "
                f"(constitution: {result['constitution_hash']}){model_suffix}"
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
    sender_id: str = typer.Argument(..., help="Sender ID of the agent"),
    topic: str = typer.Argument(..., help="Topic the agent is unregistered from"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Unregister agent"""
    reg = registry.get_registration(role, sender_id, topic)
    if not reg:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": "Registration not found"}))
        elif not quiet_output:
            typer.echo(f"Registration not found: {role} {sender_id} {topic}", err=True)
        raise typer.Exit(code=1)

    try:
        registry.unregister(role, sender_id, topic)
        if json_output:
            typer.echo(json.dumps({"status": "success", "role": role, "sender_id": sender_id}))
        elif not quiet_output:
            typer.echo(f"Unregistered: {role} ({sender_id})")
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
            f"{'ROLE':<15} {'SENDER':<15} {'TOPIC':<20} {'MODEL':<20} {'HASH':<10} {'REGISTERED':<20}"
        )
        typer.echo("-" * 110)
        for r in regs:
            model_display = r.model or "–"
            typer.echo(
                f"{r.role:<15} {r.sender_id:<15} {r.topic:<20} {model_display:<20} "
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
    role: str = typer.Argument(...),
    agent: str | None = typer.Option(
        None,
        "--agent",
        help="The agent to spawn (e.g., gemini, claude). Uses role default if not specified.",
    ),
    model: str | None = typer.Option(
        None, "--model", help="Model override (e.g., claude-4.5-sonnet, gpt-5-codex)"
    ),
):
    """Launches an agent with a specific constitutional role."""
    try:
        spawn.launch_agent(role, agent, extra_args=list(ctx.args), model=model)
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
    old_sender_id: str = typer.Argument(...),
    new_sender_id: str = typer.Argument(...),
    role: str | None = typer.Option(
        None, "--role", help="New role (optional, keeps existing if not specified)"
    ),
):
    """Rename agent across all provenance systems"""

    try:
        regs = [r for r in registry.list_registrations() if r.sender_id == old_sender_id]
        if not regs:
            typer.echo(f"No registrations found for {old_sender_id}", err=True)
            raise typer.Exit(code=1)

        if role:
            const_path = spawn.get_constitution_path(role)
            const_content = const_path.read_text()
            const_hash = spawn.hash_content(const_content)
            registry.save_agent_identity(new_sender_id, const_content, const_hash)

        registry.rename_sender(old_sender_id, new_sender_id, role)

        bridge_api.rename_sender(old_sender_id, new_sender_id)

        old_identity = config.bridge_identities_dir() / f"{old_sender_id}.md"
        if old_identity.exists() and not role:
            new_identity = config.bridge_identities_dir() / f"{new_sender_id}.md"
            old_identity.rename(new_identity)

        typer.echo(
            f"Renamed {old_sender_id} → {new_sender_id}" + (f" (role: {role})" if role else "")
        )
    except Exception as e:
        typer.echo(f"Rename failed: {e}", err=True)
        raise typer.Exit(code=1) from e


def _spawn_from_registry(sender_id: str, extra_args: list[str]):
    regs = [r for r in registry.list_registrations() if r.sender_id == sender_id]
    if not regs:
        typer.echo(f"❌ Agent {sender_id} not registered", err=True)
        typer.echo(f"Register: spawn register <role> {sender_id} <channel>", err=True)
        raise typer.Exit(1)

    reg = regs[0]
    spawn.launch_agent(reg.role, sender_id=sender_id, extra_args=extra_args, model=reg.model)


def main() -> None:
    """Entry point for poetry script."""
    app()


if __name__ == "__main__":
    main()
