from pathlib import Path

import typer

from . import registry, spawn

app = typer.Typer(invoke_without_command=True)

# Removed: PROTOCOL_FILE definition


@app.callback()
def main_command(ctx: typer.Context):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is None and not ctx.args:
        try:
            protocol_content = (
                Path(__file__).parent.parent.parent / "protocols" / "spawn.md"
            ).read_text()
            typer.echo(protocol_content)
        except FileNotFoundError:
            typer.echo("❌ spawn.md protocol not found")
        return

    if ctx.invoked_subcommand is not None:
        return

    if not ctx.args:
        typer.echo(ctx.get_help())
        return

    # This part handles the inline launch syntax
    # It will be re-implemented using Typer's capabilities
    # For now, it will raise an error if inline launch is attempted
    typer.echo("Inline launch is not yet supported in this version.", err=True)
    raise typer.Exit(code=1)


@app.command()
def register(
    role: str = typer.Argument(...),
    sender_id: str = typer.Argument(...),
    topic: str = typer.Argument(...),
    model: str | None = typer.Option(
        None, "--model", help="Model to use (e.g., claude-4.5-sonnet, gpt-5-codex)"
    ),
):
    """Register constitutional agent"""
    try:
        result = spawn.register_agent(role, sender_id, topic, model)
        model_suffix = f" (model: {result['model']})" if result.get("model") else ""
        typer.echo(
            f"Registered: {result['role']} → {result['sender_id']} on {result['topic']} "
            f"(constitution: {result['constitution_hash']}){model_suffix}"
        )
    except Exception as e:
        typer.echo(f"Registration failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def unregister(
    role: str = typer.Argument(..., help="Role of the agent"),
    sender_id: str = typer.Argument(..., help="Sender ID of the agent"),
    topic: str = typer.Argument(..., help="Topic the agent is unregistered from"),
):
    """Unregister agent"""
    try:
        reg = registry.get_registration(role, sender_id, topic)
        if not reg:
            typer.echo(f"Registration not found: {role} {sender_id} {topic}", err=True)
            raise typer.Exit(code=1)

        registry.unregister(role, sender_id, topic)
        typer.echo(f"Unregistered: {role} ({sender_id})")
    except Exception as e:
        typer.echo(f"Unregistration failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command(name="list")
def list_registrations():
    """List registered agents"""
    regs = registry.list_registrations()
    if not regs:
        typer.echo("No registrations found")
        return

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
    from . import config

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

    from . import config

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

        bridge_db = config.workspace_root() / ".space" / "bridge.db"
        import sqlite3

        conn = sqlite3.connect(bridge_db)
        conn.execute(
            "UPDATE messages SET sender = ? WHERE sender = ?", (new_sender_id, old_sender_id)
        )
        conn.execute(
            "UPDATE bookmarks SET agent_id = ? WHERE agent_id = ?", (new_sender_id, old_sender_id)
        )
        conn.commit()
        conn.close()

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


@app.command(name="_inline_launch", hidden=True)
def _inline_launch(
    ctx: typer.Context,
):
    """Handle implicit launch invocation (`spawn <agent_name> ...`)."""

    role, sender_id, base_identity, model, extra_args = _parse_inline_launch_args(ctx.args)
    try:
        spawn.launch_agent(role, sender_id, base_identity, extra_args=extra_args, model=model)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(code=1) from e


def _parse_inline_launch_args(
    args: list[str],
) -> tuple[str, str | None, str | None, str | None, list[str]]:
    """Parse inline spawn launch invocation.

    Supports:
    - spawn <agent_name> (infers role and model)
    - spawn <role> --as <sender_id>
    - spawn <role> --agent <base_identity>
    - spawn <role> --model <model>
    - spawn <role> --sonnet / --codex (model shortcuts)
    """

    # Initial parsing of the first argument as potential agent_name or role
    first_arg = args[0]

    # Default values
    role: str | None = None
    sender_id: str | None = None  # This will be the agent_name passed to launch_agent
    base_identity: str | None = None  # This is the 'agent' argument in launch_agent
    model: str | None = None
    passthrough: list[str] = []

    cfg = spawn.load_config()
    configured_roles = set(cfg.get("roles", {}).keys())
    configured_agents = set(cfg.get("agents", {}).keys())
    model_shortcuts = {
        "sonnet": "claude-4.5-sonnet",
        "codex": "gpt-5-codex",
        "gpt": "gpt-5-codex",
        "claude": "claude-4.5-sonnet",
        "gemini": "gemini-2.5-pro",
    }

    # Determine initial role and sender_id
    if first_arg in configured_roles:
        role = first_arg
        sender_id = spawn.get_base_identity(role)  # Default sender_id from role's base_identity
    else:
        # Assume first_arg is an agent_name, try to infer role
        inferred_role = first_arg.split("-")[0] if "-" in first_arg else first_arg
        if inferred_role in configured_roles:
            role = inferred_role
            sender_id = first_arg  # Use the full agent_name as sender_id
        else:
            raise typer.BadParameter(f"Unknown role or agent: {first_arg}")

    # If sender_id is still None, try to get it from the role's base_identity
    if sender_id is None and role is not None:
        sender_id = spawn.get_base_identity(role)

    # Parse remaining arguments for overrides
    idx = 1
    while idx < len(args):
        token = args[idx]
        if token == "--":
            passthrough.extend(args[idx + 1 :])
            break

        if not token.startswith("--"):
            # If it's not an option, it's a passthrough argument
            passthrough.append(token)
            idx += 1
            continue

        option = token[2:]
        if not option:
            raise typer.BadParameter("Invalid agent flag")

        if option == "as":  # Override sender_id
            idx += 1
            if idx >= len(args):
                raise typer.BadParameter(f"--{option} requires a value")
            sender_id = args[idx]
        elif option == "agent":  # Override base_identity
            idx += 1
            if idx >= len(args):
                raise typer.BadParameter(f"--{option} requires a value")
            base_identity = args[idx]
        elif option == "model":  # Override model
            idx += 1
            if idx >= len(args):
                raise typer.BadParameter("--model requires a value")
            model = args[idx]
        elif option in model_shortcuts:  # Model shortcuts
            model = model_shortcuts[option]
        elif option in configured_agents:  # Direct agent override
            base_identity = option
        else:
            # Unrecognized option, treat as passthrough
            passthrough.append(token)
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                passthrough.append(args[idx + 1])
                idx += 1
        idx += 1

    # Final check and defaults
    if role is None:
        raise typer.BadParameter("Role could not be determined.")
    if sender_id is None:
        sender_id = spawn.get_base_identity(role)  # Fallback to role's base_identity

    # If base_identity is not explicitly set, use the role's base_identity
    if base_identity is None:
        base_identity = spawn.get_base_identity(role)

    # If model is not explicitly set, try to infer from base_identity
    if model is None and base_identity is not None:
        agent_cfg = cfg.get("agents", {}).get(base_identity)
        if agent_cfg and "command" in agent_cfg:
            # This is a simplification; actual model inference might be more complex
            # For now, we'll assume the command itself implies the model or it's handled by the agent
            pass

    return role, sender_id, base_identity, model, passthrough


if __name__ == "__main__":
    app()
