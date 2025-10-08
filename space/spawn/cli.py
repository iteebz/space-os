import sys

import click

from . import registry, spawn

CONTEXT_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}


class SpawnGroup(click.Group):
    """Custom group that falls back to inline launch syntax."""

    def resolve_command(self, ctx: click.Context, args):  # type: ignore[override]
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if not args:
                raise

        if args:
            inline = self.commands.get("_inline_launch")
            if inline is not None:
                return "_inline_launch", inline, args

        # If no inline handler, re-raise original resolution error.
        return super().resolve_command(ctx, args)


@click.group(
    cls=SpawnGroup,
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def main(ctx: click.Context):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is not None:
        return

    if not ctx.args:
        click.echo(ctx.get_help())
        ctx.exit()


@main.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
@click.option("--model", help="Model to use (e.g., claude-4.5-sonnet, gpt-5-codex)")
def register(role: str, sender_id: str, topic: str, model: str | None):
    """Register constitutional agent"""
    try:
        result = spawn.register_agent(role, sender_id, topic, model)
        model_suffix = f" (model: {result['model']})" if result.get("model") else ""
        click.echo(
            f"Registered: {result['role']} → {result['sender_id']} on {result['topic']} "
            f"(constitution: {result['constitution_hash']}){model_suffix}"
        )
    except Exception as e:
        click.echo(f"Registration failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
def unregister(role: str, sender_id: str, topic: str):
    """Unregister agent"""
    try:
        reg = registry.get_registration(role, sender_id, topic)
        if not reg:
            click.echo(f"Registration not found: {role} {sender_id} {topic}", err=True)
            sys.exit(1)

        registry.unregister(role, sender_id, topic)
        click.echo(f"Unregistered: {role} ({sender_id})")
    except Exception as e:
        click.echo(f"Unregister failed: {e}", err=True)
        sys.exit(1)


@main.command(name="list")
def list_registrations():
    """List registered agents"""
    regs = registry.list_registrations()
    if not regs:
        click.echo("No registrations found")
        return

    click.echo(
        f"{'ROLE':<15} {'SENDER':<15} {'TOPIC':<20} {'MODEL':<20} {'HASH':<10} {'REGISTERED':<20}"
    )
    click.echo("-" * 110)
    for r in regs:
        model_display = r.model or "–"
        click.echo(
            f"{r.role:<15} {r.sender_id:<15} {r.topic:<20} {model_display:<20} "
            f"{r.constitution_hash[:8]:<10} {r.registered_at:<20}"
        )


@main.command()
@click.argument("role")
def constitution(role: str):
    """Get constitution path for role"""
    try:
        path = spawn.get_constitution_path(role)
        click.echo(str(path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument("role")
@click.option(
    "--agent",
    help="The agent to spawn (e.g., gemini, claude). Uses role default if not specified.",
)
@click.option("--model", help="Model override (e.g., claude-4.5-sonnet, gpt-5-codex)")
@click.pass_context
def launch(ctx: click.Context, role: str, agent: str | None, model: str | None):
    """Launches an agent with a specific constitutional role."""
    try:
        spawn.launch_agent(role, agent, extra_args=list(ctx.args), model=model)
    except Exception as e:
        click.echo(f"Launch failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("base_identity")
def identity(base_identity: str):
    """Get bridge identity file path"""
    from . import config

    identity_file = config.bridge_identities_dir() / f"{base_identity}.md"
    click.echo(str(identity_file))


@main.command()
@click.argument("old_sender_id")
@click.argument("new_sender_id")
@click.option("--role", help="New role (optional, keeps existing if not specified)")
def rename(old_sender_id: str, new_sender_id: str, role: str | None):
    """Rename agent across all provenance systems"""

    from . import config

    try:
        regs = [r for r in registry.list_registrations() if r.sender_id == old_sender_id]
        if not regs:
            click.echo(f"No registrations found for {old_sender_id}", err=True)
            sys.exit(1)

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

        click.echo(
            f"Renamed {old_sender_id} → {new_sender_id}" + (f" (role: {role})" if role else "")
        )
    except Exception as e:
        click.echo(f"Rename failed: {e}", err=True)
        sys.exit(1)


@main.command(name="_inline_launch", hidden=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def _inline_launch(ctx: click.Context):
    """Handle implicit launch invocation (`spawn <agent_name> ...`)."""

    role, sender_id, base_identity, model, extra_args = _parse_inline_launch_args(ctx.args)
    try:
        spawn.launch_agent(role, sender_id, base_identity, extra_args=extra_args, model=model)
    except Exception as e:
        click.echo(f"Launch failed: {e}", err=True)
        ctx.exit(1)


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
            raise click.UsageError(f"Unknown role or agent: {first_arg}")

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
            raise click.UsageError("Invalid agent flag")

        if option == "as":  # Override sender_id
            idx += 1
            if idx >= len(args):
                raise click.UsageError(f"--{option} requires a value")
            sender_id = args[idx]
        elif option == "agent":  # Override base_identity
            idx += 1
            if idx >= len(args):
                raise click.UsageError(f"--{option} requires a value")
            base_identity = args[idx]
        elif option == "model":  # Override model
            idx += 1
            if idx >= len(args):
                raise click.UsageError("--model requires a value")
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
        raise click.UsageError("Role could not be determined.")
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
    main()
